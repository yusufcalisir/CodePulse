"""Unit tests for the metrics service (metrics_service.py)."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.intelligence_plane.metrics.metrics_service import MetricsService
from tests.conftest import MockResult


@pytest.mark.asyncio
async def test_pr_cycle_time_success(mock_db: AsyncMock) -> None:
    """Test cycle time metric calculations with mocked DB results."""
    service = MetricsService(db=mock_db)

    # Mock DB response for summary and weekly trend queries
    summary_row = MagicMock(avg_hours=18.52, median_hours=12.34, p90_hours=42.11)
    trend_row_1 = MagicMock(week="2026-W22", avg_hours=12.34, count=14)
    trend_row_2 = MagicMock(week="2026-W23", avg_hours=11.20, count=12)

    def mock_execute(stmt, *args, **kwargs):
        stmt_str = str(stmt).lower()
        if "cycle_time_avg" in stmt_str and "date_trunc" not in stmt_str:
            # Summary query
            return MockResult(rows=[summary_row])
        elif "date_trunc" in stmt_str:
            # Trend query
            return MockResult(rows=[trend_row_1, trend_row_2])
        return MockResult()

    mock_db.execute.side_effect = mock_execute

    res = await service.pr_cycle_time(repo_id=1, days=30)

    # Asserts rounding logic (1 decimal place) and parsing
    assert res.summary.avg == 18.5
    assert res.summary.median == 12.3
    assert res.summary.p90 == 42.1

    assert len(res.trend) == 2
    assert res.trend[0].week == "2026-W22"
    assert res.trend[0].value == 12.3
    assert res.trend[0].count == 14
    assert res.trend[1].value == 11.2


@pytest.mark.asyncio
async def test_review_latency_success(mock_db: AsyncMock) -> None:
    """Test review latency calculations and reviewer breakdown parsing."""
    service = MetricsService(db=mock_db)

    summary_row = MagicMock(avg_hours=4.22, median_hours=2.11, p90_hours=12.01)
    reviewer_row_1 = MagicMock(author="alice", avg_hours=2.1, review_count=8)
    reviewer_row_2 = MagicMock(author="bob", avg_hours=6.3, review_count=4)
    trend_row = MagicMock(week="2026-W22", avg_hours=4.2, count=12)

    def mock_execute(stmt, *args, **kwargs):
        stmt_str = str(stmt).lower()
        if "review_latency_avg" in stmt_str:
            if "date_trunc" in stmt_str or "to_char" in stmt_str:
                # Weekly trend query (uses to_char)
                return MockResult(rows=[trend_row])
            else:
                # Summary query
                return MockResult(rows=[summary_row])
        elif "review_latencies" in stmt_str:
            # By reviewer query
            return MockResult(rows=[reviewer_row_1, reviewer_row_2])
        return MockResult()

    mock_db.execute.side_effect = mock_execute

    res = await service.review_latency(repo_id=1, days=30)

    assert res.summary.avg == 4.2
    assert res.summary.median == 2.1
    assert res.summary.p90 == 12.0

    assert len(res.by_reviewer) == 2
    assert res.by_reviewer[0].author == "alice"
    assert res.by_reviewer[0].avg == 2.1
    assert res.by_reviewer[0].count == 8

    assert len(res.trend) == 1
    assert res.trend[0].week == "2026-W22"


@pytest.mark.asyncio
async def test_wip_count_success(mock_db: AsyncMock) -> None:
    """Test WIP count query parsing."""
    service = MetricsService(db=mock_db)
    mock_db.execute.return_value = MockResult(scalar_rows=[7])

    count = await service.wip_count(repo_id=1)
    assert count == 7


@pytest.mark.asyncio
async def test_throughput_calculation(mock_db: AsyncMock) -> None:
    """Test weekly throughput and rolling 4-week average calculations."""
    service = MetricsService(db=mock_db)

    # 5 weeks of data (to test rolling avg of last 4 weeks)
    weekly_rows = [
        MagicMock(week="2026-W20", merged=10, opened=12),
        MagicMock(week="2026-W21", merged=12, opened=14),
        MagicMock(week="2026-W22", merged=15, opened=15),
        MagicMock(week="2026-W23", merged=14, opened=16),
        MagicMock(week="2026-W24", merged=11, opened=13),
    ]
    mock_db.execute.return_value = MockResult(rows=weekly_rows)

    res = await service.throughput(repo_id=1, weeks=12)

    assert len(res.weekly) == 5
    assert res.weekly[4].week == "2026-W24"
    assert res.weekly[4].merged == 11

    # Rolling avg should be of the last 4 weeks: (12 + 15 + 14 + 11) / 4 = 52 / 4 = 13.0
    assert res.rolling_avg == 13.0
