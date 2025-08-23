"""Statistics tracking for voice handler."""

from typing import Any


class StatsTracker:
    """Manages voice handler statistics."""

    def __init__(self) -> None:
        """Initialize stats tracker."""
        super().__init__()
        self.stats = {"messages_played": 0, "messages_skipped": 0, "errors": 0}

    def increment_messages_played(self) -> None:
        """Increment messages played counter."""
        self.stats["messages_played"] += 1

    def increment_messages_skipped(self) -> None:
        """Increment messages skipped counter."""
        self.stats["messages_skipped"] += 1

    def increment_errors(self) -> None:
        """Increment errors counter."""
        self.stats["errors"] += 1

    def get_stats(self) -> dict[str, Any]:
        """Get current statistics."""
        return self.stats.copy()

    def reset_stats(self) -> None:
        """Reset all statistics to zero."""
        self.stats = {"messages_played": 0, "messages_skipped": 0, "errors": 0}
