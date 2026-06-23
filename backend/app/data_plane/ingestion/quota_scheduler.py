"""Quota-aware scheduler for pacing GitHub API requests based on rate limit remaining and reset window."""

import asyncio
import logging
import time

logger = logging.getLogger(__name__)


class QuotaAwareScheduler:
    """Schedules and paces GitHub API requests dynamically based on remaining quota.

    Instead of simple reactive backoff, this scheduler is proactive:
    - It calculates the allowed rate: usable_quota / time_until_reset.
    - It paces consecutive requests using sleeps to stay within the allowed rate.
    - It halts operations and blocks until reset if quota falls below a safety buffer.
    - It respects secondary rate limits via Retry-After values.
    """

    def __init__(self, limit_buffer: int = 100, max_rate: float = 10.0) -> None:
        """Initialize the scheduler.

        Args:
            limit_buffer: Safety margin of requests to keep unused (default 100).
            max_rate: Maximum requests per second to allow (default 10.0).
        """
        self.limit_buffer = limit_buffer
        self.max_rate = max_rate
        self.last_request_time = 0.0
        self.lock = asyncio.Lock()

    async def schedule_request(self, remaining: int, reset_at: float) -> None:
        """Gate request execution to align with remaining quota.

        Args:
            remaining: Number of requests remaining in current rate limit window.
            reset_at: Epoch timestamp (seconds) when rate limit resets.
        """
        async with self.lock:
            now = time.time()

            # First request or uninitialized state -> execute immediately
            if reset_at <= 0.0:
                self.last_request_time = now
                return

            time_to_reset = reset_at - now

            # If quota is exhausted or below safety buffer, block until reset
            if remaining <= self.limit_buffer:
                if time_to_reset > 0:
                    wait_time = time_to_reset + 2.0  # Add 2s buffer for clock drift
                    logger.warning(
                        "Rate limit quota exhausted (remaining: %d, buffer: %d). "
                        "Blocking for %.1f seconds until reset at %s.",
                        remaining,
                        self.limit_buffer,
                        wait_time,
                        time.ctime(reset_at),
                    )
                    await asyncio.sleep(wait_time)
                self.last_request_time = time.time()
                return

            # Dynamic pacing calculation:
            # Distribute remaining usable requests evenly across the remaining window time.
            if time_to_reset > 0:
                usable_quota = remaining - self.limit_buffer
                allowed_rate = usable_quota / time_to_reset  # requests / second

                # Cap to prevent burst loads
                allowed_rate = min(allowed_rate, self.max_rate)

                if allowed_rate > 0:
                    min_interval = 1.0 / allowed_rate
                    elapsed = now - self.last_request_time
                    if elapsed < min_interval:
                        delay = min_interval - elapsed
                        logger.debug(
                            "Quota Scheduler: Pacing request. Sleeping for %.3f seconds (allowed rate: %.2f req/s).",
                            delay,
                            allowed_rate,
                        )
                        await asyncio.sleep(delay)

            self.last_request_time = time.time()
