"""Event normalizer — converts raw GitHub API payloads into normalized schemas."""

from datetime import datetime, timezone


def parse_datetime(dt_str: str | None) -> datetime | None:
    """Safely parse ISO datetime strings from GitHub into timezone-aware datetime objects."""
    if not dt_str:
        return None
    try:
        # Replace Z with +00:00 for timezone consistency across Python versions
        normalized_str = dt_str.replace("Z", "+00:00")
        return datetime.fromisoformat(normalized_str)
    except Exception:
        return None


def normalize_repository(raw_repo: dict) -> dict:
    """Normalize raw GitHub repository payload.

    Args:
        raw_repo: Dict containing raw GitHub repository info.

    Returns:
        A dictionary with keys mapped to Repository model attributes.
    """
    default_branch = (raw_repo.get("defaultBranchRef") or {}).get("name", "main")
    return {
        "github_id": raw_repo["databaseId"],
        "name": raw_repo["name"],
        "full_name": raw_repo["nameWithOwner"],
        "org": raw_repo["owner"]["login"] if raw_repo.get("owner") else None,
        "default_branch": default_branch,
    }


def normalize_pull_request(repo_id: int, raw_pr: dict) -> dict:
    """Normalize raw GitHub pull request payload.

    Args:
        repo_id: Internal database ID of the repository.
        raw_pr: Dict containing raw GitHub PR info.

    Returns:
        A dictionary with keys mapped to PullRequest model attributes.
    """
    state = raw_pr.get("state", "open").lower()
    if state == "merged" or raw_pr.get("mergedAt"):
        state = "merged"

    return {
        "repo_id": repo_id,
        "github_id": raw_pr["databaseId"],
        "number": raw_pr["number"],
        "title": raw_pr.get("title"),
        "state": state,
        "author": (raw_pr.get("author") or {}).get("login"),
        "created_at": parse_datetime(raw_pr["createdAt"]),
        "merged_at": parse_datetime(raw_pr.get("mergedAt")),
        "closed_at": parse_datetime(raw_pr.get("closedAt")),
        "additions": raw_pr.get("additions", 0),
        "deletions": raw_pr.get("deletions", 0),
    }


def normalize_review(pr_id: int, raw_review: dict) -> dict:
    """Normalize raw GitHub review payload.

    Args:
        pr_id: Internal database ID of the parent Pull Request.
        raw_review: Dict containing raw GitHub review info.

    Returns:
        A dictionary with keys mapped to Review model attributes.
    """
    return {
        "pr_id": pr_id,
        "github_id": raw_review["databaseId"],
        "author": (raw_review.get("author") or {}).get("login"),
        "state": raw_review.get("state", "COMMENTED"),
        "submitted_at": parse_datetime(raw_review["createdAt"]),
    }


def normalize_commit(repo_id: int, raw_commit: dict) -> dict:
    """Normalize raw GitHub commit payload.

    Args:
        repo_id: Internal database ID of the repository.
        raw_commit: Dict containing raw GitHub commit info.

    Returns:
        A dictionary with keys mapped to Commit model attributes.
    """
    author_info = raw_commit.get("author") or {}
    author_login = (author_info.get("user") or {}).get("login") or author_info.get("name")
    return {
        "repo_id": repo_id,
        "sha": raw_commit["oid"],
        "message": raw_commit.get("message"),
        "author": author_login,
        "authored_at": parse_datetime(raw_commit.get("authoredDate")),
    }

