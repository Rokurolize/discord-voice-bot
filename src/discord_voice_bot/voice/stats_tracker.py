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

    def get(self, key: str, default: Any = None) -> Any:
        """Get a stat value by key, maintaining dict-like access for backward compatibility."""
        return self.stats.get(key, default)

    def current_count(self) -> int:
        """Get total count of processed messages for backward compatibility."""
        return self.stats["messages_played"] + self.stats["messages_skipped"]

    def __getitem__(self, key: str) -> Any:
        """Dict-like access for backward compatibility."""
        return self.stats[key]

    def __setitem__(self, key: str, value: Any) -> None:
        """Dict-like assignment for backward compatibility."""
        self.stats[key] = value
