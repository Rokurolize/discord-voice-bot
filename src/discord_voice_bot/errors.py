"""Custom exception types for discord_voice_bot.

Focused, typed errors that carry structured context for top-level handling.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import override


@dataclass(slots=True)
class HealthCheckError(Exception):
    """Raised when startup health checks encounter an unexpected contract violation.

    Attributes capture structured context for actionable logging at the top level.
    """

    message: str
    result_type: str
    result_repr: str
    engine_name: str
    api_url: str

    @override
    def __str__(self) -> str:  # pragma: no cover - formatting convenience
        return (
            f"{self.message} | result_type={self.result_type} "
            f"result_repr={self.result_repr} engine={self.engine_name} url={self.api_url}"
        )
