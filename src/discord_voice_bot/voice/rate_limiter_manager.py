"""Rate limiting and circuit breaker management for voice handler."""

import asyncio
from collections.abc import Callable
from typing import Any

import discord

from .ratelimit import CircuitBreaker, SimpleRateLimiter


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open and requests cannot be made."""


class RateLimiterManager:
    """Manages rate limiting and circuit breaker functionality."""

    def __init__(self) -> None:
        """Initialize rate limiter manager."""
        super().__init__()
        self.rate_limiter = SimpleRateLimiter()
        self.circuit_breaker = CircuitBreaker()

    async def make_rate_limited_request(self, api_call: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Make a rate-limited API request with circuit breaker pattern."""
        # Check circuit breaker state first
        if not await self.circuit_breaker.can_make_request():
            raise CircuitBreakerOpenError("Circuit breaker is open")

        await self.rate_limiter.wait_if_needed()

        try:
            result = await api_call(*args, **kwargs)
            # Record success in circuit breaker
            await self.circuit_breaker.record_success()
            return result
        except discord.HTTPException as e:
            # Record failure in circuit breaker for non-rate-limit errors
            if e.status != 429:
                await self.circuit_breaker.record_failure()

            if e.status == 429:  # Rate limited by Discord
                retry_after = self._extract_retry_after(e)
                await asyncio.sleep(float(retry_after))
                # Retry once after rate limit
                return await api_call(*args, **kwargs)
            else:
                raise

    def _extract_retry_after(self, exception: discord.HTTPException) -> str:
        """Extract retry-after value from HTTP exception."""
        if hasattr(exception, "response") and exception.response:
            try:
                headers = getattr(exception.response, "headers", {})
                if hasattr(headers, "get"):
                    return headers.get("Retry-After", "1")
            except (AttributeError, TypeError):
                pass
        return "1"

    async def can_make_request(self) -> bool:
        """Check if a request can be made through the circuit breaker."""
        return await self.circuit_breaker.can_make_request()

    def get_circuit_breaker_state(self) -> str:
        """Get the current circuit breaker state."""
        return self.circuit_breaker.state

    def reset_circuit_breaker(self) -> None:
        """Reset the circuit breaker to closed state."""
        self.circuit_breaker.reset()
