"""Storage Manager — orchestrates data plane DB insertions, normalizations, and sync execution."""

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.data_plane.ingestion.github_collector import GitHubCollector
from app.data_plane.normalization.normalizer import (
    normalize_pull_request,
    normalize_repository,
    normalize_review,
    normalize_commit,
)
from app.data_plane.storage.models.commit import Commit
from app.data_plane.storage.models.pull_request import PullRequest
from app.data_plane.storage.models.repository import Repository
from app.data_plane.storage.models.review import Review
from app.data_plane.storage.models.sync_log import SyncLog
from app.data_plane.storage.models.event import Event

logger = logging.getLogger(__name__)


class StorageManager:
    """Orchestrates ingestion, payload normalization, and immutable DB storage."""

    def __init__(self, db: AsyncSession, github_token: str = "") -> None:
        self.db = db
        self.collector = GitHubCollector(token=github_token)

    async def close(self) -> None:
        """Clean up collector client resources."""
        await self.collector.close()

    async def initial_sync(self, full_name: str, org_id: str) -> SyncLog:
        """Run a full initial sync for a repository."""
        owner, name = full_name.split("/", 1)

        repo = await self.ensure_repository(owner, name, org_id)
        sync_log = SyncLog(repo_id=repo.id, status="running", pr_count=0)
        self.db.add(sync_log)
        await self.db.flush()

        try:
            raw_prs = await self.collector.fetch_pull_requests(owner, name, max_prs=1000)
            logger.info("Fetched %d raw PRs for %s", len(raw_prs), full_name)

            pr_count = await self.upsert_normalized_prs(repo.id, raw_prs)

            default_branch = repo.default_branch or "main"
            raw_commits = await self.collector.fetch_commits(owner, name, default_branch)
            logger.info("Fetched %d raw commits for %s on branch %s", len(raw_commits), full_name, default_branch)
            await self.upsert_normalized_commits(repo.id, raw_commits)

            # Precompute engineering metrics and store daily snapshots
            from app.intelligence_plane.metrics.precomputer import MetricsPrecomputer
            precomputer = MetricsPrecomputer(self.db)
            await precomputer.precompute_repository_metrics(repo.id)

            repo.synced_at = datetime.now(timezone.utc)

            sync_log.status = "completed"
            sync_log.pr_count = pr_count
            sync_log.finished_at = datetime.now(timezone.utc)

            logger.info(
                "Sync completed for %s: %d PRs ingested", full_name, pr_count
            )

        except Exception as e:
            sync_log.status = "failed"
            sync_log.error = str(e)
            sync_log.finished_at = datetime.now(timezone.utc)
            logger.error("Sync failed for %s: %s", full_name, e)
            raise

        return sync_log

    async def incremental_sync(self, repo_id: int) -> SyncLog:
        """Run an incremental sync for a repository."""
        result = await self.db.execute(
            select(Repository).where(Repository.id == repo_id)
        )
        repo = result.scalar_one_or_none()
        if not repo:
            raise ValueError(f"Repository with id {repo_id} not found")

        owner, name = repo.full_name.split("/", 1)

        sync_log = SyncLog(repo_id=repo.id, status="running", pr_count=0)
        self.db.add(sync_log)
        await self.db.flush()

        try:
            raw_prs = await self.collector.fetch_pull_requests(owner, name, max_prs=200)
            pr_count = await self.upsert_normalized_prs(repo.id, raw_prs)

            default_branch = repo.default_branch or "main"
            raw_commits = await self.collector.fetch_commits(owner, name, default_branch)
            await self.upsert_normalized_commits(repo.id, raw_commits)

            # Precompute engineering metrics and store daily snapshots
            from app.intelligence_plane.metrics.precomputer import MetricsPrecomputer
            precomputer = MetricsPrecomputer(self.db)
            await precomputer.precompute_repository_metrics(repo.id)

            repo.synced_at = datetime.now(timezone.utc)
            sync_log.status = "completed"
            sync_log.pr_count = pr_count
            sync_log.finished_at = datetime.now(timezone.utc)

        except Exception as e:
            sync_log.status = "failed"
            sync_log.error = str(e)
            sync_log.finished_at = datetime.now(timezone.utc)
            raise

        return sync_log

    async def ensure_repository(self, owner: str, name: str, org_id: str) -> Repository:
        """Get or create a repository record using normalizer."""
        full_name = f"{owner}/{name}"

        result = await self.db.execute(
            select(Repository).where(
                Repository.full_name == full_name,
                Repository.org_id == org_id
            )
        )
        repo = result.scalar_one_or_none()

        if repo:
            return repo

        raw_info = await self.collector.get_repo_info(owner, name)
        normalized = normalize_repository(raw_info)
        normalized["org_id"] = org_id

        repo = Repository(**normalized)
        self.db.add(repo)
        await self.db.flush()
        return repo

    async def _log_event(
        self,
        repo_id: int,
        event_type: str,
        actor: str | None,
        payload: dict,
        idempotency_key: str | None = None,
    ) -> None:
        """Create and append an immutable event log entry with database-level idempotency guarantees."""
        if idempotency_key:
            existing = await self.db.execute(
                select(Event.id).where(Event.idempotency_key == idempotency_key)
            )
            if existing.scalar_one_or_none() is not None:
                return
        else:
            source_id = payload.get("source_github_id")
            if source_id:
                existing = await self.db.execute(
                    select(Event.id).where(
                        Event.repo_id == repo_id,
                        Event.type == event_type,
                        Event.payload["source_github_id"].as_json() == str(source_id)
                    )
                )
                if existing.scalar_one_or_none() is not None:
                    return

        event_log = Event(
            type=event_type,
            repo_id=repo_id,
            actor=actor,
            payload=payload,
            idempotency_key=idempotency_key,
        )
        self.db.add(event_log)
        await self.db.flush()

    async def upsert_normalized_prs(self, repo_id: int, raw_prs: list[dict]) -> int:
        """Normalize and upsert pull requests and their reviews into storage."""
        count = 0

        for raw_pr in raw_prs:
            normalized_pr = normalize_pull_request(repo_id, raw_pr)

            # Upsert the normalized PR
            pr_stmt = pg_insert(PullRequest).values(**normalized_pr)
            pr_stmt = pr_stmt.on_conflict_do_update(
                constraint="uq_pr_repo_github",
                set_={
                    "state": pr_stmt.excluded.state,
                    "title": pr_stmt.excluded.title,
                    "merged_at": pr_stmt.excluded.merged_at,
                    "closed_at": pr_stmt.excluded.closed_at,
                    "additions": pr_stmt.excluded.additions,
                    "deletions": pr_stmt.excluded.deletions,
                    "fetched_at": datetime.now(timezone.utc),
                },
            )
            await self.db.execute(pr_stmt)

            # Log PR_CREATED event (store full normalized attributes for replayability)
            await self._log_event(
                repo_id=repo_id,
                event_type="PR_CREATED",
                actor=normalized_pr["author"],
                payload={
                    "source_github_id": normalized_pr["github_id"],
                    "number": normalized_pr["number"],
                    "title": normalized_pr["title"],
                    "state": normalized_pr["state"],
                    "author": normalized_pr["author"],
                    "created_at": normalized_pr["created_at"].isoformat() if normalized_pr["created_at"] else None,
                    "merged_at": normalized_pr["merged_at"].isoformat() if normalized_pr["merged_at"] else None,
                    "closed_at": normalized_pr["closed_at"].isoformat() if normalized_pr["closed_at"] else None,
                    "additions": normalized_pr["additions"],
                    "deletions": normalized_pr["deletions"],
                },
                idempotency_key=f"PR_CREATED:{repo_id}:{normalized_pr['github_id']}"
            )

            # Log PR_MERGED event if applicable
            if normalized_pr["state"] == "merged":
                await self._log_event(
                    repo_id=repo_id,
                    event_type="PR_MERGED",
                    actor=normalized_pr["author"],
                    payload={
                        "source_github_id": normalized_pr["github_id"],
                        "number": normalized_pr["number"],
                        "merged_at": normalized_pr["merged_at"].isoformat() if normalized_pr["merged_at"] else None,
                        "closed_at": normalized_pr["closed_at"].isoformat() if normalized_pr["closed_at"] else None
                    },
                    idempotency_key=f"PR_MERGED:{repo_id}:{normalized_pr['github_id']}"
                )

            # Get the PR ID for review mapping
            pr_result = await self.db.execute(
                select(PullRequest.id).where(
                    PullRequest.repo_id == repo_id,
                    PullRequest.github_id == normalized_pr["github_id"],
                )
            )
            pr_id = pr_result.scalar_one()

            # Normalize and upsert reviews
            reviews = (raw_pr.get("reviews") or {}).get("nodes", [])
            for raw_review in reviews:
                if not raw_review.get("databaseId"):
                    continue

                normalized_review = normalize_review(pr_id, raw_review)
                review_stmt = pg_insert(Review).values(**normalized_review)
                review_stmt = review_stmt.on_conflict_do_update(
                    constraint="uq_review_pr_github",
                    set_={
                        "state": review_stmt.excluded.state,
                    },
                )
                await self.db.execute(review_stmt)

                # Log REVIEW_SUBMITTED event (store full normalized attributes for replayability)
                await self._log_event(
                    repo_id=repo_id,
                    event_type="REVIEW_SUBMITTED",
                    actor=normalized_review["author"],
                    payload={
                        "source_github_id": normalized_review["github_id"],
                        "pr_github_id": normalized_pr["github_id"],
                        "author": normalized_review["author"],
                        "state": normalized_review["state"],
                        "submitted_at": normalized_review["submitted_at"].isoformat() if normalized_review["submitted_at"] else None
                    },
                    idempotency_key=f"REVIEW_SUBMITTED:{repo_id}:{normalized_review['github_id']}"
                )

            count += 1

        await self.db.flush()
        return count

    async def upsert_normalized_commits(self, repo_id: int, raw_commits: list[dict]) -> int:
        """Normalize and upsert commits, logging COMMIT_PUSHED events."""
        count = 0

        for raw_commit in raw_commits:
            if not raw_commit.get("oid"):
                continue

            normalized_commit = normalize_commit(repo_id, raw_commit)

            # Upsert the normalized Commit
            commit_stmt = pg_insert(Commit).values(**normalized_commit)
            commit_stmt = commit_stmt.on_conflict_do_nothing(
                index_elements=["sha"]
            )
            await self.db.execute(commit_stmt)

            # Log COMMIT_PUSHED event (store full normalized attributes for replayability)
            await self._log_event(
                repo_id=repo_id,
                event_type="COMMIT_PUSHED",
                actor=normalized_commit["author"],
                payload={
                    "source_github_id": normalized_commit["sha"],
                    "sha": normalized_commit["sha"],
                    "message": normalized_commit["message"],
                    "author": normalized_commit["author"],
                    "authored_at": normalized_commit["authored_at"].isoformat() if normalized_commit["authored_at"] else None
                },
                idempotency_key=f"COMMIT_PUSHED:{repo_id}:{normalized_commit['sha']}"
            )
            count += 1

        await self.db.flush()
        return count

