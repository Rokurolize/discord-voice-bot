"""Content filtering and cleaning for Discord Voice TTS Bot."""

import re

import discord
from loguru import logger


class ContentFilter:
    """Handles content filtering and cleaning for TTS processing."""

    def __init__(self) -> None:
        """Initialize content filter."""
        super().__init__()
        # URL and mention patterns
        self._url_pattern = re.compile(r"https?://[^\s]+")
        self._mention_pattern = re.compile(r"<@!?[0-9]+>")
        self._channel_mention_pattern = re.compile(r"<#[0-9]+>")
        self._role_mention_pattern = re.compile(r"<@&[0-9]+>")
        self._emoji_pattern = re.compile(r"<:[a-zA-Z0-9_]+:[0-9]+>")
        self._animated_emoji_pattern = re.compile(r"<a:[a-zA-Z0-9_]+:[0-9]+>")

        # Content limits
        self._max_message_length = 1000  # Will be set from config

        logger.info("Content filter initialized")

    def set_max_length(self, max_length: int) -> None:
        """Set maximum message length.

        Args:
            max_length: Maximum allowed message length

        """
        self._max_message_length = max_length

    async def filter_content(self, message: discord.Message) -> str:
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

    def validate_content_length(self, content: str) -> tuple[bool, str]:
        """Validate content length for TTS processing.

        Args:
            content: Filtered content

        Returns:
            Tuple of (is_valid, reason)

        """
        if not content:
            return False, "Content is empty after filtering"

        if len(content) > 500:  # Reasonable TTS limit
            return True, f"Content length {len(content)} may be too long for TTS"

        return True, ""

    # Test access methods
    def get_url_pattern(self) -> re.Pattern[str]:
        """Get URL pattern for testing.

        Returns:
            Compiled URL regex pattern

        """
        return self._url_pattern

    def get_mention_pattern(self) -> re.Pattern[str]:
        """Get mention pattern for testing.

        Returns:
            Compiled mention regex pattern

        """
        return self._mention_pattern

    def get_suspicious_patterns(self) -> list[str]:
        """Get suspicious patterns for testing.

        Returns:
            List of suspicious regex patterns

        """
        return []  # Moved to main validator for safety checks
