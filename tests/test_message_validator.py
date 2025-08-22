"""Tests for MessageValidator component - TDD Approach (Red-Green-Refactor)."""

import unittest
from unittest.mock import MagicMock, patch

import discord
from .base_test import BaseTestCase, MockDiscordObjects
from discord_voice_bot.message_validator import MessageValidator, ValidationResult


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

    def setUp(self) -> None:
        """Set up test fixtures."""
        super().setUp()
        self.validator = MessageValidator()

    def test_initialization(self) -> None:
        """Test MessageValidator initializes correctly."""
        self.assertIsInstance(self.validator, MessageValidator)
        self.assertEqual(self.validator._blocked_words, set())
        self.assertEqual(self.validator._blocked_users, set())
        self.assertEqual(self.validator._blocked_channels, set())
        self.assertEqual(self.validator._allowed_domains, set())
        self.assertIsNotNone(self.validator._url_pattern)
        self.assertIsNotNone(self.validator._mention_pattern)
        self.assertIsNotNone(self.validator._suspicious_patterns)

    def test_should_process_message_valid(self) -> None:
        """Test should_process_message with valid message."""
        # Need to set channel ID to match config.target_voice_channel_id
        mock_message = MockDiscordObjects.create_mock_message("Hello world")
        # Import config to get the target channel ID
        from discord_voice_bot.config import config

        mock_message.channel.id = config.target_voice_channel_id

        result = self.validator.should_process_message(mock_message)

        self.assertTrue(result)

    def test_should_process_message_bot(self) -> None:
        """Test should_process_message filters bot messages."""
        mock_message = MockDiscordObjects.create_mock_message("Bot message")
        mock_message.author.bot = True

        result = self.validator.should_process_message(mock_message)

        self.assertFalse(result)

    def test_should_process_message_system(self) -> None:
        """Test should_process_message filters system messages."""
        mock_message = MockDiscordObjects.create_mock_message("System message")
        mock_message.type = MagicMock()
        mock_message.type.name = "pins_add"

        result = self.validator.should_process_message(mock_message)

        self.assertFalse(result)

    def test_should_process_message_empty(self) -> None:
        """Test should_process_message filters empty messages."""
        mock_message = MockDiscordObjects.create_mock_message("")

        result = self.validator.should_process_message(mock_message)

        self.assertFalse(result)

    def test_should_process_message_whitespace(self) -> None:
        """Test should_process_message filters whitespace-only messages."""
        mock_message = MockDiscordObjects.create_mock_message("   \n\t  ")

        result = self.validator.should_process_message(mock_message)

        self.assertFalse(result)

    def test_should_process_message_too_long(self) -> None:
        """Test should_process_message filters overly long messages."""
        long_content = "a" * 10001  # Very long message (over 10000 limit)
        mock_message = MockDiscordObjects.create_mock_message(long_content)

        result = self.validator.should_process_message(mock_message)

        self.assertFalse(result)

    async def test_validate_message_valid(self) -> None:
        """Test validate_message with valid message."""
        mock_message = MockDiscordObjects.create_mock_message("Hello world!")

        result = await self.validator.validate_message(mock_message)

        self.assertTrue(result.is_valid)
        self.assertEqual(result.reason, "")
        self.assertNotEqual(result.filtered_content, "")
        self.assertIn("original_length", result.metadata)
        self.assertIn("filtered_length", result.metadata)

    async def test_validate_message_bot(self) -> None:
        """Test validate_message filters bot messages."""
        mock_message = MockDiscordObjects.create_mock_message("Bot message")
        mock_message.author.bot = True

        result = await self.validator.validate_message(mock_message)

        self.assertFalse(result.is_valid)
        self.assertEqual(result.reason, "Bot messages are not processed")

    async def test_validate_message_system(self) -> None:
        """Test validate_message filters system messages."""
        mock_message = MockDiscordObjects.create_mock_message("System message")
        mock_message.type = MagicMock()
        mock_message.type.name = "pins_add"

        result = await self.validator.validate_message(mock_message)

        self.assertFalse(result.is_valid)
        self.assertIn("System message type:", result.reason)

    async def test_validate_message_empty(self) -> None:
        """Test validate_message filters empty messages."""
        mock_message = MockDiscordObjects.create_mock_message("")

        result = await self.validator.validate_message(mock_message)

        self.assertFalse(result.is_valid)
        self.assertEqual(result.reason, "Empty message content")

    async def test_validate_message_too_long(self) -> None:
        """Test validate_message filters overly long messages."""
        long_content = "a" * 10000
        mock_message = MockDiscordObjects.create_mock_message(long_content)

        result = await self.validator.validate_message(mock_message)

        self.assertFalse(result.is_valid)
        self.assertIn("Message too long", result.reason)

    async def test_validate_message_special_chars(self) -> None:
        """Test validate_message filters messages with excessive special characters."""
        special_content = "!@#$%^&*()!@#$%^&*()" * 50  # 80% special chars
        mock_message = MockDiscordObjects.create_mock_message(special_content)

        result = await self.validator.validate_message(mock_message)

        self.assertFalse(result.is_valid)
        self.assertEqual(result.reason, "Too many special characters")

    async def test_validate_message_blocked_word(self) -> None:
        """Test validate_message filters messages with blocked words."""
        self.validator.add_blocked_word("blocked")
        mock_message = MockDiscordObjects.create_mock_message("This contains blocked word")

        result = await self.validator.validate_message(mock_message)

        self.assertFalse(result.is_valid)
        self.assertIn("Blocked word detected:", result.reason)

    async def test_validate_message_suspicious_pattern(self) -> None:
        """Test validate_message filters messages with suspicious patterns."""
        mock_message = MockDiscordObjects.create_mock_message("<script>alert('xss')</script>")

        result = await self.validator.validate_message(mock_message)

        self.assertFalse(result.is_valid)
        self.assertIn("Suspicious content pattern detected:", result.reason)

    async def test_validate_message_blocked_user(self) -> None:
        """Test validate_message filters messages from blocked users."""
        blocked_user_id = 12345
        self.validator.add_blocked_user(blocked_user_id)
        mock_message = MockDiscordObjects.create_mock_message("Message from blocked user")
        mock_message.author.id = blocked_user_id

        result = await self.validator.validate_message(mock_message)

        self.assertFalse(result.is_valid)
        self.assertEqual(result.reason, "User is blocked from TTS")

    async def test_validate_message_blocked_channel(self) -> None:
        """Test validate_message filters messages from blocked channels."""
        blocked_channel_id = 67890
        self.validator.add_blocked_channel(blocked_channel_id)
        mock_message = MockDiscordObjects.create_mock_message("Message in blocked channel")
        mock_message.channel.id = blocked_channel_id

        result = await self.validator.validate_message(mock_message)

        self.assertFalse(result.is_valid)
        self.assertEqual(result.reason, "Channel is blocked from TTS")

    async def test_validate_message_with_urls(self) -> None:
        """Test validate_message handles URLs correctly."""
        mock_message = MockDiscordObjects.create_mock_message("Check this link: https://example.com")

        result = await self.validator.validate_message(mock_message)

        self.assertTrue(result.is_valid)
        self.assertIn("link", result.filtered_content)
        self.assertEqual(result.metadata["urls_removed"], 1)

    async def test_validate_message_with_mentions(self) -> None:
        """Test validate_message handles mentions correctly."""
        mock_message = MockDiscordObjects.create_mock_message("Hello <@123456> and <#987654>!")

        result = await self.validator.validate_message(mock_message)

        self.assertTrue(result.is_valid)
        self.assertIn("someone", result.filtered_content)
        self.assertIn("channel", result.filtered_content)
        self.assertEqual(result.metadata["mentions_removed"], 1)

    async def test_validate_message_with_emojis(self) -> None:
        """Test validate_message handles emojis correctly."""
        mock_message = MockDiscordObjects.create_mock_message("Hello! :smile: <a:animated:123>")

        result = await self.validator.validate_message(mock_message)

        self.assertTrue(result.is_valid)
        self.assertIn("emoji", result.filtered_content)

    async def test_validate_message_with_markdown(self) -> None:
        """Test validate_message handles markdown correctly."""
        mock_message = MockDiscordObjects.create_mock_message("**Bold** *italic* ~~strike~~ `code`")

        result = await self.validator.validate_message(mock_message)

        self.assertTrue(result.is_valid)
        self.assertEqual(result.filtered_content, "Bold italic strike code")

    def test_clean_markdown(self) -> None:
        """Test _clean_markdown removes markdown formatting."""
        content = "**bold** *italic* ~~strike~~ ||spoiler|| `code` >>> quote"
        result = self.validator._clean_markdown(content)

        self.assertEqual(result, "bold italic strike spoiler code  quote")

    def test_clean_whitespace(self) -> None:
        """Test _clean_whitespace normalizes whitespace."""
        content = "Multiple   spaces\n\n\nMultiple\n\n\nNewlines"
        result = self.validator._clean_whitespace(content)

        # _clean_whitespace replaces ALL whitespace with single spaces, then reduces excessive newlines
        # So newlines are converted to spaces, then excessive spaces are reduced
        self.assertEqual(result, "Multiple spaces Multiple Newlines")

    def test_validate_content_length_valid(self) -> None:
        """Test _validate_content_length with valid content."""
        content = "Valid content"
        result = ValidationResult(is_valid=True)

        is_valid = self.validator._validate_content_length(content, result)

        self.assertTrue(is_valid)
        self.assertTrue(result.is_valid)

    def test_validate_content_length_empty(self) -> None:
        """Test _validate_content_length with empty content."""
        content = ""
        result = ValidationResult(is_valid=True)

        is_valid = self.validator._validate_content_length(content, result)

        self.assertFalse(is_valid)
        self.assertFalse(result.is_valid)
        self.assertEqual(result.reason, "Content is empty after filtering")

    def test_validate_content_length_warning(self) -> None:
        """Test _validate_content_length with long content (should warn but not fail)."""
        content = "a" * 600  # Long but not too long
        result = ValidationResult(is_valid=True)

        is_valid = self.validator._validate_content_length(content, result)

        self.assertTrue(is_valid)
        self.assertTrue(result.is_valid)
        self.assertTrue(len(result.warnings) > 0)
        self.assertIn("may be too long for TTS", result.warnings[0])

    def test_add_remove_blocked_word(self) -> None:
        """Test adding and removing blocked words."""
        word = "testword"

        # Add word
        self.validator.add_blocked_word(word)
        self.assertIn(word.lower(), self.validator._blocked_words)

        # Remove word
        self.validator.remove_blocked_word(word)
        self.assertNotIn(word.lower(), self.validator._blocked_words)

    def test_add_remove_blocked_user(self) -> None:
        """Test adding and removing blocked users."""
        user_id = 12345

        # Add user
        self.validator.add_blocked_user(user_id)
        self.assertIn(user_id, self.validator._blocked_users)

        # Remove user
        self.validator.remove_blocked_user(user_id)
        self.assertNotIn(user_id, self.validator._blocked_users)

    def test_add_remove_blocked_channel(self) -> None:
        """Test adding and removing blocked channels."""
        channel_id = 67890

        # Add channel
        self.validator.add_blocked_channel(channel_id)
        self.assertIn(channel_id, self.validator._blocked_channels)

        # Remove channel
        self.validator.remove_blocked_channel(channel_id)
        self.assertNotIn(channel_id, self.validator._blocked_channels)

    def test_get_stats(self) -> None:
        """Test getting validation statistics."""
        # Add some test data
        self.validator.add_blocked_word("word1")
        self.validator.add_blocked_word("word2")
        self.validator.add_blocked_user(123)
        self.validator.add_blocked_channel(456)

        stats = self.validator.get_stats()

        expected_keys = ["blocked_words", "blocked_users", "blocked_channels", "allowed_domains", "max_message_length"]

        for key in expected_keys:
            self.assertIn(key, stats)

        self.assertEqual(stats["blocked_words"], 2)
        self.assertEqual(stats["blocked_users"], 1)
        self.assertEqual(stats["blocked_channels"], 1)

    def test_reset_filters(self) -> None:
        """Test resetting all filters."""
        # Add some test data
        self.validator.add_blocked_word("word")
        self.validator.add_blocked_user(123)
        self.validator.add_blocked_channel(456)

        # Reset
        self.validator.reset_filters()

        # Check all are cleared
        self.assertEqual(len(self.validator._blocked_words), 0)
        self.assertEqual(len(self.validator._blocked_users), 0)
        self.assertEqual(len(self.validator._blocked_channels), 0)
        self.assertEqual(len(self.validator._allowed_domains), 0)

    def test_blocked_word_case_insensitive(self) -> None:
        """Test blocked words are case-insensitive."""
        self.validator.add_blocked_word("TestWord")

        # Test different cases
        test_cases = ["testword", "TESTWORD", "TestWord", "testWord"]

        for word in test_cases:
            self.assertIn(word.lower(), self.validator._blocked_words)


if __name__ == "__main__":
    unittest.main()
