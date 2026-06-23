"""Anomalies detection API endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.data_plane.storage.models.repository import Repository
from app.intelligence_plane.api.dependencies import verify_repo_access_query
from app.schemas.anomalies import Anomaly
from app.intelligence_plane.anomalies.anomaly_detector import AnomalyDetector

router = APIRouter()


@router.get("", response_model=list[Anomaly])
async def get_anomalies(
    days: int = Query(30, ge=7, le=90, description="Period in days"),
    repo: Repository = Depends(verify_repo_access_query),
    db: AsyncSession = Depends(get_db),
):
    """Detect and return process exceptions and bottlenecks for the repository.

    Identifies:
    - Cycle time spikes (+2 standard deviations)
    - Exceptionally large PR size anomalies (>500 lines changed)
    - Reviewer hotspots/bottlenecks
    - High work-in-progress relative to throughput
    """
    detector = AnomalyDetector(db)
    return await detector.detect_anomalies(repo.id, days)

