"""Core message validation for Discord Voice TTS Bot."""

import re
from dataclasses import dataclass, field
from typing import Any

import discord
from loguru import logger

from .config import Config
from .content_filter import ContentFilter
from .permission_manager import PermissionManager


@dataclass
class ValidationResult:
    """Result of message validation."""

    is_valid: bool
    reason: str = ""
    filtered_content: str = ""
    warnings: list[str] = field(default_factory=list)  # type: ignore
    metadata: dict[str, Any] = field(default_factory=dict)  # type: ignore


class MessageValidator:
    """Core validation logic for Discord messages."""

    def __init__(self, config: Config) -> None:
        """Initialize message validator."""
        self.config = config

        # Initialize components
        self.content_filter = ContentFilter()
        self.permission_manager = PermissionManager()
        self.content_filter.set_max_length(self.config.max_message_length)

        # Suspicious content patterns
        self._suspicious_patterns = [
            r"<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>",  # Script tags
            r"javascript:",  # JavaScript URLs
            r"onload=",  # Event handlers
            r"onerror=",
            r"data:text/html",
            r"vbscript:",
            r"onmouseover=",
            r"eval\s*\(",
            r"document\.cookie",
            r"document\.write",
        ]
        self._compiled_suspicious_patterns = [re.compile(p, re.IGNORECASE) for p in self._suspicious_patterns]

        # Content limits
        self._max_special_chars_ratio = 0.8  # Max ratio of special chars to total chars

        logger.debug("Message validator initialized")

    @property
    def max_message_length(self) -> int:
        """Get maximum message length from config."""
        return self.config.max_message_length

    def _get_enable_self_message_processing(self) -> bool:
        """Get enable self message processing setting from config."""
        return self.config.enable_self_message_processing

    async def validate_message(self, message: discord.Message) -> ValidationResult:
        """Validate a Discord message for TTS processing.

        Args:
            message: Discord message to validate

        Returns:
            Validation result

        """
        result = ValidationResult(is_valid=True)

        # Basic message checks
        if not await self._basic_message_check(message, result):
            return result

        # Content safety checks
        if not await self._content_safety_check(message, result):
            return result

        # User permission checks
        if not await self._user_permission_check(message, result):
            return result

        # Rate limiting checks
        if not await self._rate_limit_check(message, result):
            return result

        # Content filtering and sanitization
        filtered_content = await self.content_filter.filter_content(message)
        result.filtered_content = filtered_content

        # Content length validation
        is_valid, reason = self.content_filter.validate_content_length(filtered_content)
        if not is_valid:
            result.is_valid = False
            result.reason = reason
            return result

        if reason:  # Warning message
            result.warnings.append(reason)

        result.metadata.update(
            {
                "original_length": len(message.content),
                "filtered_length": len(filtered_content),
                "mentions_removed": len(self.content_filter.get_mention_pattern().findall(message.content)),
                "urls_removed": len(self.content_filter.get_url_pattern().findall(message.content)),
            }
        )

        logger.debug(f"Message {message.id} validated successfully")
        return result

    async def _basic_message_check(self, message: discord.Message, result: ValidationResult) -> bool:
        """Perform basic message validation checks.

        Args:
            message: Discord message
            result: Validation result to update

        Returns:
            True if checks pass, False otherwise

        """
        # Skip bot messages
        if message.author.bot:
            result.is_valid = False
            result.reason = "Bot messages are not processed"
            return False

        # Skip system messages
        if message.type != discord.MessageType.default:
            result.is_valid = False
            result.reason = f"System message type: {message.type}"
            return False

        # Skip empty messages
        if not message.content or not message.content.strip():
            result.is_valid = False
            result.reason = "Empty message content"
            return False

        # Check message length limits
        if len(message.content) > self.max_message_length:
            result.is_valid = False
            result.reason = f"Message too long ({len(message.content)} > {self.max_message_length})"
            return False

        # Check for excessive special characters
        special_chars = sum(1 for c in message.content if not c.isalnum() and not c.isspace())
        if special_chars / len(message.content) > self._max_special_chars_ratio:
            result.is_valid = False
            result.reason = "Too many special characters"
            return False

        return True

    async def _content_safety_check(self, message: discord.Message, result: ValidationResult) -> bool:
        """Check message content for safety and appropriateness.

        Args:
            message: Discord message
            result: Validation result to update

        Returns:
            True if content is safe, False otherwise

        """
        # Check for blocked words via permission manager
        is_safe, reason = self.permission_manager.check_content_safety(message)
        if not is_safe:
            result.is_valid = False
            result.reason = reason
            return False

        # Check for suspicious patterns
        for pattern in self._compiled_suspicious_patterns:
            if pattern.search(message.content):
                result.is_valid = False
                result.reason = f"Suspicious content pattern detected: {pattern.pattern}"
                result.warnings.append("Message contains potentially harmful content")
                return False

        return True

    async def _user_permission_check(self, message: discord.Message, result: ValidationResult) -> bool:
        """Check if user has permission to send TTS messages.

        Args:
            message: Discord message
            result: Validation result to update

        Returns:
            True if user has permission, False otherwise

        """
        has_permission, reason = await self.permission_manager.check_user_permission(message)
        if not has_permission:
            result.is_valid = False
            result.reason = reason
            return False

        return True

    async def _rate_limit_check(self, message: discord.Message, result: ValidationResult) -> bool:
        """Check if user is within rate limits.

        Args:
            message: Discord message
            result: Validation result to update

        Returns:
            True if within limits, False otherwise

        """
        within_limits, reason = await self.permission_manager.check_rate_limit(message)
        if not within_limits:
            result.is_valid = False
            result.reason = reason
            return False

        return True

    def should_process_message(self, message: discord.Message, bot_user_id: int | None = None) -> bool:
        """Quick check to determine if message should be processed.

        Args:
            message: Discord message
            bot_user_id: Optional bot user ID for self-message processing

        Returns:
            True if message should be processed, False otherwise

        """
        # Quick checks without full validation
        if message.author.bot:
            # Allow self-messages if enabled and bot_user_id is provided
            if self._get_enable_self_message_processing() and bot_user_id and message.author.id == bot_user_id:
                logger.debug(f"Allowing self-message from bot {bot_user_id}")
            else:
                return False

        if message.type != discord.MessageType.default:
            return False

        if not message.content or not message.content.strip():
            return False

        if len(message.content) > self.max_message_length:
            return False

        return True

    def get_stats(self) -> dict[str, Any]:
        """Get validation statistics.

        Returns:
            Dictionary with validation statistics

        """
        permission_stats = self.permission_manager.get_statistics()
        return {
            **permission_stats,
            "max_message_length": self.max_message_length,
        }

    # Delegation methods for backward compatibility
    def add_blocked_word(self, word: str) -> None:
        """Add a word to the blocked list.

        Args:
            word: Word to block

        """
        self.permission_manager.add_blocked_word(word)

    def remove_blocked_word(self, word: str) -> None:
        """Remove a word from the blocked list.

        Args:
            word: Word to unblock

        """
        self.permission_manager.remove_blocked_word(word)

    def add_blocked_user(self, user_id: int) -> None:
        """Add a user to the blocked list.

        Args:
            user_id: Discord user ID to block

        """
        self.permission_manager.add_blocked_user(user_id)

    def remove_blocked_user(self, user_id: int) -> None:
        """Remove a user from the blocked list.

        Args:
            user_id: Discord user ID to unblock

        """
        self.permission_manager.remove_blocked_user(user_id)

    def add_blocked_channel(self, channel_id: int) -> None:
        """Add a channel to the blocked list.

        Args:
            channel_id: Discord channel ID to block

        """
        self.permission_manager.add_blocked_channel(channel_id)

    def remove_blocked_channel(self, channel_id: int) -> None:
        """Remove a channel from the blocked list.

        Args:
            channel_id: Discord channel ID to unblock

        """
        self.permission_manager.remove_blocked_channel(channel_id)

    def reset_filters(self) -> None:
        """Reset all filters to default state."""
        self.permission_manager.reset_filters()

    # Test access methods
    def get_blocked_words(self) -> set[str]:
        """Get blocked words for testing.

        Returns:
            Set of blocked words

        """
        return self.permission_manager.get_blocked_words()

    def get_blocked_users(self) -> set[int]:
        """Get blocked users for testing.

        Returns:
            Set of blocked user IDs

        """
        return self.permission_manager.get_blocked_users()

    def get_blocked_channels(self) -> set[int]:
        """Get blocked channels for testing.

        Returns:
            Set of blocked channel IDs

        """
        return self.permission_manager.get_blocked_channels()

    def get_allowed_domains(self) -> set[str]:
        """Get allowed domains for testing.

        Returns:
            Set of allowed domains

        """
        return self.permission_manager.get_allowed_domains()

    def get_url_pattern(self) -> re.Pattern[str]:
        """Get URL pattern for testing.

        Returns:
            Compiled URL regex pattern

        """
        return self.content_filter.get_url_pattern()

    def get_mention_pattern(self) -> re.Pattern[str]:
        """Get mention pattern for testing.

        Returns:
            Compiled mention regex pattern

        """
        return self.content_filter.get_mention_pattern()

    def get_suspicious_patterns(self) -> list[str]:
        """Get suspicious patterns for testing.

        Returns:
            List of suspicious regex patterns

        """
        return self._suspicious_patterns.copy()
