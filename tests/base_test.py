"""Base test infrastructure for Discord Voice TTS Bot tests."""

import unittest
from typing import Any, override
from unittest.mock import MagicMock


class BaseTestCase(unittest.TestCase):
    """Base test case with common utilities."""

    def __init__(self, methodName: str = "runTest", *args: Any, **kwargs: Any) -> None:
        """Initialize test case."""
        # Handle pytest compatibility - pytest doesn't pass methodName
        if not args and not methodName.startswith("test_"):
            methodName = "runTest"
        super().__init__(methodName, *args, **kwargs)
        self.mock_logger: MagicMock = MagicMock()

    @override
    def setUp(self) -> None:
        """Set up test fixtures."""
        super().setUp()
        self.mock_logger = MagicMock()

    @override
    def tearDown(self) -> None:
        """Clean up test fixtures."""
        super().tearDown()

    def assertDictContainsSubset(self, subset: dict[str, Any], dictionary: dict[str, Any]) -> None:
        """Assert that dictionary contains all key-value pairs from subset."""
        for key, value in subset.items():
            self.assertIn(key, dictionary)
            self.assertEqual(dictionary[key], value)


class AsyncTestCase(BaseTestCase):
    """Base test case for async tests."""

    @override
    def setUp(self) -> None:
        """Set up async test fixtures."""
        super().setUp()

    @override
    def tearDown(self) -> None:
        """Clean up async test fixtures."""
        super().tearDown()


class MockDiscordObjects:
    """Factory for creating mock Discord objects."""

    @staticmethod
    def create_mock_message(content: str = "test message", author_name: str = "test_user") -> MagicMock:
        """Create a mock Discord message."""
        import discord

        mock_message = MagicMock()
        mock_message.content = content
        mock_message.author.display_name = author_name
        mock_message.author.name = author_name
        mock_message.author.id = 12345
        mock_message.author.bot = False  # Important: explicitly set bot to False
        mock_message.id = 67890
        mock_message.channel.id = 11111
        mock_message.guild = MagicMock()  # Treat as a server message
        mock_message.type = discord.MessageType.default
        return mock_message

    @staticmethod
    def create_mock_bot() -> MagicMock:
        """Create a mock Discord bot."""
        mock_bot = MagicMock()
        mock_bot.user = MagicMock()
        mock_bot.user.id = 12345
        mock_bot.user.name = "TestBot"
        mock_bot.guilds = []
        return mock_bot

    @staticmethod
    def create_mock_voice_state(channel_name: str = "Test Channel", channel_id: int = 12345) -> MagicMock:
        """Create a mock Discord voice state."""
        mock_state = MagicMock()
        if channel_name:
            mock_state.channel = MagicMock()
            mock_state.channel.name = channel_name
            mock_state.channel.id = channel_id
        else:
            mock_state.channel = None
        return mock_state
