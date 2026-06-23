"""Integration tests for backend API routes (api/v1/)."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.data_plane.storage.models.repository import Repository
from app.data_plane.storage.models.sync_log import SyncLog
from app.schemas.metrics import (
    CycleTimeResponse,
    OverviewMetrics,
    OverviewResponse,
    StatSummary,
    ThroughputResponse,
)
from tests.conftest import MockResult


@pytest.mark.asyncio
async def test_health_check_endpoint(client: AsyncClient) -> None:
    """Test GET /api/v1/health returns success."""
    res = await client.get("/api/v1/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "service" in data


@pytest.mark.asyncio
async def test_list_repositories(client: AsyncClient, mock_db: AsyncMock) -> None:
    """Test GET /api/v1/repos returns list of repositories."""
    repo = Repository(
        id=1,
        github_id=123,
        name="codepulse",
        full_name="org/codepulse",
        org="org",
        default_branch="main",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    mock_db.execute.return_value = MockResult(rows=[repo], scalar_rows=[repo])

    res = await client.get("/api/v1/repos")
    assert res.status_code == 200
    data = res.json()
    assert "repositories" in data
    assert len(data["repositories"]) == 1
    assert data["repositories"][0]["full_name"] == "org/codepulse"
    assert data["count"] == 1


@pytest.mark.asyncio
async def test_get_repository_not_found(
    client: AsyncClient, mock_db: AsyncMock
) -> None:
    """Test GET /api/v1/repos/{id} returns 404 on missing repo."""
    mock_db.execute.return_value = MockResult(rows=[], scalar_rows=[])

    res = await client.get("/api/v1/repos/99")
    assert res.status_code == 404
    assert res.json()["detail"] == "Repository 99 not found or access denied for organization test_org"


@pytest.mark.asyncio
async def test_sync_repository_trigger(
    client: AsyncClient, mock_db: AsyncMock
) -> None:
    """Test POST /api/v1/repos/sync schedules background sync."""
    # First lookup returns None (repo doesn't exist, we will create it)
    mock_db.execute.return_value = MockResult(rows=[], scalar_rows=[])

    with patch("app.intelligence_plane.api.repos.BackgroundTasks.add_task") as mock_add_task:
        res = await client.post(
            "/api/v1/repos/sync", json={"full_name": "org/codepulse"}
        )
        assert res.status_code == 202
        data = res.json()
        assert data["status"] == "running"
        assert "started" in data["message"]
        mock_add_task.assert_called_once()


@pytest.mark.asyncio
async def test_get_sync_status(client: AsyncClient, mock_db: AsyncMock) -> None:
    """Test GET /api/v1/repos/{id}/sync-status returns latest log."""
    sync_log = SyncLog(
        id=5,
        repo_id=1,
        status="completed",
        pr_count=45,
        started_at=datetime.now(timezone.utc),
        finished_at=datetime.now(timezone.utc),
    )
    mock_db.execute.return_value = MockResult(rows=[sync_log], scalar_rows=[sync_log])

    res = await client.get("/api/v1/repos/1/sync-status")
    assert res.status_code == 200
    data = res.json()
    assert data["sync_id"] == 5
    assert data["status"] == "completed"
    assert data["pr_count"] == 45


@pytest.mark.asyncio
async def test_get_metrics_overview(client: AsyncClient, mock_db: AsyncMock) -> None:
    """Test GET /api/v1/metrics/overview maps to metrics service correctly."""
    repo = Repository(id=1, github_id=123, name="codepulse", full_name="org/codepulse", org_id="test_org")
    mock_db.execute.return_value = MockResult(rows=[repo], scalar_rows=[repo])

    mock_overview_res = OverviewResponse(
        metrics=OverviewMetrics(
            cycle_time=StatSummary(avg=18.5, median=12.3, p90=42.1),
            review_latency=StatSummary(avg=4.2, median=2.1, p90=12.0),
            wip=7,
            throughput_current_week=12,
            throughput_avg_4_week=15.5,
        ),
        cycle_time_trend=[],
        throughput_trend=[],
    )

    with patch(
        "app.intelligence_plane.metrics.metrics_service.MetricsService.overview",
        new_callable=AsyncMock,
    ) as mock_overview:
        mock_overview.return_value = mock_overview_res

        res = await client.get("/api/v1/metrics/overview?repo_id=1")
        assert res.status_code == 200
        data = res.json()
        assert data["metrics"]["wip"] == 7
        assert data["metrics"]["cycle_time"]["median"] == 12.3
        mock_overview.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_get_insights_endpoint(client: AsyncClient, mock_db: AsyncMock) -> None:
    """Test GET /api/v1/metrics/insights handles mock metrics and returns structured layers."""
    repo = Repository(id=1, github_id=123, name="codepulse", full_name="org/codepulse", org_id="test_org")
    mock_db.execute.return_value = MockResult(rows=[repo], scalar_rows=[repo])

    mock_overview_res = OverviewResponse(
        metrics=OverviewMetrics(
            # Median ct is 55h (> 24h warning), wip = 12 (> 2.5x throughput)
            cycle_time=StatSummary(avg=50.0, median=55.0, p90=200.0), # p90 > median * 3 (percentile shift)
            review_latency=StatSummary(avg=4.2, median=2.1, p90=12.0),
            wip=12,
            throughput_current_week=5,
            throughput_avg_4_week=4.0,
        ),
        cycle_time_trend=[],
        throughput_trend=[],
    )

    with patch(
        "app.intelligence_plane.metrics.metrics_service.MetricsService.overview",
        new_callable=AsyncMock,
    ) as mock_overview, patch(
        "app.intelligence_plane.api.metrics.AnomalyDetector.detect_anomalies",
        new_callable=AsyncMock,
    ) as mock_detect_anomalies:
        mock_overview.return_value = mock_overview_res
        
        # Mock some rule anomalies
        from app.schemas.anomalies import Anomaly
        mock_detect_anomalies.return_value = [
            Anomaly(
                type="reviewer_bottleneck",
                title="Review Bottleneck: @alice",
                description="@alice did 60% of all reviews.",
                severity="high",
                pr_number=None,
                author="alice",
                value=60.0
            )
        ]

        res = await client.get("/api/v1/metrics/insights?repo_id=1")
        assert res.status_code == 200
        data = res.json()
        
        # Verify 3-layer structure
        assert "rule_engine" in data
        assert "statistical_layer" in data
        assert "llm_layer" in data

        # 1. Rule Engine Layer
        assert len(data["rule_engine"]) == 1
        assert data["rule_engine"][0]["type"] == "bottleneck"
        assert "@alice" in data["rule_engine"][0]["title"]

        # 2. Statistical Layer
        assert len(data["statistical_layer"]) >= 1
        assert data["statistical_layer"][0]["type"] == "percentile_shift"

        # 3. LLM / Interpretive Layer
        assert "why_did_this_happen" in data["llm_layer"]
        assert "executive_summary" in data["llm_layer"]
        assert "bottleneck on @alice" in data["llm_layer"]["executive_summary"]


@pytest.mark.asyncio
async def test_replay_repository_events_endpoint(client: AsyncClient, mock_db: AsyncMock) -> None:
    """Test POST /api/v1/repos/{id}/replay returns success."""
    repo = Repository(id=1, github_id=123, name="codepulse", full_name="org/codepulse", org_id="test_org")
    mock_db.execute.return_value = MockResult(rows=[repo], scalar_rows=[repo])

    with patch(
        "app.intelligence_plane.api.repos.ReplayService.replay_repository_events",
        new_callable=AsyncMock,
    ) as mock_replay:
        mock_replay.return_value = 5
        
        res = await client.post("/api/v1/repos/1/replay")
        assert res.status_code == 200
        data = res.json()
        assert data["replayed_count"] == 5
        assert "Successfully replayed 5 events" in data["message"]
        mock_replay.assert_called_once()


