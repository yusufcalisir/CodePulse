"""Unit tests for the QuotaAwareScheduler pacing and throttling logic."""

import time
from unittest.mock import AsyncMock, patch
import pytest

from app.data_plane.ingestion.quota_scheduler import QuotaAwareScheduler


@pytest.mark.asyncio
async def test_scheduler_initial_request() -> None:
    """The first request (no rate limit context yet) should execute immediately."""
    scheduler = QuotaAwareScheduler()
    
    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        await scheduler.schedule_request(remaining=5000, reset_at=0.0)
        mock_sleep.assert_not_called()


@pytest.mark.asyncio
async def test_scheduler_quota_exhausted() -> None:
    """When the remaining quota drops below the safety buffer, the scheduler should block until reset_at."""
    scheduler = QuotaAwareScheduler(limit_buffer=100)
    now = time.time()
    reset_at = now + 10.0  # Reset in 10 seconds
    
    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        await scheduler.schedule_request(remaining=99, reset_at=reset_at)
        
        # Should sleep for time_to_reset + 2s buffer
        mock_sleep.assert_called_once()
        args, _ = mock_sleep.call_args
        assert args[0] >= 11.9
        assert args[0] <= 12.1


@pytest.mark.asyncio
async def test_scheduler_dynamic_pacing() -> None:
    """When there is usable quota, the scheduler should pace requests based on calculated requests per second."""
    scheduler = QuotaAwareScheduler(limit_buffer=100, max_rate=5.0)
    now = time.time()
    
    # 500 remaining requests, 100 buffer = 400 usable requests
    # 80 seconds until reset
    # allowed_rate = 400 / 80 = 5.0 requests/second -> min interval = 0.2 seconds
    reset_at = now + 80.0
    
    # Set last request to exactly now to simulate a back-to-back call
    scheduler.last_request_time = now
    
    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        await scheduler.schedule_request(remaining=500, reset_at=reset_at)
        
        mock_sleep.assert_called_once()
        args, _ = mock_sleep.call_args
        # Pacing delay should be close to 0.2 seconds
        assert args[0] > 0.15
        assert args[0] <= 0.20
