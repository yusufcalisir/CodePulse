"""GitHub GraphQL API client with rate limit handling."""

import asyncio
import logging
import time
from dataclasses import dataclass, field

import httpx

from app.core.config import get_settings
from app.data_plane.ingestion.quota_scheduler import QuotaAwareScheduler

logger = logging.getLogger(__name__)

# ── GraphQL Queries ──────────────────────────────────────────

PULL_REQUESTS_QUERY = """
query($owner: String!, $name: String!, $cursor: String) {
  repository(owner: $owner, name: $name) {
    databaseId
    pullRequests(
      first: 100,
      after: $cursor,
      orderBy: {field: CREATED_AT, direction: DESC}
    ) {
      pageInfo {
        hasNextPage
        endCursor
      }
      nodes {
        databaseId
        number
        title
        state
        createdAt
        mergedAt
        closedAt
        additions
        deletions
        author { login }
        reviews(first: 50) {
          nodes {
            databaseId
            state
            createdAt
            author { login }
          }
        }
      }
    }
  }
}
"""

REPO_INFO_QUERY = """
query($owner: String!, $name: String!) {
  repository(owner: $owner, name: $name) {
    databaseId
    name
    nameWithOwner
    owner { login }
    defaultBranchRef { name }
  }
}
"""

COMMITS_QUERY = """
query($owner: String!, $name: String!, $expression: String!) {
  repository(owner: $owner, name: $name) {
    object(expression: $expression) {
      ... on Commit {
        history(first: 100) {
          nodes {
            oid
            message
            authoredDate
            author {
              user {
                login
              }
              name
            }
          }
        }
      }
    }
  }
}
"""


VIEWER_REPOS_QUERY = """
query($cursor: String) {
  viewer {
    repositories(
      first: 100,
      after: $cursor,
      affiliations: [OWNER, COLLABORATOR, ORGANIZATION_MEMBER],
      orderBy: {field: UPDATED_AT, direction: DESC}
    ) {
      pageInfo { hasNextPage endCursor }
      nodes {
        databaseId
        name
        nameWithOwner
        owner { login }
        defaultBranchRef { name }
      }
    }
  }
}
"""


@dataclass
class RateLimitState:
    """Tracks GitHub API rate limit status."""

    remaining: int = 5000
    reset_at: float = 0.0
    last_checked: float = 0.0


@dataclass
class GitHubCollector:
    """Async GitHub GraphQL API client with rate limiting and pagination."""

    token: str = ""
    _client: httpx.AsyncClient | None = field(default=None, repr=False)
    _rate_limit: RateLimitState = field(default_factory=RateLimitState)
    _scheduler: QuotaAwareScheduler = field(default_factory=QuotaAwareScheduler, repr=False)

    def __post_init__(self) -> None:
        if not self.token:
            settings = get_settings()
            self.token = settings.GITHUB_TOKEN

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url="https://api.github.com",
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                timeout=30.0,
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def _wait_for_rate_limit(self) -> None:
        """Wait if we are close to the rate limit."""
        await self._scheduler.schedule_request(
            remaining=self._rate_limit.remaining,
            reset_at=self._rate_limit.reset_at,
        )

    def _update_rate_limit(self, headers: httpx.Headers) -> None:
        """Update rate limit state from response headers."""
        remaining = headers.get("x-ratelimit-remaining")
        reset_at = headers.get("x-ratelimit-reset")
        if remaining is not None:
            self._rate_limit.remaining = int(remaining)
        if reset_at is not None:
            self._rate_limit.reset_at = float(reset_at)
        self._rate_limit.last_checked = time.time()

    async def _execute_query(
        self,
        query: str,
        variables: dict | None = None,
        retries: int = 3,
    ) -> dict:
        """Execute a GraphQL query with rate limiting and retries."""
        await self._wait_for_rate_limit()

        client = await self._get_client()
        payload = {"query": query}
        if variables:
            payload["variables"] = variables

        for attempt in range(retries):
            try:
                response = await client.post("/graphql", json=payload)
                self._update_rate_limit(response.headers)

                if response.status_code == 200:
                    data = response.json()
                    if "errors" in data:
                        error_msg = data["errors"][0].get("message", "Unknown GraphQL error")
                        logger.error("GraphQL error: %s", error_msg)
                        raise GitHubAPIError(error_msg)
                    return data["data"]

                if response.status_code == 403:
                    # Secondary rate limit — respect Retry-After
                    retry_after = int(response.headers.get("retry-after", 60))
                    logger.warning(
                        "Secondary rate limit hit. Waiting %d seconds.", retry_after
                    )
                    await asyncio.sleep(retry_after)
                    continue

                if response.status_code >= 500:
                    # Server error — retry with backoff
                    wait = (2**attempt) + 1
                    logger.warning(
                        "GitHub server error %d. Retry %d/%d in %ds.",
                        response.status_code,
                        attempt + 1,
                        retries,
                        wait,
                    )
                    await asyncio.sleep(wait)
                    continue

                response.raise_for_status()

            except httpx.TimeoutException:
                if attempt < retries - 1:
                    wait = (2**attempt) + 1
                    logger.warning("Timeout. Retry %d/%d in %ds.", attempt + 1, retries, wait)
                    await asyncio.sleep(wait)
                else:
                    raise

        raise GitHubAPIError("Max retries exceeded")

    # ── Public API ────────────────────────────────────────────

    async def get_repo_info(self, owner: str, name: str) -> dict:
        """Fetch basic repository information."""
        data = await self._execute_query(REPO_INFO_QUERY, {"owner": owner, "name": name})
        return data["repository"]

    async def fetch_pull_requests(
        self,
        owner: str,
        name: str,
        max_prs: int = 1000,
    ) -> list[dict]:
        """Fetch pull requests with reviews using cursor-based pagination.

        Args:
            owner: Repository owner (org or user).
            name: Repository name.
            max_prs: Maximum number of PRs to fetch (default 1000).

        Returns:
            List of PR dictionaries including nested reviews.
        """
        all_prs: list[dict] = []
        cursor: str | None = None

        while len(all_prs) < max_prs:
            variables = {"owner": owner, "name": name, "cursor": cursor}
            data = await self._execute_query(PULL_REQUESTS_QUERY, variables)

            repo_data = data["repository"]
            pr_data = repo_data["pullRequests"]

            all_prs.extend(pr_data["nodes"])
            logger.info(
                "Fetched %d PRs (total: %d) for %s/%s",
                len(pr_data["nodes"]),
                len(all_prs),
                owner,
                name,
            )

            if not pr_data["pageInfo"]["hasNextPage"]:
                break

            cursor = pr_data["pageInfo"]["endCursor"]

        return all_prs[:max_prs]

    async def fetch_commits(
        self,
        owner: str,
        name: str,
        branch: str = "main",
    ) -> list[dict]:
        """Fetch recent commits from the specified branch using the commit expression."""
        try:
            data = await self._execute_query(
                COMMITS_QUERY,
                {"owner": owner, "name": name, "expression": branch}
            )
            repo = data.get("repository")
            if not repo:
                return []
            obj = repo.get("object")
            if not obj:
                return []
            history = obj.get("history")
            if not history:
                return []
            return history.get("nodes") or []
        except Exception as e:
            logger.error("Failed to fetch commits for %s/%s on branch %s: %s", owner, name, branch, e)
            return []


    async def fetch_viewer_repos(self) -> list[dict]:
        """Fetch repositories accessible to the authenticated user."""
        all_repos: list[dict] = []
        cursor: str | None = None

        while True:
            data = await self._execute_query(VIEWER_REPOS_QUERY, {"cursor": cursor})
            viewer_data = data["viewer"]["repositories"]

            all_repos.extend(viewer_data["nodes"])

            if not viewer_data["pageInfo"]["hasNextPage"]:
                break

            cursor = viewer_data["pageInfo"]["endCursor"]

        return all_repos


class GitHubAPIError(Exception):
    """Custom exception for GitHub API errors."""

    pass
