"""Unit tests for the storage manager / synchronization service (storage_manager.py)."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.data_plane.storage.models.repository import Repository
from app.data_plane.storage.models.sync_log import SyncLog
from app.data_plane.storage.storage_manager import StorageManager
from tests.conftest import MockResult


@pytest.mark.asyncio
async def test_initial_sync_success(mock_db: AsyncMock) -> None:
    """Test a successful full initial sync of a repository."""
    # Instantiation of service with mock DB session
    service = StorageManager(db=mock_db, github_token="test_token")

    # Mock the github client calls
    service.collector.get_repo_info = AsyncMock(
        return_value={
            "databaseId": 12345,
            "name": "codepulse",
            "nameWithOwner": "org/codepulse",
            "owner": {"login": "org"},
            "defaultBranchRef": {"name": "main"},
        }
    )

    raw_prs = [
        {
            "databaseId": 9991,
            "number": 1,
            "title": "Initial commit PR",
            "state": "MERGED",
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "mergedAt": datetime.now(timezone.utc).isoformat(),
            "closedAt": None,
            "additions": 100,
            "deletions": 5,
            "author": {"login": "coder-alice"},
            "reviews": {
                "nodes": [
                    {
                        "databaseId": 771,
                        "state": "APPROVED",
                        "createdAt": datetime.now(timezone.utc).isoformat(),
                        "author": {"login": "reviewer-bob"},
                    }
                ]
            },
        }
    ]
    service.collector.fetch_pull_requests = AsyncMock(return_value=raw_prs)

    raw_commits = [
        {
            "oid": "abcdef1234567890abcdef1234567890abcdef12",
            "message": "Add gitignore",
            "authoredDate": datetime.now(timezone.utc).isoformat(),
            "author": {
                "user": {"login": "coder-alice"},
                "name": "Alice"
            }
        }
    ]
    service.collector.fetch_commits = AsyncMock(return_value=raw_commits)

    # Setup side-effects for DB execute calls
    def mock_execute(stmt, *args, **kwargs):
        stmt_str = str(stmt)
        if "FROM repositories" in stmt_str:
            # First lookup returns None (repo not exists yet), we will then create it
            return MockResult(rows=[])
        elif "pull_requests.id" in stmt_str:
            # Return mocked PR ID for review associations
            return MockResult(scalar_rows=[88])
        # Return empty results for insert/update executions
        return MockResult(rows=[])

    mock_db.execute.side_effect = mock_execute

    sync_log = await service.initial_sync("org/codepulse", "test_org")

    # Assertions
    assert isinstance(sync_log, SyncLog)
    assert sync_log.status == "completed"
    assert sync_log.pr_count == 1
    assert sync_log.finished_at is not None
    assert sync_log.error is None

    # Check database flush / add was called
    assert mock_db.flush.call_count >= 1
    assert mock_db.add.call_count >= 1

    # Verify that events were logged
    from app.data_plane.storage.models.event import Event
    added_objs = [call[0][0] for call in mock_db.add.call_args_list if call[0]]
    events = [obj for obj in added_objs if isinstance(obj, Event)]
    assert len(events) == 4
    event_types = [e.type for e in events]
    assert "PR_CREATED" in event_types
    assert "PR_MERGED" in event_types
    assert "REVIEW_SUBMITTED" in event_types
    assert "COMMIT_PUSHED" in event_types

    service.collector.fetch_pull_requests.assert_called_once_with(
        "org", "codepulse", max_prs=1000
    )
    service.collector.fetch_commits.assert_called_once_with(
        "org", "codepulse", "main"
    )


@pytest.mark.asyncio
async def test_initial_sync_failure_rollbacks(mock_db: AsyncMock) -> None:
    """Test database rollback and failure logging on exception."""
    service = StorageManager(db=mock_db, github_token="test_token")

    # Mock DB lookup to return existing repo
    existing_repo = Repository(id=1, github_id=123, name="codepulse", full_name="org/codepulse")
    
    def mock_execute(stmt, *args, **kwargs):
        stmt_str = str(stmt)
        if "FROM repositories" in stmt_str:
            return MockResult(rows=[existing_repo], scalar_rows=[existing_repo])
        return MockResult()

    mock_db.execute.side_effect = mock_execute

    # Make github fetch throw an API exception
    service.collector.fetch_pull_requests = AsyncMock(
        side_effect=Exception("GitHub API Connection timeout")
    )

    with pytest.raises(Exception, match="GitHub API Connection timeout"):
        await service.initial_sync("org/codepulse", "test_org")

    # The exception should be bubbled up, but sync status should be failed
    # Verify that mock_db logged the error (sync_log is updated inside initial_sync)
    # The last flush should set the status of sync_log to failed
    # Find sync_log add
    sync_logs = [
        call[0][0]
        for call in mock_db.add.call_args_list
        if call[0] and isinstance(call[0][0], SyncLog)
    ]
    assert len(sync_logs) == 1
    assert sync_logs[0].status == "failed"
    assert "GitHub API Connection" in sync_logs[0].error


@pytest.mark.asyncio
async def test_incremental_sync_success(mock_db: AsyncMock) -> None:
    """Test a successful incremental sync of a repository."""
    service = StorageManager(db=mock_db, github_token="test_token")

    repo = Repository(id=42, github_id=123, name="codepulse", full_name="org/codepulse")
    
    # Mock database repository retrieval
    def mock_execute(stmt, *args, **kwargs):
        stmt_str = str(stmt)
        if "FROM repositories" in stmt_str:
            return MockResult(rows=[repo], scalar_rows=[repo])
        elif "pull_requests.id" in stmt_str:
            return MockResult(scalar_rows=[100])
        return MockResult()

    mock_db.execute.side_effect = mock_execute

    # Mock github client recent PR retrieval
    raw_prs = [
        {
            "databaseId": 9992,
            "number": 2,
            "title": "Feature branch PR",
            "state": "OPEN",
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "mergedAt": None,
            "closedAt": None,
            "additions": 50,
            "deletions": 10,
            "author": {"login": "coder-bob"},
            "reviews": {"nodes": []},
        }
    ]
    service.collector.fetch_pull_requests = AsyncMock(return_value=raw_prs)
    service.collector.fetch_commits = AsyncMock(return_value=[])

    sync_log = await service.incremental_sync(42)

    assert sync_log.status == "completed"
    assert sync_log.pr_count == 1
    assert repo.synced_at is not None
    service.collector.fetch_pull_requests.assert_called_once_with(
        "org", "codepulse", max_prs=200
    )
    service.collector.fetch_commits.assert_called_once_with(
        "org", "codepulse", "main"
    )


@pytest.mark.asyncio
async def test_log_event_idempotency_key(mock_db: AsyncMock) -> None:
    """Test _log_event checks for existing events and calls db.add with correct idempotency key."""
    service = StorageManager(db=mock_db, github_token="test_token")
    mock_db.execute.return_value = MockResult(scalar_rows=[None])
    
    payload = {"source_github_id": 12345, "number": 1, "title": "Test PR"}
    await service._log_event(
        repo_id=1,
        event_type="PR_CREATED",
        actor="alice",
        payload=payload,
        idempotency_key="PR_CREATED:1:12345"
    )
    
    assert mock_db.execute.call_count == 1
    stmt = mock_db.execute.call_args[0][0]
    assert "FROM events" in str(stmt)
    
    mock_db.add.assert_called_once()
    event = mock_db.add.call_args[0][0]
    assert event.idempotency_key == "PR_CREATED:1:12345"
    assert event.type == "PR_CREATED"



