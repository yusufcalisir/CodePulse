"""Metrics and Insights endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.data_plane.storage.models.repository import Repository
from app.intelligence_plane.api.dependencies import verify_repo_access_query
from app.schemas.metrics import (
    CycleTimeResponse,
    OverviewResponse,
    ReviewLatencyResponse,
    ThroughputResponse,
)
from app.intelligence_plane.insights.insight_service import InsightService
from app.intelligence_plane.metrics.metrics_service import MetricsService
from app.intelligence_plane.anomalies.anomaly_detector import AnomalyDetector
from app.schemas.insights import InsightsResponse

router = APIRouter()


@router.get("/overview", response_model=OverviewResponse)
async def get_overview(
    repo: Repository = Depends(verify_repo_access_query),
    db: AsyncSession = Depends(get_db),
):
    """Get an overview of all metrics for the dashboard.

    Returns cycle time, review latency, WIP, throughput,
    and weekly trend data in a single response.
    """
    service = MetricsService(db)
    return await service.overview(repo.id)


@router.get("/pr-cycle-time", response_model=CycleTimeResponse)
async def get_pr_cycle_time(
    days: int = Query(30, ge=7, le=365, description="Period in days"),
    repo: Repository = Depends(verify_repo_access_query),
    db: AsyncSession = Depends(get_db),
):
    """Get PR cycle time metrics.

    Cycle time = merged_at - created_at (in hours).
    Returns avg, median, p90, and weekly trend.
    """
    service = MetricsService(db)
    return await service.pr_cycle_time(repo.id, days)


@router.get("/review-latency", response_model=ReviewLatencyResponse)
async def get_review_latency(
    days: int = Query(30, ge=7, le=365, description="Period in days"),
    repo: Repository = Depends(verify_repo_access_query),
    db: AsyncSession = Depends(get_db),
):
    """Get review latency metrics.

    Review latency = time from PR creation to first review.
    Returns avg, median, p90, per-reviewer breakdown, and weekly trend.
    """
    service = MetricsService(db)
    return await service.review_latency(repo.id, days)


@router.get("/throughput", response_model=ThroughputResponse)
async def get_throughput(
    weeks: int = Query(12, ge=4, le=52, description="Period in weeks"),
    repo: Repository = Depends(verify_repo_access_query),
    db: AsyncSession = Depends(get_db),
):
    """Get PR throughput metrics.

    Returns weekly merged and opened PR counts,
    plus a rolling 4-week average.
    """
    service = MetricsService(db)
    return await service.throughput(repo.id, weeks)


@router.get("/insights", response_model=InsightsResponse)
async def get_insights(
    repo: Repository = Depends(verify_repo_access_query),
    db: AsyncSession = Depends(get_db),
):
    """Get multi-layered product-core insights based on metrics and anomalies.

    Returns deterministic rule insights, statistical trend/percentile deviations,
    and an interpretive executive explanation.
    """
    metrics_service = MetricsService(db)
    overview = await metrics_service.overview(repo.id)

    anomaly_detector = AnomalyDetector(db)
    anomalies = await anomaly_detector.detect_anomalies(repo.id)

    insight_service = InsightService()
    return insight_service.generate_structured_insights(overview, anomalies)


