"""Event Replay Service — reconstructs database state tables from the immutable events log."""

import logging
from datetime import datetime
from sqlalchemy import select, delete
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.data_plane.storage.models.commit import Commit
from app.data_plane.storage.models.pull_request import PullRequest
from app.data_plane.storage.models.review import Review
from app.data_plane.storage.models.repository import Repository
from app.data_plane.storage.models.event import Event
from app.intelligence_plane.metrics.precomputer import MetricsPrecomputer

logger = logging.getLogger(__name__)


class ReplayService:
    """Replays events sequentially to reconstruct database state tables."""

    @staticmethod
    async def replay_repository_events(db: AsyncSession, repo_id: int) -> int:
        """Deletes current state tables for a repository and rebuilds them from events logs.

        Args:
            db: SQLAlchemy AsyncSession.
            repo_id: Internal database ID of the repository.

        Returns:
            The number of replayed events.
        """
        # 1. Verify repository exists
        repo_result = await db.execute(
            select(Repository).where(Repository.id == repo_id)
        )
        repo = repo_result.scalar_one_or_none()
        if not repo:
            raise ValueError(f"Repository with ID {repo_id} not found")

        logger.info("Replay engine: Starting event replay for %s", repo.full_name)

        # 2. Delete existing state records for this repository
        # Delete reviews (connected to pull requests of this repo)
        await db.execute(
            delete(Review).where(Review.pr_id.in_(
                select(PullRequest.id).where(PullRequest.repo_id == repo_id)
            ))
        )
        # Delete pull requests
        await db.execute(
            delete(PullRequest).where(PullRequest.repo_id == repo_id)
        )
        # Delete commits
        await db.execute(
            delete(Commit).where(Commit.repo_id == repo_id)
        )
        await db.flush()

        # 3. Retrieve all events for this repository in sequential order
        events_result = await db.execute(
            select(Event).where(Event.repo_id == repo_id).order_by(Event.id.asc())
        )
        events = events_result.scalars().all()
        logger.info("Replay engine: Fetched %d events to replay.", len(events))

        replayed_count = 0

        # Helper to parse ISO format string
        def parse_iso(dt_str: str | None) -> datetime | None:
            if not dt_str:
                return None
            try:
                # fromisoformat handles +00:00 format
                return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
            except ValueError:
                return None

        # 4. Sequentially process and reconstruct
        for event in events:
            payload = event.payload
            
            if event.type == "PR_CREATED":
                pr_values = {
                    "repo_id": repo_id,
                    "github_id": payload["source_github_id"],
                    "number": payload["number"],
                    "title": payload.get("title"),
                    "state": payload.get("state", "open").lower(),
                    "author": payload.get("author") or event.actor,
                    "created_at": parse_iso(payload.get("created_at")),
                    "merged_at": parse_iso(payload.get("merged_at")),
                    "closed_at": parse_iso(payload.get("closed_at")),
                    "additions": payload.get("additions", 0),
                    "deletions": payload.get("deletions", 0),
                }
                
                pr_stmt = pg_insert(PullRequest).values(**pr_values)
                pr_stmt = pr_stmt.on_conflict_do_update(
                    constraint="uq_pr_repo_github",
                    set_={
                        "state": pr_stmt.excluded.state,
                        "title": pr_stmt.excluded.title,
                        "merged_at": pr_stmt.excluded.merged_at,
                        "closed_at": pr_stmt.excluded.closed_at,
                        "additions": pr_stmt.excluded.additions,
                        "deletions": pr_stmt.excluded.deletions,
                    }
                )
                await db.execute(pr_stmt)
                replayed_count += 1

            elif event.type == "PR_MERGED":
                # Find parent PR and update status
                github_id = payload["source_github_id"]
                pr_result = await db.execute(
                    select(PullRequest).where(
                        PullRequest.repo_id == repo_id,
                        PullRequest.github_id == github_id,
                    )
                )
                pr = pr_result.scalar_one_or_none()
                if pr:
                    pr.state = "merged"
                    pr.merged_at = parse_iso(payload.get("merged_at"))
                    pr.closed_at = parse_iso(payload.get("closed_at"))
                replayed_count += 1

            elif event.type == "REVIEW_SUBMITTED":
                pr_github_id = payload["pr_github_id"]
                
                # Retrieve parent PR
                pr_result = await db.execute(
                    select(PullRequest.id).where(
                        PullRequest.repo_id == repo_id,
                        PullRequest.github_id == pr_github_id,
                    )
                )
                pr_id = pr_result.scalar_one_or_none()
                
                if pr_id:
                    review_values = {
                        "pr_id": pr_id,
                        "github_id": payload["source_github_id"],
                        "author": payload.get("author") or event.actor,
                        "state": payload.get("state", "COMMENTED"),
                        "submitted_at": parse_iso(payload.get("submitted_at")),
                    }
                    
                    review_stmt = pg_insert(Review).values(**review_values)
                    review_stmt = review_stmt.on_conflict_do_update(
                        constraint="uq_review_pr_github",
                        set_={
                            "state": review_stmt.excluded.state,
                        }
                    )
                    await db.execute(review_stmt)
                replayed_count += 1

            elif event.type == "COMMIT_PUSHED":
                commit_values = {
                    "repo_id": repo_id,
                    "sha": payload["sha"],
                    "message": payload.get("message"),
                    "author": payload.get("author") or event.actor,
                    "authored_at": parse_iso(payload.get("authored_at")),
                }
                
                commit_stmt = pg_insert(Commit).values(**commit_values)
                commit_stmt = commit_stmt.on_conflict_do_nothing(
                    index_elements=["sha"]
                )
                await db.execute(commit_stmt)
                replayed_count += 1

        await db.flush()

        # 5. Recompute metrics for this repository
        precomputer = MetricsPrecomputer(db)
        await precomputer.precompute_repository_metrics(repo_id)

        logger.info(
            "Replay engine: Finished event replay for %s. Replayed %d events and precomputed daily metrics.",
            repo.full_name,
            replayed_count,
        )

        return replayed_count
