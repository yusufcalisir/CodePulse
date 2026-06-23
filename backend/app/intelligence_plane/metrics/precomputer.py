"""Metrics Precomputer — handles precalculating metrics for a repository."""

import logging
from datetime import date
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.data_plane.storage.models.repo_metrics_daily import RepoMetricsDaily

logger = logging.getLogger(__name__)


class MetricsPrecomputer:
    """Precomputes daily metrics for repositories and caches them in aggregated tables."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def precompute_repository_metrics(self, repo_id: int, days: int = 90) -> None:
        """Calculate daily metrics for the last N days and upsert them into repo_metrics_daily."""
        if repo_id is None:
            logger.warning("Skipping precompute: repo_id is None")
            return

        query = text(f"""
            WITH date_series AS (
                SELECT (generate_series(
                    DATE_TRUNC('day', NOW() - INTERVAL '{days} days'),
                    DATE_TRUNC('day', NOW()),
                    '1 day'::interval
                ))::date as d
            ),
            daily_throughput AS (
                SELECT
                    DATE(merged_at) as d,
                    COUNT(*) as merged_count,
                    COALESCE(AVG(EXTRACT(EPOCH FROM (merged_at - created_at)) / 3600), 0) as cycle_avg,
                    COALESCE(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM (merged_at - created_at)) / 3600), 0) as cycle_med,
                    COALESCE(PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM (merged_at - created_at)) / 3600), 0) as cycle_p90
                FROM pull_requests
                WHERE repo_id = :repo_id AND state = 'merged'
                GROUP BY DATE(merged_at)
            ),
            daily_opened AS (
                SELECT
                    DATE(created_at) as d,
                    COUNT(*) as opened_count
                FROM pull_requests
                WHERE repo_id = :repo_id
                GROUP BY DATE(created_at)
            ),
            first_reviews AS (
                SELECT
                    pr.id as pr_id,
                    pr.created_at as pr_created,
                    MIN(r.submitted_at) as first_review_at
                FROM pull_requests pr
                JOIN reviews r ON r.pr_id = pr.id
                WHERE pr.repo_id = :repo_id
                GROUP BY pr.id, pr.created_at
            ),
            daily_reviews AS (
                SELECT
                    DATE(pr_created) as d,
                    COALESCE(AVG(EXTRACT(EPOCH FROM (first_review_at - pr_created)) / 3600), 0) as review_avg,
                    COALESCE(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM (first_review_at - pr_created)) / 3600), 0) as review_med,
                    COALESCE(PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM (first_review_at - pr_created)) / 3600), 0) as review_p90
                FROM first_reviews
                GROUP BY DATE(pr_created)
            ),
            daily_wip AS (
                SELECT
                    ds.d,
                    COUNT(pr.id) as wip_count
                FROM date_series ds
                LEFT JOIN pull_requests pr ON pr.repo_id = :repo_id
                    AND DATE(pr.created_at) <= ds.d
                    AND (pr.closed_at IS NULL OR DATE(pr.closed_at) > ds.d)
                GROUP BY ds.d
            )
            SELECT
                ds.d as date,
                COALESCE(dt.cycle_avg, 0) as cycle_time_avg,
                COALESCE(dt.cycle_med, 0) as cycle_time_median,
                COALESCE(dt.cycle_p90, 0) as cycle_time_p90,
                COALESCE(dr.review_avg, 0) as review_latency_avg,
                COALESCE(dr.review_med, 0) as review_latency_median,
                COALESCE(dr.review_p90, 0) as review_latency_p90,
                COALESCE(dt.merged_count, 0) as throughput_merged,
                COALESCE(do.opened_count, 0) as throughput_opened,
                COALESCE(dw.wip_count, 0) as wip
            FROM date_series ds
            LEFT JOIN daily_throughput dt ON dt.d = ds.d
            LEFT JOIN daily_opened "do" ON "do".d = ds.d
            LEFT JOIN daily_reviews dr ON dr.d = ds.d
            LEFT JOIN daily_wip dw ON dw.d = ds.d
            ORDER BY ds.d
        """)

        try:
            result = await self.db.execute(query, {"repo_id": repo_id})
            rows = result.all()

            for row in rows:
                stmt = pg_insert(RepoMetricsDaily).values(
                    repo_id=repo_id,
                    date=row.date,
                    cycle_time_avg=row.cycle_time_avg,
                    cycle_time_median=row.cycle_time_median,
                    cycle_time_p90=row.cycle_time_p90,
                    review_latency_avg=row.review_latency_avg,
                    review_latency_median=row.review_latency_median,
                    review_latency_p90=row.review_latency_p90,
                    throughput_merged=row.throughput_merged,
                    throughput_opened=row.throughput_opened,
                    wip=row.wip,
                )
                stmt = stmt.on_conflict_do_update(
                    constraint="uq_repo_metrics_date",
                    set_={
                        "cycle_time_avg": stmt.excluded.cycle_time_avg,
                        "cycle_time_median": stmt.excluded.cycle_time_median,
                        "cycle_time_p90": stmt.excluded.cycle_time_p90,
                        "review_latency_avg": stmt.excluded.review_latency_avg,
                        "review_latency_median": stmt.excluded.review_latency_median,
                        "review_latency_p90": stmt.excluded.review_latency_p90,
                        "throughput_merged": stmt.excluded.throughput_merged,
                        "throughput_opened": stmt.excluded.throughput_opened,
                        "wip": stmt.excluded.wip,
                    }
                )
                await self.db.execute(stmt)

            await self.db.flush()
            logger.info("Precomputed metrics for repo %s: %d daily rows updated", repo_id, len(rows))
        except Exception as e:
            logger.error("Failed to precompute metrics for repo %s: %s", repo_id, e)
            raise
