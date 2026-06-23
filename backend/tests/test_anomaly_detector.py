"""Unit tests for the anomaly detection service (anomaly_detector.py)."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.data_plane.storage.models.pull_request import PullRequest
from app.intelligence_plane.anomalies.anomaly_detector import AnomalyDetector
from tests.conftest import MockResult


@pytest.mark.asyncio
async def test_detect_size_anomalies(mock_db: AsyncMock) -> None:
    """Test that PRs with additions + deletions > 500 trigger a size anomaly."""
    detector = AnomalyDetector(db=mock_db)

    # 1. Mock PRs returned from db
    pr_normal = PullRequest(
        id=1, repo_id=1, github_id=101, number=1, title="Small PR",
        state="open", author="alice", additions=10, deletions=5,
        created_at=datetime.now(timezone.utc)
    )
    pr_large = PullRequest(
        id=2, repo_id=1, github_id=102, number=2, title="Huge PR",
        state="open", author="bob", additions=400, deletions=200,  # 600 total lines
        created_at=datetime.now(timezone.utc)
    )

    def mock_execute(stmt, *args, **kwargs):
        stmt_str = str(stmt).lower()
        if "count" in stmt_str:
            return MockResult(scalar_rows=[0])
        elif "pull_requests" in stmt_str:
            return MockResult(scalar_rows=[pr_normal, pr_large])
        return MockResult()

    mock_db.execute.side_effect = mock_execute

    # Execute and check
    anomalies = await detector.detect_anomalies(repo_id=1, days=30)
    
    size_anoms = [a for a in anomalies if a.type == "pr_size_anomaly"]
    assert len(size_anoms) == 1
    assert size_anoms[0].pr_number == 2
    assert size_anoms[0].author == "bob"
    assert size_anoms[0].value == 600.0


@pytest.mark.asyncio
async def test_detect_cycle_time_spikes(mock_db: AsyncMock) -> None:
    """Test that PRs with cycle times exceeding 2 standard deviations trigger a cycle time spike anomaly."""
    detector = AnomalyDetector(db=mock_db)

    # We need 3+ merged PRs, with more normal points to lower standard deviation
    now = datetime.now(timezone.utc)
    normal_prs = [
        PullRequest(
            id=i, repo_id=1, github_id=100 + i, number=i, title=f"PR {i}",
            state="merged", author="alice", additions=10, deletions=5,
            created_at=now - timedelta(hours=5), merged_at=now
        )
        for i in range(1, 9)
    ]
    pr_spike = PullRequest(
        id=9, repo_id=1, github_id=109, number=9, title="PR 9 Spike",
        state="merged", author="charlie", additions=10, deletions=5,
        created_at=now - timedelta(hours=100), merged_at=now
    )

    def mock_execute(stmt, *args, **kwargs):
        stmt_str = str(stmt).lower()
        if "count" in stmt_str:
            return MockResult(scalar_rows=[0])
        elif "pull_requests" in stmt_str:
            return MockResult(scalar_rows=normal_prs + [pr_spike])
        return MockResult()

    mock_db.execute.side_effect = mock_execute

    anomalies = await detector.detect_anomalies(repo_id=1, days=30)
    
    ct_spikes = [a for a in anomalies if a.type == "cycle_time_spike"]
    assert len(ct_spikes) == 1
    assert ct_spikes[0].pr_number == 9
    assert ct_spikes[0].value == 100.0


@pytest.mark.asyncio
async def test_detect_reviewer_bottlenecks(mock_db: AsyncMock) -> None:
    """Test that a bottleneck alert is raised when one reviewer handles >50% of the reviews."""
    detector = AnomalyDetector(db=mock_db)

    # Mock PRs lookup (need at least one PR to proceed)
    pr = PullRequest(
        id=1, repo_id=1, github_id=101, number=1, state="open",
        created_at=datetime.now(timezone.utc), additions=0, deletions=0
    )
    
    # Reviewer queries return counts
    # Total reviews = 10. bob has 8 reviews (80%)
    reviewer_row_1 = MagicMock(author="bob", cnt=8)
    reviewer_row_2 = MagicMock(author="charlie", cnt=2)

    # We mock execute call side effect
    def mock_execute(stmt, *args, **kwargs):
        stmt_str = str(stmt).lower()
        if "from pull_requests" in stmt_str:
            # First query to fetch PRs
            return MockResult(scalar_rows=[pr])
        elif "from reviews" in stmt_str:
            # Bottleneck query
            return MockResult(rows=[reviewer_row_1, reviewer_row_2])
        # Return default 0 count for throughput queries
        return MockResult(scalar_rows=[0])

    mock_db.execute.side_effect = mock_execute

    anomalies = await detector.detect_anomalies(repo_id=1, days=30)

    bottlenecks = [a for a in anomalies if a.type == "reviewer_bottleneck"]
    assert len(bottlenecks) == 1
    assert bottlenecks[0].author == "bob"
    assert bottlenecks[0].value == 80.0
