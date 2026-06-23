"""Metrics computation engine — the core of CodePulse.

All metrics are computed via SQL queries against PostgreSQL.
Uses window functions, PERCENTILE_CONT, and LATERAL joins for efficiency.
"""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.data_plane.storage.models.pull_request import PullRequest
from app.data_plane.storage.models.review import Review
from app.data_plane.storage.models.repo_metrics_daily import RepoMetricsDaily
from app.schemas.metrics import (
    ContributorMetric,
    CycleTimeResponse,
    OverviewMetrics,
    OverviewResponse,
    ReviewLatencyResponse,
    StatSummary,
    ThroughputResponse,
    ThroughputWeek,
    WeeklyDataPoint,
)

logger = logging.getLogger(__name__)


class MetricsService:
    """Computes engineering metrics from stored GitHub data."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── PR Cycle Time ─────────────────────────────────────────

    async def pr_cycle_time(
        self, repo_id: int, days: int = 30
    ) -> CycleTimeResponse:
        """Calculate PR cycle time (merged_at - created_at) in hours.

        Returns summary stats (avg, median, p90) and weekly trend.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        # Summary stats
        summary_query = text("""
            SELECT
                COALESCE(SUM(cycle_time_avg * throughput_merged) / NULLIF(SUM(throughput_merged), 0), 0) as avg_hours,
                COALESCE(SUM(cycle_time_median * throughput_merged) / NULLIF(SUM(throughput_merged), 0), 0) as median_hours,
                COALESCE(SUM(cycle_time_p90 * throughput_merged) / NULLIF(SUM(throughput_merged), 0), 0) as p90_hours
            FROM repo_metrics_daily
            WHERE repo_id = :repo_id
              AND date >= :cutoff
        """)

        result = await self.db.execute(
            summary_query, {"repo_id": repo_id, "cutoff": cutoff}
        )
        row = result.one()

        summary = StatSummary(
            avg=round(row.avg_hours, 1),
            median=round(row.median_hours, 1),
            p90=round(row.p90_hours, 1),
        )

        # Weekly trend
        trend_query = text("""
            SELECT
                TO_CHAR(DATE_TRUNC('week', date), 'IYYY-"W"IW') as week,
                COALESCE(SUM(cycle_time_avg * throughput_merged) / NULLIF(SUM(throughput_merged), 0), 0) as avg_hours,
                SUM(throughput_merged) as count
            FROM repo_metrics_daily
            WHERE repo_id = :repo_id
              AND date >= :cutoff
            GROUP BY DATE_TRUNC('week', date)
            ORDER BY DATE_TRUNC('week', date)
        """)

        result = await self.db.execute(
            trend_query, {"repo_id": repo_id, "cutoff": cutoff}
        )
        trend = [
            WeeklyDataPoint(
                week=row.week,
                value=round(row.avg_hours, 1),
                count=row.count,
            )
            for row in result.all()
        ]

        return CycleTimeResponse(
            summary=summary, trend=trend, period_days=days
        )

    # ── Review Latency ────────────────────────────────────────

    async def review_latency(
        self, repo_id: int, days: int = 30
    ) -> ReviewLatencyResponse:
        """Calculate time from PR creation to first review.

        Returns summary stats, per-reviewer breakdown, and weekly trend.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        # Summary — first review latency
        summary_query = text("""
            SELECT
                COALESCE(SUM(review_latency_avg * throughput_opened) / NULLIF(SUM(throughput_opened), 0), 0) as avg_hours,
                COALESCE(SUM(review_latency_median * throughput_opened) / NULLIF(SUM(throughput_opened), 0), 0) as median_hours,
                COALESCE(SUM(review_latency_p90 * throughput_opened) / NULLIF(SUM(throughput_opened), 0), 0) as p90_hours
            FROM repo_metrics_daily
            WHERE repo_id = :repo_id
              AND date >= :cutoff
        """)

        result = await self.db.execute(
            summary_query, {"repo_id": repo_id, "cutoff": cutoff}
        )
        row = result.one()

        summary = StatSummary(
            avg=round(row.avg_hours, 1),
            median=round(row.median_hours, 1),
            p90=round(row.p90_hours, 1),
        )

        # By reviewer breakdown (remain dynamic as it is secondary / per-user metrics)
        reviewer_query = text("""
            WITH review_latencies AS (
                SELECT
                    r.author,
                    EXTRACT(EPOCH FROM (r.submitted_at - pr.created_at)) / 3600 as latency_hours
                FROM reviews r
                JOIN pull_requests pr ON pr.id = r.pr_id
                WHERE pr.repo_id = :repo_id
                  AND pr.created_at > :cutoff
                  AND r.author IS NOT NULL
            )
            SELECT
                author,
                AVG(latency_hours) as avg_hours,
                COUNT(*) as review_count
            FROM review_latencies
            GROUP BY author
            ORDER BY avg_hours ASC
        """)

        result = await self.db.execute(
            reviewer_query, {"repo_id": repo_id, "cutoff": cutoff}
        )
        by_reviewer = [
            ContributorMetric(
                author=row.author,
                avg=round(row.avg_hours, 1),
                count=row.review_count,
            )
            for row in result.all()
        ]

        # Weekly trend
        trend_query = text("""
            SELECT
                TO_CHAR(DATE_TRUNC('week', date), 'IYYY-"W"IW') as week,
                COALESCE(SUM(review_latency_avg * throughput_opened) / NULLIF(SUM(throughput_opened), 0), 0) as avg_hours,
                SUM(throughput_opened) as count
            FROM repo_metrics_daily
            WHERE repo_id = :repo_id
              AND date >= :cutoff
            GROUP BY DATE_TRUNC('week', date)
            ORDER BY DATE_TRUNC('week', date)
        """)

        result = await self.db.execute(
            trend_query, {"repo_id": repo_id, "cutoff": cutoff}
        )
        trend = [
            WeeklyDataPoint(
                week=row.week,
                value=round(row.avg_hours, 1),
                count=row.count,
            )
            for row in result.all()
        ]

        return ReviewLatencyResponse(
            summary=summary,
            by_reviewer=by_reviewer,
            trend=trend,
            period_days=days,
        )

    # ── WIP (Work in Progress) ────────────────────────────────

    async def wip_count(self, repo_id: int) -> int:
        """Fetch the latest cached WIP count from precomputed daily metrics."""
        result = await self.db.execute(
            select(RepoMetricsDaily.wip)
            .where(RepoMetricsDaily.repo_id == repo_id)
            .order_by(RepoMetricsDaily.date.desc())
            .limit(1)
        )
        val = result.scalar_one_or_none()
        return val if val is not None else 0

    # ── Throughput ────────────────────────────────────────────

    async def throughput(
        self, repo_id: int, weeks: int = 12
    ) -> ThroughputResponse:
        """Calculate weekly throughput (merged and opened PRs).

        Returns weekly counts and a rolling 4-week average.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(weeks=weeks)

        # Weekly merged + opened
        query = text("""
            WITH weeks AS (
                SELECT generate_series(
                    DATE_TRUNC('week', :cutoff::timestamptz),
                    DATE_TRUNC('week', NOW()),
                    '1 week'::interval
                ) as week_start
            ),
            weekly_agg AS (
                SELECT
                    DATE_TRUNC('week', date) as week_start,
                    SUM(throughput_merged) as merged,
                    SUM(throughput_opened) as opened
                FROM repo_metrics_daily
                WHERE repo_id = :repo_id AND date >= :cutoff
                GROUP BY DATE_TRUNC('week', date)
            )
            SELECT
                TO_CHAR(w.week_start, 'IYYY-"W"IW') as week,
                COALESCE(wa.merged, 0) as merged,
                COALESCE(wa.opened, 0) as opened
            FROM weeks w
            LEFT JOIN weekly_agg wa ON wa.week_start = w.week_start
            ORDER BY w.week_start
        """)

        result = await self.db.execute(
            query, {"repo_id": repo_id, "cutoff": cutoff}
        )
        weekly = [
            ThroughputWeek(week=row.week, merged=row.merged, opened=row.opened)
            for row in result.all()
        ]

        # Rolling 4-week average of merged PRs
        recent_merged = [w.merged for w in weekly[-4:]] if weekly else [0]
        rolling_avg = round(sum(recent_merged) / max(len(recent_merged), 1), 1)

        return ThroughputResponse(
            weekly=weekly, rolling_avg=rolling_avg, period_weeks=weeks
        )

    # ── Overview (Dashboard) ──────────────────────────────────

    async def overview(self, repo_id: int) -> OverviewResponse:
        """Compute all dashboard metrics in one call."""
        cycle_time = await self.pr_cycle_time(repo_id, days=30)
        review_lat = await self.review_latency(repo_id, days=30)
        wip = await self.wip_count(repo_id)
        throughput_data = await self.throughput(repo_id, weeks=12)

        # Current week throughput
        current_week_merged = throughput_data.weekly[-1].merged if throughput_data.weekly else 0

        metrics = OverviewMetrics(
            cycle_time=cycle_time.summary,
            review_latency=review_lat.summary,
            wip=wip,
            throughput_current_week=current_week_merged,
            throughput_avg_4_week=throughput_data.rolling_avg,
        )

        return OverviewResponse(
            metrics=metrics,
            cycle_time_trend=cycle_time.trend,
            throughput_trend=throughput_data.weekly,
        )
