"""Permission and access control management for Discord Voice TTS Bot."""

from typing import Any, TypeVar

import discord
from loguru import logger

# Type variable for blockable items
T = TypeVar("T")


class BlockManager[T]:
    """Generic manager for blocked items."""

    def __init__(self, item_type: str) -> None:
        """Initialize block manager.

        Args:
            item_type: Type name for logging (e.g., 'word', 'user', 'channel')

        """
        super().__init__()
        self._blocked_items: set[T] = set()
        self._item_type = item_type

    def _modify_blocked_item(self, item: T, action: str, operation: Any) -> None:
        """Modify blocked item with logging."""
        operation(item)
        logger.info(f"{action} blocked {self._item_type}: {item}")

    def add(self, item: T) -> None:
        """Add an item to the blocked list."""

        def add_item(i: T) -> None:
            self._blocked_items.add(i)

        self._modify_blocked_item(item, "Added", add_item)

    def remove(self, item: T) -> None:
        """Remove an item from the blocked list."""

        def remove_item(i: T) -> None:
            self._blocked_items.discard(i)

        self._modify_blocked_item(item, "Removed", remove_item)

    def contains(self, item: T) -> bool:
        """Check if item is blocked.

        Args:
            item: Item to check

        Returns:
            True if blocked, False otherwise

        """
        return item in self._blocked_items

    def clear(self) -> None:
        """Clear all blocked items."""
        self._blocked_items.clear()
        logger.info(f"Cleared all blocked {self._item_type}s")

    def get_all(self) -> set[T]:
        """Get all blocked items.

        Returns:
            Set of blocked items

        """
        return self._blocked_items.copy()

    def count(self) -> int:
        """Get count of blocked items.

        Returns:
            Number of blocked items

        """
        return len(self._blocked_items)


class PermissionManager:
    """Manages permissions and access control for TTS functionality."""

    def __init__(self) -> None:
        """Initialize permission manager."""
        super().__init__()
        # Content filters using generic block managers
        self._word_manager = BlockManager[str]("word")
        self._user_manager = BlockManager[int]("user")
        self._channel_manager = BlockManager[int]("channel")
        self._allowed_domains: set[str] = set()

        logger.info("Permission manager initialized")

    async def check_user_permission(self, message: discord.Message) -> tuple[bool, str]:
        """Check if user has permission to send TTS messages.

        Args:
            message: Discord message

        Returns:
            Tuple of (has_permission, reason)

        """
        # Check blocked users
        if self._user_manager.contains(message.author.id):
            return False, "User is blocked from TTS"

        # Check blocked channels
        if self._channel_manager.contains(message.channel.id):
            return False, "Channel is blocked from TTS"

        # Additional permission checks can be added here
        # e.g., role-based permissions, server-specific rules

        return True, ""

    async def check_rate_limit(self, message: discord.Message) -> tuple[bool, str]:
        """Check if user is within rate limits.

        Args:
            message: Discord message

        Returns:
            Tuple of (within_limits, reason)

        """
        # This would integrate with a rate limiter
        # For now, we'll assume it's handled elsewhere
        # but this provides the interface for future implementation

        # Placeholder for rate limiting logic
        # if self.rate_limiter.is_rate_limited(message.author.id):
        #     return False, "Rate limit exceeded"

        return True, ""

    def check_content_safety(self, message: discord.Message) -> tuple[bool, str]:
        """Check message content for safety and appropriateness.

        Args:
            message: Discord message

        Returns:
            Tuple of (is_safe, reason)

        """
        content_lower = message.content.lower()

        # Check for blocked words
        for word in self._word_manager.get_all():
            if word.lower() in content_lower:
                return False, f"Blocked word detected: {word}"

        return True, ""

    def _modify_blocked_item_by_manager(self, manager_name: str, item: str | int, action: str) -> None:
        """Modify blocked item using manager with logging."""
        manager = getattr(self, f"_{manager_name}_manager")
        if action == "add":
            if manager_name == "word":
                manager.add(str(item).lower())
            else:
                manager.add(item)
        else:  # remove
            if manager_name == "word":
                manager.remove(str(item).lower())
            else:
                manager.remove(item)

    # Configuration methods
    def add_blocked_word(self, word: str) -> None:
        """Add a word to the blocked list."""
        self._modify_blocked_item_by_manager("word", word, "add")

    def remove_blocked_word(self, word: str) -> None:
        """Remove a word from the blocked list."""
        self._modify_blocked_item_by_manager("word", word, "remove")

    def add_blocked_user(self, user_id: int) -> None:
        """Add a user to the blocked list."""
        self._modify_blocked_item_by_manager("user", user_id, "add")

    def remove_blocked_user(self, user_id: int) -> None:
        """Remove a user from the blocked list."""
        self._modify_blocked_item_by_manager("user", user_id, "remove")

    def add_blocked_channel(self, channel_id: int) -> None:
        """Add a channel to the blocked list."""
        self._modify_blocked_item_by_manager("channel", channel_id, "add")

    def remove_blocked_channel(self, channel_id: int) -> None:
        """Remove a channel from the blocked list."""
        self._modify_blocked_item_by_manager("channel", channel_id, "remove")

    def get_statistics(self) -> dict[str, int]:
        """Get permission statistics.

        Returns:
            Dictionary with permission statistics

        """
        return {
            "blocked_words": self._word_manager.count(),
            "blocked_users": self._user_manager.count(),
            "blocked_channels": self._channel_manager.count(),
            "allowed_domains": len(self._allowed_domains),
        }

    def reset_filters(self) -> None:
        """Reset all filters to default state."""
        self._word_manager.clear()
        self._user_manager.clear()
        self._channel_manager.clear()
        self._allowed_domains.clear()
        logger.info("Reset all permission filters")

    # Test access methods
    def get_blocked_words(self) -> set[str]:
        """Get blocked words for testing.

        Returns:
            Set of blocked words

        """
        return self._word_manager.get_all()

    def get_blocked_users(self) -> set[int]:
        """Get blocked users for testing.

        Returns:
            Set of blocked user IDs

        """
        return self._user_manager.get_all()

    def get_blocked_channels(self) -> set[int]:
        """Get blocked channels for testing.

        Returns:
            Set of blocked channel IDs

        """
        return self._channel_manager.get_all()

    def get_allowed_domains(self) -> set[str]:
        """Get allowed domains for testing.

        Returns:
            Set of allowed domains

        """
        return self._allowed_domains.copy()
