"""Rate limiting and circuit breaker management for voice handler."""
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
        """Make a rate-limited API request with circuit breaker pattern.

        This manager is intended for external APIs (e.g., TTS backends). Discord API calls
        should be delegated to discord.py, which handles rate limits internally. If the
        provided callable appears to be a discord.py API call, it is invoked directly
        without applying client-side rate limiting or circuit breaking.
        """
        # If this looks like a discord.py API call, bypass local limiter/CB
        if self._looks_like_discord_callable(api_call):
            return await api_call(*args, **kwargs)

        # External API: apply simple spacing + circuit breaker
        if not await self.circuit_breaker.can_make_request():
            raise CircuitBreakerOpenError("Circuit breaker is open")

        await self.rate_limiter.wait_if_needed()

        try:
            result = await api_call(*args, **kwargs)
            await self.circuit_breaker.record_success()
            return result
        except Exception:
            # Treat any failure from external API as a breaker failure
            await self.circuit_breaker.record_failure()
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

    def _looks_like_discord_callable(self, api_call: Callable[..., Any]) -> bool:
        """Best-effort check whether the callable belongs to discord.py.

        This avoids double-handling of Discord rate limits by skipping local
        rate limiting/circuit breaking for discord.py-bound methods.
        """
        try:
            mod = getattr(api_call, "__module__", "") or ""
            if mod.startswith("discord"):
                return True
            # bound methods: inspect the instance's module
            owner = getattr(api_call, "__self__", None)
            owner_mod = getattr(owner, "__module__", "") if owner is not None else ""
            return isinstance(owner, object) and owner_mod.startswith("discord")
        except Exception:
            return False

    async def can_make_request(self) -> bool:
        """Check if a request can be made through the circuit breaker."""
        return await self.circuit_breaker.can_make_request()

    def get_circuit_breaker_state(self) -> str:
        """Get the current circuit breaker state."""
        return self.circuit_breaker.state

    def reset_circuit_breaker(self) -> None:
        """Reset the circuit breaker to closed state."""
        self.circuit_breaker.reset()
