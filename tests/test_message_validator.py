"""Tests for MessageValidator component - TDD Approach (Red-Green-Refactor)."""

import unittest
from typing import override
from unittest.mock import MagicMock

import pytest

from discord_voice_bot.message_validator import MessageValidator, ValidationResult

from .base_test import BaseTestCase, MockDiscordObjects


class TestValidationResult(BaseTestCase):
    """Test cases for ValidationResult data class."""

    def test_validation_result_initialization(self) -> None:
        """Test ValidationResult initializes with correct default values."""
        result = ValidationResult(is_valid=False)

        self.assertFalse(result.is_valid)
        self.assertEqual(result.reason, "")
        self.assertEqual(result.filtered_content, "")
        self.assertEqual(result.warnings, [])
        self.assertEqual(result.metadata, {})

    def test_validation_result_with_values(self) -> None:
        """Test ValidationResult with custom values."""
        result = ValidationResult(is_valid=True, reason="Test reason", filtered_content="filtered content", warnings=["warning1", "warning2"], metadata={"key": "value"})

        self.assertTrue(result.is_valid)
        self.assertEqual(result.reason, "Test reason")
        self.assertEqual(result.filtered_content, "filtered content")
        self.assertEqual(result.warnings, ["warning1", "warning2"])
        self.assertEqual(result.metadata, {"key": "value"})


class TestMessageValidator(BaseTestCase):
    """Test cases for MessageValidator - Main component."""

    def __init__(self, methodName: str = "runTest") -> None:
        """Initialize test case."""
        super().__init__(methodName)
        self.validator: MessageValidator

    @override
    def setUp(self) -> None:
        """Set up test fixtures."""
        super().setUp()
        self.validator = MessageValidator()

    def test_initialization(self) -> None:
        """Test MessageValidator initializes correctly."""
        assert isinstance(self.validator, MessageValidator)
        assert self.validator.get_blocked_words() == set()
        assert self.validator.get_blocked_users() == set()
        assert self.validator.get_blocked_channels() == set()
        assert self.validator.get_allowed_domains() == set()
        assert self.validator.get_url_pattern() is not None
        assert self.validator.get_mention_pattern() is not None
        assert self.validator.get_suspicious_patterns() is not None

    def test_should_process_message_valid(self) -> None:
        """Test should_process_message with valid message."""
        # Need to set channel ID to match config.target_voice_channel_id
        mock_message = MockDiscordObjects.create_mock_message("Hello world")
        # Import config to get the target channel ID
        from discord_voice_bot.config import config

        mock_message.channel.id = config.target_voice_channel_id

        result = self.validator.should_process_message(mock_message)

        assert result

    def test_should_process_message_bot(self) -> None:
        """Test should_process_message filters bot messages."""
        mock_message = MockDiscordObjects.create_mock_message("Bot message")
        mock_message.author.bot = True

        result = self.validator.should_process_message(mock_message)

        assert not result

    def test_should_process_message_system(self) -> None:
        """Test should_process_message filters system messages."""
        mock_message = MockDiscordObjects.create_mock_message("System message")
        mock_message.type = MagicMock()
        mock_message.type.name = "pins_add"

        result = self.validator.should_process_message(mock_message)

        assert not result

    def test_should_process_message_empty(self) -> None:
        """Test should_process_message filters empty messages."""
        mock_message = MockDiscordObjects.create_mock_message("")

        result = self.validator.should_process_message(mock_message)

        assert not result

    def test_should_process_message_whitespace(self) -> None:
        """Test should_process_message filters whitespace-only messages."""
        mock_message = MockDiscordObjects.create_mock_message("   \n\t  ")

        result = self.validator.should_process_message(mock_message)

        assert not result

    def test_should_process_message_too_long(self) -> None:
        """Test should_process_message filters overly long messages."""
        long_content = "a" * 10001  # Very long message (over 10000 limit)
        mock_message = MockDiscordObjects.create_mock_message(long_content)

        result = self.validator.should_process_message(mock_message)

        assert not result

    @pytest.mark.asyncio
    async def test_validate_message_valid(self) -> None:
        """Test validate_message with valid message."""
        mock_message = MockDiscordObjects.create_mock_message("Hello world!")

        result = await self.validator.validate_message(mock_message)

        assert result.is_valid
        assert result.reason == ""
        assert result.filtered_content != ""
        assert "original_length" in result.metadata
        assert "filtered_length" in result.metadata

    @pytest.mark.asyncio
    async def test_validate_message_bot(self) -> None:
        """Test validate_message filters bot messages."""
        mock_message = MockDiscordObjects.create_mock_message("Bot message")
        mock_message.author.bot = True

        result = await self.validator.validate_message(mock_message)

        assert not result.is_valid
        assert result.reason == "Bot messages are not processed"

    @pytest.mark.asyncio
    async def test_validate_message_system(self) -> None:
        """Test validate_message filters system messages."""
        mock_message = MockDiscordObjects.create_mock_message("System message")
        mock_message.type = MagicMock()
        mock_message.type.name = "pins_add"

        result = await self.validator.validate_message(mock_message)

        assert not result.is_valid
        assert "System message type:" in result.reason

    @pytest.mark.asyncio
    async def test_validate_message_empty(self) -> None:
        """Test validate_message filters empty messages."""
        mock_message = MockDiscordObjects.create_mock_message("")

        result = await self.validator.validate_message(mock_message)

        assert not result.is_valid
        assert result.reason == "Empty message content"

    @pytest.mark.asyncio
    async def test_validate_message_too_long(self) -> None:
        """Test validate_message filters overly long messages."""
        long_content = "a" * 10001  # Use 10001 to exceed the 10000 limit
        mock_message = MockDiscordObjects.create_mock_message(long_content)

        result = await self.validator.validate_message(mock_message)

        assert not result.is_valid
        assert "Message too long" in result.reason

    @pytest.mark.asyncio
    async def test_validate_message_special_chars(self) -> None:
        """Test validate_message filters messages with excessive special characters."""
        special_content = "!@#$%^&*()!@#$%^&*()" * 50  # 80% special chars
        mock_message = MockDiscordObjects.create_mock_message(special_content)

        result = await self.validator.validate_message(mock_message)

        assert not result.is_valid
        assert result.reason == "Too many special characters"

    @pytest.mark.asyncio
    async def test_validate_message_blocked_word(self) -> None:
        """Test validate_message filters messages with blocked words."""
        self.validator.add_blocked_word("blocked")
        mock_message = MockDiscordObjects.create_mock_message("This contains blocked word")

        result = await self.validator.validate_message(mock_message)

        assert not result.is_valid
        assert "Blocked word detected:" in result.reason

    @pytest.mark.asyncio
    async def test_validate_message_suspicious_pattern(self) -> None:
        """Test validate_message filters messages with suspicious patterns."""
        mock_message = MockDiscordObjects.create_mock_message("<script>alert('xss')</script>")

        result = await self.validator.validate_message(mock_message)

        assert not result.is_valid
        assert "Suspicious content pattern detected:" in result.reason

    @pytest.mark.asyncio
    async def test_validate_message_blocked_user(self) -> None:
        """Test validate_message filters messages from blocked users."""
        blocked_user_id = 12345
        self.validator.add_blocked_user(blocked_user_id)
        mock_message = MockDiscordObjects.create_mock_message("Message from blocked user")
        mock_message.author.id = blocked_user_id

        result = await self.validator.validate_message(mock_message)

        assert not result.is_valid
        assert result.reason == "User is blocked from TTS"

    @pytest.mark.asyncio
    async def test_validate_message_blocked_channel(self) -> None:
        """Test validate_message filters messages from blocked channels."""
        blocked_channel_id = 67890
        self.validator.add_blocked_channel(blocked_channel_id)
        mock_message = MockDiscordObjects.create_mock_message("Message in blocked channel")
        mock_message.channel.id = blocked_channel_id

        result = await self.validator.validate_message(mock_message)

        assert not result.is_valid
        assert result.reason == "Channel is blocked from TTS"

    @pytest.mark.asyncio
    async def test_validate_message_with_urls(self) -> None:
        """Test validate_message handles URLs correctly."""
        mock_message = MockDiscordObjects.create_mock_message("Check this link: https://example.com")

        result = await self.validator.validate_message(mock_message)

        assert result.is_valid
        assert "link" in result.filtered_content
        assert result.metadata["urls_removed"] == 1

    @pytest.mark.asyncio
    async def test_validate_message_with_mentions(self) -> None:
        """Test validate_message handles mentions correctly."""
        mock_message = MockDiscordObjects.create_mock_message("Hello <@123456> and <#987654>!")

        result = await self.validator.validate_message(mock_message)

        assert result.is_valid
        assert "someone" in result.filtered_content
        assert "channel" in result.filtered_content
        assert result.metadata["mentions_removed"] == 1

    @pytest.mark.asyncio
    async def test_validate_message_with_emojis(self) -> None:
        """Test validate_message handles emojis correctly."""
        mock_message = MockDiscordObjects.create_mock_message("Hello! :smile: <a:animated:123>")

        result = await self.validator.validate_message(mock_message)

        assert result.is_valid
        assert "emoji" in result.filtered_content

    @pytest.mark.asyncio
    async def test_validate_message_with_markdown(self) -> None:
        """Test validate_message handles markdown correctly."""
        mock_message = MockDiscordObjects.create_mock_message("**Bold** *italic* ~~strike~~ `code`")

        result = await self.validator.validate_message(mock_message)

        assert result.is_valid
        assert result.filtered_content == "Bold italic strike code"


if __name__ == "__main__":
    _ = unittest.main()
