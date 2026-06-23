"""Metrics endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.metrics import (
    CycleTimeResponse,
    OverviewResponse,
    ReviewLatencyResponse,
    ThroughputResponse,
)
from app.services.insight_service import Insight, InsightService
from app.services.metrics_service import MetricsService

router = APIRouter()


@router.get("/overview", response_model=OverviewResponse)
async def get_overview(
    repo_id: int = Query(..., description="Repository ID"),
    db: AsyncSession = Depends(get_db),
):
    """Get an overview of all metrics for the dashboard.

    Returns cycle time, review latency, WIP, throughput,
    and weekly trend data in a single response.
    """
    service = MetricsService(db)
    return await service.overview(repo_id)


@router.get("/pr-cycle-time", response_model=CycleTimeResponse)
async def get_pr_cycle_time(
    repo_id: int = Query(..., description="Repository ID"),
    days: int = Query(30, ge=7, le=365, description="Period in days"),
    db: AsyncSession = Depends(get_db),
):
    """Get PR cycle time metrics.

    Cycle time = merged_at - created_at (in hours).
    Returns avg, median, p90, and weekly trend.
    """
    service = MetricsService(db)
    return await service.pr_cycle_time(repo_id, days)


@router.get("/review-latency", response_model=ReviewLatencyResponse)
async def get_review_latency(
    repo_id: int = Query(..., description="Repository ID"),
    days: int = Query(30, ge=7, le=365, description="Period in days"),
    db: AsyncSession = Depends(get_db),
):
    """Get review latency metrics.

    Review latency = time from PR creation to first review.
    Returns avg, median, p90, per-reviewer breakdown, and weekly trend.
    """
    service = MetricsService(db)
    return await service.review_latency(repo_id, days)


@router.get("/throughput", response_model=ThroughputResponse)
async def get_throughput(
    repo_id: int = Query(..., description="Repository ID"),
    weeks: int = Query(12, ge=4, le=52, description="Period in weeks"),
    db: AsyncSession = Depends(get_db),
):
    """Get PR throughput metrics.

    Returns weekly merged and opened PR counts,
    plus a rolling 4-week average.
    """
    service = MetricsService(db)
    return await service.throughput(repo_id, weeks)


@router.get("/insights")
async def get_insights(
    repo_id: int = Query(..., description="Repository ID"),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Get AI-generated insights based on current metrics.

    Uses rule-based anomaly detection to identify:
    - Cycle time spikes
    - Review bottlenecks
    - WIP overload
    - Throughput declines
    """
    metrics_service = MetricsService(db)
    overview = await metrics_service.overview(repo_id)

    insight_service = InsightService()
    insights = insight_service.generate_insights(overview)

    return [
        {
            "type": insight.type,
            "title": insight.title,
            "description": insight.description,
            "metric": insight.metric,
            "severity": insight.severity,
        }
        for insight in insights
    ]
