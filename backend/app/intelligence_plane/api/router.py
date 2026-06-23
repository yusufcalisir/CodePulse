"""Aggregate API router for the Intelligence Plane."""

from fastapi import APIRouter

from app.intelligence_plane.api import health, metrics, repos, anomalies

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(health.router, tags=["health"])
api_router.include_router(repos.router, prefix="/repos", tags=["repositories"])
api_router.include_router(metrics.router, prefix="/metrics", tags=["metrics"])
api_router.include_router(anomalies.router, prefix="/anomalies", tags=["anomalies"])
