"""Anomaly detection service — detects engineering process outliers and bottlenecks."""

import logging
import math
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.data_plane.storage.models.pull_request import PullRequest
from app.data_plane.storage.models.review import Review
from app.schemas.anomalies import Anomaly

logger = logging.getLogger(__name__)


class AnomalyDetector:
    """Identifies process and workflow anomalies from repository data."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def detect_anomalies(self, repo_id: int, days: int = 30) -> list[Anomaly]:
        """Detect all anomalies for a given repository over the specified time range.

        Args:
            repo_id: Internal database ID of the repository.
            days: Lookback window in days.

        Returns:
            A list of detected Anomaly objects.
        """
        anomalies: list[Anomaly] = []
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        # 1. Fetch PRs for Cycle Time and PR Size analyses
        result = await self.db.execute(
            select(PullRequest)
            .where(
                PullRequest.repo_id == repo_id,
                PullRequest.created_at > cutoff
            )
        )
        prs = result.scalars().all()

        if not prs:
            return anomalies

        # Run detection functions
        anomalies.extend(self._detect_cycle_time_spikes(prs))
        anomalies.extend(self._detect_size_anomalies(prs))
        await self._detect_reviewer_bottlenecks(repo_id, cutoff, anomalies)
        await self._detect_wip_anomalies(repo_id, cutoff, anomalies)

        return anomalies

    def _detect_cycle_time_spikes(self, prs: list[PullRequest]) -> list[Anomaly]:
        """Identify PRs with cycle times exceeding 2 standard deviations from the mean."""
        anomalies = []
        merged_prs = [p for p in prs if p.state == "merged" and p.merged_at and p.created_at]

        if len(merged_prs) < 3:
            return anomalies

        cycle_times = [
            (p.merged_at - p.created_at).total_seconds() / 3600
            for p in merged_prs
        ]

        mean = sum(cycle_times) / len(cycle_times)
        variance = sum((x - mean) ** 2 for x in cycle_times) / len(cycle_times)
        std_dev = math.sqrt(variance)

        # We need a non-trivial std_dev to prevent division/range issues
        if std_dev < 1.0:
            std_dev = 1.0

        threshold = mean + 2 * std_dev

        for pr in merged_prs:
            ct = (pr.merged_at - pr.created_at).total_seconds() / 3600
            # Only flag if cycle time is above threshold and at least 24 hours
            if ct > threshold and ct > 24:
                anomalies.append(Anomaly(
                    type="cycle_time_spike",
                    title=f"Cycle Time Spike (PR #{pr.number})",
                    description=(
                        f"PR #{pr.number} took {ct:.1f} hours to merge. This is significantly "
                        f"higher than the repository average of {mean:.1f} hours (+2σ)."
                    ),
                    severity="high" if ct > 72 else "medium",
                    pr_number=pr.number,
                    author=pr.author,
                    value=round(ct, 1),
                ))

        return anomalies

    def _detect_size_anomalies(self, prs: list[PullRequest]) -> list[Anomaly]:
        """Identify unusually large PRs (>500 lines changed)."""
        anomalies = []

        for pr in prs:
            additions = pr.additions or 0
            deletions = pr.deletions or 0
            size = additions + deletions
            if size > 500:
                anomalies.append(Anomaly(
                    type="pr_size_anomaly",
                    title=f"Large PR: #{pr.number}",
                    description=(
                        f"PR #{pr.number} by @{pr.author} has {size} lines changed "
                        f"({additions} additions, {deletions} deletions). "
                        f"Large PRs delay code review and introduce regression risks."
                    ),
                    severity="high" if size > 1000 else "medium",
                    pr_number=pr.number,
                    author=pr.author,
                    value=float(size),
                ))

        return anomalies

    async def _detect_reviewer_bottlenecks(
        self, repo_id: int, cutoff: datetime, anomalies: list[Anomaly]
    ) -> None:
        """Flag single-reviewer bottleneck if one contributor performs >50% of all reviews."""
        query = text("""
            SELECT r.author, COUNT(*) as cnt
            FROM reviews r
            JOIN pull_requests pr ON pr.id = r.pr_id
            WHERE pr.repo_id = :repo_id
              AND pr.created_at > :cutoff
              AND r.author IS NOT NULL
            GROUP BY r.author
        """)
        result = await self.db.execute(query, {"repo_id": repo_id, "cutoff": cutoff})
        rows = result.all()

        total_reviews = sum(row.cnt for row in rows)
        if total_reviews >= 6:  # Need sufficient sample size to identify bottlenecks
            for row in rows:
                pct = (row.cnt / total_reviews) * 100
                if pct > 50:
                    anomalies.append(Anomaly(
                        type="reviewer_bottleneck",
                        title=f"Review Bottleneck: @{row.author}",
                        description=(
                            f"@{row.author} performed {row.cnt} reviews, which is {pct:.1f}% "
                            f"of all reviews in the last 30 days. High bus factor risk."
                        ),
                        severity="high" if pct > 70 else "medium",
                        pr_number=None,
                        author=row.author,
                        value=round(pct, 1),
                    ))

    async def _detect_wip_anomalies(
        self, repo_id: int, cutoff: datetime, anomalies: list[Anomaly]
    ) -> None:
        """Flag open work-in-progress overload relative to historical throughput."""
        # 1. Count currently open PRs
        open_result = await self.db.execute(
            select(func.count(PullRequest.id)).where(
                PullRequest.repo_id == repo_id,
                PullRequest.state == "open"
            )
        )
        try:
            wip = open_result.scalar_one()
            if not isinstance(wip, (int, float)):
                wip = 0
        except Exception:
            wip = 0

        # 2. Compute weekly throughput (merged PRs per week)
        throughput_query = text("""
            SELECT COUNT(*) as cnt
            FROM pull_requests
            WHERE repo_id = :repo_id
              AND state = 'merged'
              AND merged_at > :cutoff
        """)
        tp_result = await self.db.execute(throughput_query, {"repo_id": repo_id, "cutoff": cutoff})
        try:
            merged_count = tp_result.scalar_one()
            if not isinstance(merged_count, (int, float)):
                merged_count = 0
        except Exception:
            merged_count = 0

        # Average weekly merged
        weekly_throughput = merged_count / 4.2  # 30 days is ~4.2 weeks
        if weekly_throughput < 1.0:
            weekly_throughput = 1.0

        if wip > weekly_throughput * 2.5:
            anomalies.append(Anomaly(
                type="high_wip",
                title="WIP Overload Detected",
                description=(
                    f"{wip} concurrent open PRs vs {weekly_throughput:.1f}/week throughput. "
                    f"WIP exceeds 2.5x weekly throughput — context switching is harming delivery velocity."
                ),
                severity="high" if wip > weekly_throughput * 4.0 else "medium",
                pr_number=None,
                author=None,
                value=float(wip),
            ))
