"""Message validation and filtering for Discord Voice TTS Bot."""

import re
from dataclasses import dataclass, field
from typing import Any

import discord
from loguru import logger

from .config import config


@dataclass
class ValidationResult:
    """Result of message validation."""

    is_valid: bool
    reason: str = ""
    filtered_content: str = ""
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class MessageValidator:
    """Validates and filters messages for TTS processing."""

    def __init__(self) -> None:
        """Initialize message validator."""
        # Content filters
        self._blocked_words: set[str] = set()
        self._allowed_domains: set[str] = set()
        self._blocked_users: set[int] = set()
        self._blocked_channels: set[int] = set()

        # Pattern filters
        self._url_pattern = re.compile(r"https?://[^\s]+")
        self._mention_pattern = re.compile(r"<@!?[0-9]+>")
        self._channel_mention_pattern = re.compile(r"<#[0-9]+>")
        self._role_mention_pattern = re.compile(r"<@&[0-9]+>")
        self._emoji_pattern = re.compile(r"<:[a-zA-Z0-9_]+:[0-9]+>")
        self._animated_emoji_pattern = re.compile(r"<a:[a-zA-Z0-9_]+:[0-9]+>")

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

        # Content limits
        self._max_message_length = config.max_message_length
        self._max_special_chars_ratio = 0.8  # Max ratio of special chars to total chars

        logger.info("Message validator initialized")

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
        filtered_content = await self._filter_content(message)
        result.filtered_content = filtered_content

        # Content length validation
        if not self._validate_content_length(filtered_content, result):
            return result

        result.metadata.update(
            {
                "original_length": len(message.content),
                "filtered_length": len(filtered_content),
                "mentions_removed": len(self._mention_pattern.findall(message.content)),
                "urls_removed": len(self._url_pattern.findall(message.content)),
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
        if len(message.content) > self._max_message_length:
            result.is_valid = False
            result.reason = f"Message too long ({len(message.content)} > {self._max_message_length})"
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
        content_lower = message.content.lower()

        # Check for blocked words
        for word in self._blocked_words:
            if word.lower() in content_lower:
                result.is_valid = False
                result.reason = f"Blocked word detected: {word}"
                return False

        # Check for suspicious patterns
        for pattern in self._suspicious_patterns:
            if re.search(pattern, content_lower, re.IGNORECASE):
                result.is_valid = False
                result.reason = f"Suspicious content pattern detected: {pattern}"
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
        # Check blocked users
        if message.author.id in self._blocked_users:
            result.is_valid = False
            result.reason = "User is blocked from TTS"
            return False

        # Check blocked channels
        if message.channel.id in self._blocked_channels:
            result.is_valid = False
            result.reason = "Channel is blocked from TTS"
            return False

        # Additional permission checks can be added here
        # e.g., role-based permissions, server-specific rules

        return True

    async def _rate_limit_check(self, message: discord.Message, result: ValidationResult) -> bool:
        """Check if user is within rate limits.

        Args:
            message: Discord message
            result: Validation result to update

        Returns:
            True if within limits, False otherwise
        """
        # This would integrate with a rate limiter
        # For now, we'll assume it's handled elsewhere
        # but this provides the interface for future implementation

        # Placeholder for rate limiting logic
        # if self.rate_limiter.is_rate_limited(message.author.id):
        #     result.is_valid = False
        #     result.reason = "Rate limit exceeded"
        #     return False

        return True

    async def _filter_content(self, message: discord.Message) -> str:
        """Filter and clean message content for TTS.

        Args:
            message: Discord message

        Returns:
            Filtered content suitable for TTS
        """
        content = message.content

        # Remove URLs
        content = self._url_pattern.sub("link", content)

        # Replace mentions
        content = self._mention_pattern.sub("someone", content)
        content = self._channel_mention_pattern.sub("channel", content)
        content = self._role_mention_pattern.sub("role", content)

        # Replace emojis
        content = self._emoji_pattern.sub("emoji", content)
        content = self._animated_emoji_pattern.sub("emoji", content)

        # Clean markdown formatting
        content = self._clean_markdown(content)

        # Clean whitespace
        content = self._clean_whitespace(content)

        return content.strip()

    def _clean_markdown(self, content: str) -> str:
        """Remove markdown formatting from content.

        Args:
            content: Content with markdown

        Returns:
            Content without markdown
        """
        # Remove common markdown patterns
        replacements = {
            "**": "",  # Bold
            "*": "",  # Italic
            "_": "",  # Underline
            "~~": "",  # Strikethrough
            "||": "",  # Spoiler
            "`": "",  # Code
            ">>>": "",  # Block quotes
            ">": "",  # Quotes
        }

        for old, new in replacements.items():
            content = content.replace(old, new)

        return content

    def _clean_whitespace(self, content: str) -> str:
        """Clean excessive whitespace.

        Args:
            content: Content to clean

        Returns:
            Content with normalized whitespace
        """
        # Replace multiple spaces with single space
        content = re.sub(r"\s+", " ", content)

        # Remove excessive newlines
        content = re.sub(r"\n{3,}", "\n\n", content)

        return content.strip()

    def _validate_content_length(self, content: str, result: ValidationResult) -> bool:
        """Validate content length for TTS processing.

        Args:
            content: Filtered content
            result: Validation result to update

        Returns:
            True if length is valid, False otherwise
        """
        if not content:
            result.is_valid = False
            result.reason = "Content is empty after filtering"
            return False

        if len(content) > 500:  # Reasonable TTS limit
            result.warnings.append(f"Content length {len(content)} may be too long for TTS")
            # Don't fail validation, just warn

        return True

    def should_process_message(self, message: discord.Message) -> bool:
        """Quick check to determine if message should be processed.

        Args:
            message: Discord message

        Returns:
            True if message should be processed, False otherwise
        """
        # Quick checks without full validation
        if message.author.bot:
            return False

        if message.type != discord.MessageType.default:
            return False

        if not message.content or not message.content.strip():
            return False

        if len(message.content) > self._max_message_length:
            return False

        return True

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

    def get_stats(self) -> dict[str, Any]:
        """Get validation statistics.

        Returns:
            Dictionary with validation statistics
        """
        return {
            "blocked_words": len(self._blocked_words),
            "blocked_users": len(self._blocked_users),
            "blocked_channels": len(self._blocked_channels),
            "allowed_domains": len(self._allowed_domains),
            "max_message_length": self._max_message_length,
        }

    def reset_filters(self) -> None:
        """Reset all filters to default state."""
        self._blocked_words.clear()
        self._blocked_users.clear()
        self._blocked_channels.clear()
        self._allowed_domains.clear()
        logger.info("Reset all message filters")
