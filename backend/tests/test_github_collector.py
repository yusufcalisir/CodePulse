"""Unit tests for the GitHub GraphQL client (github_collector.py)."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.data_plane.ingestion.github_collector import GitHubAPIError, GitHubCollector


@pytest.mark.asyncio
async def test_get_repo_info_success() -> None:
    """Test successful fetching of repository details."""
    client = GitHubCollector(token="test_token")

    # Mock response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "data": {
            "repository": {
                "databaseId": 12345,
                "name": "codepulse",
                "nameWithOwner": "org/codepulse",
                "owner": {"login": "org"},
                "defaultBranchRef": {"name": "main"},
            }
        }
    }
    mock_response.headers = httpx.Headers(
        {
            "x-ratelimit-remaining": "4999",
            "x-ratelimit-reset": "1782236000",
        }
    )

    mock_http_client = AsyncMock()
    mock_http_client.is_closed = False
    mock_http_client.post.return_value = mock_response
    client._client = mock_http_client

    repo_info = await client.get_repo_info("org", "codepulse")

    assert repo_info["databaseId"] == 12345
    assert repo_info["name"] == "codepulse"
    assert client._rate_limit.remaining == 4999
    assert client._rate_limit.reset_at == 1782236000.0


@pytest.mark.asyncio
async def test_execute_query_graphql_error() -> None:
    """Test GraphQL error response raises GitHubAPIError."""
    client = GitHubCollector(token="test_token")

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "errors": [{"message": "Could not resolve owner or repository name"}]
    }
    mock_response.headers = httpx.Headers()

    mock_http_client = AsyncMock()
    mock_http_client.is_closed = False
    mock_http_client.post.return_value = mock_response
    client._client = mock_http_client

    with pytest.raises(
        GitHubAPIError, match="Could not resolve owner or repository name"
    ):
        await client.get_repo_info("org", "nonexistent")


@pytest.mark.asyncio
async def test_execute_query_server_error_retry() -> None:
    """Test automatic retries on server errors (status code >= 500)."""
    client = GitHubCollector(token="test_token")

    mock_response_500 = MagicMock()
    mock_response_500.status_code = 502
    mock_response_500.headers = httpx.Headers()

    mock_response_200 = MagicMock()
    mock_response_200.status_code = 200
    mock_response_200.json.return_value = {
        "data": {"repository": {"databaseId": 123}}
    }
    mock_response_200.headers = httpx.Headers()

    mock_http_client = AsyncMock()
    mock_http_client.is_closed = False
    # First call returns 502, second call returns 200
    mock_http_client.post.side_effect = [mock_response_500, mock_response_200]
    client._client = mock_http_client

    with patch("asyncio.sleep", AsyncMock()) as mock_sleep:
        repo_info = await client.get_repo_info("org", "codepulse")
        assert repo_info["databaseId"] == 123
        assert mock_http_client.post.call_count == 2
        mock_sleep.assert_called_once()


@pytest.mark.asyncio
async def test_execute_query_secondary_rate_limit() -> None:
    """Test secondary rate limit handling (403 with retry-after header)."""
    client = GitHubCollector(token="test_token")

    mock_response_403 = MagicMock()
    mock_response_403.status_code = 403
    mock_response_403.headers = httpx.Headers({"retry-after": "5"})

    mock_response_200 = MagicMock()
    mock_response_200.status_code = 200
    mock_response_200.json.return_value = {
        "data": {"repository": {"databaseId": 999}}
    }
    mock_response_200.headers = httpx.Headers()

    mock_http_client = AsyncMock()
    mock_http_client.is_closed = False
    mock_http_client.post.side_effect = [mock_response_403, mock_response_200]
    client._client = mock_http_client

    with patch("asyncio.sleep", AsyncMock()) as mock_sleep:
        repo_info = await client.get_repo_info("org", "codepulse")
        assert repo_info["databaseId"] == 999
        mock_sleep.assert_any_call(5)


@pytest.mark.asyncio
async def test_fetch_pull_requests_pagination() -> None:
    """Test cursor-based pagination handles multiple pages of PRs."""
    client = GitHubCollector(token="test_token")

    # First page
    mock_response_1 = MagicMock()
    mock_response_1.status_code = 200
    mock_response_1.json.return_value = {
        "data": {
            "repository": {
                "pullRequests": {
                    "pageInfo": {"hasNextPage": True, "endCursor": "cursor_1"},
                    "nodes": [{"databaseId": 1, "number": 101}],
                }
            }
        }
    }
    mock_response_1.headers = httpx.Headers()

    # Second page
    mock_response_2 = MagicMock()
    mock_response_2.status_code = 200
    mock_response_2.json.return_value = {
        "data": {
            "repository": {
                "pullRequests": {
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                    "nodes": [{"databaseId": 2, "number": 102}],
                }
            }
        }
    }
    mock_response_2.headers = httpx.Headers()

    mock_http_client = AsyncMock()
    mock_http_client.is_closed = False
    mock_http_client.post.side_effect = [mock_response_1, mock_response_2]
    client._client = mock_http_client

    prs = await client.fetch_pull_requests("org", "codepulse", max_prs=10)

    assert len(prs) == 2
    assert prs[0]["databaseId"] == 1
    assert prs[1]["databaseId"] == 2
    assert mock_http_client.post.call_count == 2
