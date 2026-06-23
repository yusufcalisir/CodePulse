"""Unit tests for the ReplayService database reconstruction logic."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.data_plane.storage.models.repository import Repository
from app.data_plane.storage.models.event import Event
from app.data_plane.storage.replay_service import ReplayService
from tests.conftest import MockResult


@pytest.mark.asyncio
async def test_replay_repository_events_success(mock_db: AsyncMock) -> None:
    """Test replaying repository events sequentially to reconstruct database state tables."""
    repo_id = 42
    repo = Repository(id=repo_id, full_name="org/test-repo", name="test-repo")
    
    # 1. Mock repository check
    mock_db.execute.side_effect = [
        # First query: Repository exists check
        MockResult(scalar_rows=[repo]),
        # Second execute: truncate deletes (reviews, pull_requests, commits)
        MagicMock(),
        MagicMock(),
        MagicMock(),
        # Third query: select Events
        MockResult(
            scalar_rows=[
                Event(
                    id=1,
                    type="PR_CREATED",
                    repo_id=repo_id,
                    actor="alice",
                    payload={
                        "source_github_id": 901,
                        "number": 1,
                        "title": "Fix bug",
                        "state": "open",
                        "author": "alice",
                        "created_at": "2026-06-23T12:00:00+00:00",
                        "additions": 10,
                        "deletions": 2,
                    }
                ),
                Event(
                    id=2,
                    type="REVIEW_SUBMITTED",
                    repo_id=repo_id,
                    actor="bob",
                    payload={
                        "source_github_id": 801,
                        "pr_github_id": 901,
                        "author": "bob",
                        "state": "APPROVED",
                        "submitted_at": "2026-06-23T12:30:00+00:00",
                    }
                ),
                Event(
                    id=3,
                    type="PR_MERGED",
                    repo_id=repo_id,
                    actor="alice",
                    payload={
                        "source_github_id": 901,
                        "number": 1,
                        "merged_at": "2026-06-23T13:00:00+00:00",
                        "closed_at": "2026-06-23T13:00:00+00:00",
                    }
                ),
                Event(
                    id=4,
                    type="COMMIT_PUSHED",
                    repo_id=repo_id,
                    actor="alice",
                    payload={
                        "sha": "abc123sha",
                        "message": "Add test",
                        "author": "alice",
                        "authored_at": "2026-06-23T11:00:00+00:00",
                    }
                ),
            ]
        ),
        # Subsequent queries inside loop:
        # PR created execute
        MagicMock(),
        # REVIEW_SUBMITTED parent PR check
        MockResult(scalar_rows=[1]),
        # review execute
        MagicMock(),
        # PR merged search check
        MockResult(scalar_rows=[MagicMock()]),
        # commit execute
        MagicMock(),
    ]

    with patch("app.data_plane.storage.replay_service.MetricsPrecomputer") as mock_precomputer_cls:
        mock_precomputer = AsyncMock()
        mock_precomputer_cls.return_value = mock_precomputer

        count = await ReplayService.replay_repository_events(mock_db, repo_id)
        
        assert count == 4
        # Verify precomputer was run for the repository
        mock_precomputer.precompute_repository_metrics.assert_called_once_with(repo_id)
        # Verify database deletes and inserts were executed
        assert mock_db.execute.call_count >= 5
