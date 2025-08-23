"""Permission and access control management for Discord Voice TTS Bot."""

import discord
from loguru import logger


class PermissionManager:
    """Manages permissions and access control for TTS functionality."""

    def __init__(self) -> None:
        """Initialize permission manager."""
        super().__init__()
        # Content filters
        self._blocked_words: set[str] = set()
        self._allowed_domains: set[str] = set()
        self._blocked_users: set[int] = set()
        self._blocked_channels: set[int] = set()

        logger.info("Permission manager initialized")

    async def check_user_permission(self, message: discord.Message) -> tuple[bool, str]:
        """Check if user has permission to send TTS messages.

        Args:
            message: Discord message

        Returns:
            Tuple of (has_permission, reason)

        """
        # Check blocked users
        if message.author.id in self._blocked_users:
            return False, "User is blocked from TTS"

        # Check blocked channels
        if message.channel.id in self._blocked_channels:
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
        for word in self._blocked_words:
            if word.lower() in content_lower:
                return False, f"Blocked word detected: {word}"

        return True, ""

    # Configuration methods
    def add_blocked_word(self, word: str) -> None:
        """Add a word to the blocked list.

        Args:
            word: Word to block

        """
        self._blocked_words.add(word.lower())
        logger.info(f"Added blocked word: {word}")

    def remove_blocked_word(self, word: str) -> None:
        """Remove a word from the blocked list.

        Args:
            word: Word to unblock

        """
        self._blocked_words.discard(word.lower())
        logger.info(f"Removed blocked word: {word}")

    def add_blocked_user(self, user_id: int) -> None:
        """Add a user to the blocked list.

        Args:
            user_id: Discord user ID to block

        """
        self._blocked_users.add(user_id)
        logger.info(f"Added blocked user: {user_id}")

    def remove_blocked_user(self, user_id: int) -> None:
        """Remove a user from the blocked list.

        Args:
            user_id: Discord user ID to unblock

        """
        self._blocked_users.discard(user_id)
        logger.info(f"Removed blocked user: {user_id}")

    def add_blocked_channel(self, channel_id: int) -> None:
        """Add a channel to the blocked list.

        Args:
            channel_id: Discord channel ID to block

        """
        self._blocked_channels.add(channel_id)
        logger.info(f"Added blocked channel: {channel_id}")

    def remove_blocked_channel(self, channel_id: int) -> None:
        """Remove a channel from the blocked list.

        Args:
            channel_id: Discord channel ID to unblock

        """
        self._blocked_channels.discard(channel_id)
        logger.info(f"Removed blocked channel: {channel_id}")

    def get_statistics(self) -> dict[str, int]:
        """Get permission statistics.

        Returns:
            Dictionary with permission statistics

        """
        return {
            "blocked_words": len(self._blocked_words),
            "blocked_users": len(self._blocked_users),
            "blocked_channels": len(self._blocked_channels),
            "allowed_domains": len(self._allowed_domains),
        }

    def reset_filters(self) -> None:
        """Reset all filters to default state."""
        self._blocked_words.clear()
        self._blocked_users.clear()
        self._blocked_channels.clear()
        self._allowed_domains.clear()
        logger.info("Reset all permission filters")

    # Test access methods
    def get_blocked_words(self) -> set[str]:
        """Get blocked words for testing.

        Returns:
            Set of blocked words

        """
        return self._blocked_words.copy()

    def get_blocked_users(self) -> set[int]:
        """Get blocked users for testing.

        Returns:
            Set of blocked user IDs

        """
        return self._blocked_users.copy()

    def get_blocked_channels(self) -> set[int]:
        """Get blocked channels for testing.

        Returns:
            Set of blocked channel IDs

        """
        return self._blocked_channels.copy()

    def get_allowed_domains(self) -> set[str]:
        """Get allowed domains for testing.

        Returns:
            Set of allowed domains

        """
        return self._allowed_domains.copy()
