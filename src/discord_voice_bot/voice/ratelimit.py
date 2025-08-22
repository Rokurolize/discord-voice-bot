"""Rate limiting utilities for voice operations."""

import time
from typing import Any


class SimpleRateLimiter:
    """Simple rate limiter that respects Discord's global limit."""

    def __init__(self) -> None:
        self.last_request_time = 0.0

    async def wait_if_needed(self) -> None:
        """Wait to respect Discord's 50 requests per second global limit."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time

        # Discord allows 50 requests per second globally
        min_interval = 1.0 / 50.0

        if time_since_last < min_interval:
            wait_time = min_interval - time_since_last
            import asyncio

            await asyncio.sleep(wait_time)

        self.last_request_time = time.time()


class CircuitBreaker:
    """Circuit breaker pattern for API failure handling."""

    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 60.0) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = 0.0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    async def can_make_request(self) -> bool:
        """Check if a request can be made."""
        current_time = time.time()

        if self.state == "CLOSED":
            return True
        elif self.state == "OPEN":
            if current_time - self.last_failure_time >= self.recovery_timeout:
                self.state = "HALF_OPEN"
                from loguru import logger

                logger.info("Circuit breaker transitioning to HALF_OPEN state")
                return True
            return False
        else:  # HALF_OPEN
            return True

    async def record_success(self) -> None:
        """Record a successful request."""
        if self.state == "HALF_OPEN":
            self.state = "CLOSED"
            self.failure_count = 0
            from loguru import logger

            logger.info("Circuit breaker transitioning to CLOSED state")

    async def record_failure(self) -> None:
        """Record a failed request."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            from loguru import logger

            logger.error(f"Circuit breaker transitioning to OPEN state after {self.failure_count} failures")

    def get_state(self) -> dict[str, Any]:
        """Get current circuit breaker state."""
        return {"state": self.state, "failure_count": self.failure_count, "last_failure_time": self.last_failure_time}
