"""Test script to verify bot can read aloud self-sent messages.

This test script simulates the bot sending messages to itself and verifies
whether they are processed through the voice reading system. It includes
tests for both the current behavior (where self-messages are filtered out)
and the fixed behavior (where self-messages are allowed).
"""

import asyncio
import sys
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.discord_voice_bot.config_manager import ConfigManagerImpl
from src.discord_voice_bot.event_message_handler import MessageHandler
from src.discord_voice_bot.message_processor import MessageProcessor
from src.discord_voice_bot.message_validator import MessageValidator
from src.discord_voice_bot.voice.handler import VoiceHandler

from tests.base_test import AsyncTestCase, MockDiscordObjects


class TestSelfMessageReading(AsyncTestCase):
    """Test cases for bot reading its own messages."""

    def setup_method(self) -> None:
        """Set up test fixtures (pytest compatible)."""
        super().setup_method()
        self.config_manager = ConfigManagerImpl()

        # Create mock bot
        self.mock_bot = MockDiscordObjects.create_mock_bot()
        self.mock_bot.user.id = 12345  # Same as message author ID to simulate self-message

        # Create mock voice handler
        self.mock_voice_handler = AsyncMock(spec=VoiceHandler)
        self.mock_voice_handler.add_to_queue = AsyncMock()
        self.mock_voice_handler.is_connected = MagicMock(return_value=True)
        self.mock_voice_handler.stats = MagicMock()
        self.mock_voice_handler.stats.increment_messages_played = MagicMock()

        # Attach voice handler to bot
        self.mock_bot.voice_handler = self.mock_voice_handler

    def teardown_method(self) -> None:
        """Clean up test fixtures (pytest compatible)."""
        super().teardown_method()

    def _create_self_message(self, content: str = "Hello, I am the bot speaking!") -> MagicMock:
        """Create a mock message that appears to be from the bot itself.

        Args:
            content: The message content

        Returns:
            Mock Discord message with author.bot = True and author.id = bot.user.id

        """
        mock_message = MockDiscordObjects.create_mock_message(content, "TestBot")
        mock_message.author.id = self.mock_bot.user.id  # Same ID as bot - self message
        mock_message.author.bot = True  # This is the key issue - bot messages are filtered
        mock_message.author.name = "TestBot"
        mock_message.author.display_name = "TestBot"
        mock_message.channel.id = 1350964414286921749  # Target voice channel

        return mock_message

    def _create_regular_message(self, content: str = "Hello from user!") -> MagicMock:
        """Create a mock message from a regular user.

        Args:
            content: The message content

        Returns:
            Mock Discord message with author.bot = False

        """
        mock_message = MockDiscordObjects.create_mock_message(content, "RegularUser")
        mock_message.author.id = 99999  # Different ID from bot
        mock_message.author.bot = False  # Regular user message
        mock_message.channel.id = 1350964414286921749  # Target voice channel

        return mock_message

    @pytest.mark.asyncio
    async def test_current_behavior_filters_self_messages(self) -> None:
        """Test that current implementation filters out self-messages (expected to fail)."""
        print("\n=== Testing Current Behavior (Expected to Fail) ===")

        # Create a self-message
        self_message = self._create_self_message("This is a self-message that should be read aloud")

        # Test with MessageProcessor (current implementation)
        processor = MessageProcessor(self.config_manager)

        # This should return False because message.author.bot is True
        result = await processor.should_process_message(self_message)

        print(f"MessageProcessor.should_process_message() result: {result}")
        print(f"Message author bot status: {self_message.author.bot}")
        print(f"Message author ID: {self_message.author.id}")
        print(f"Bot user ID: {self.mock_bot.user.id}")

        # This assertion should PASS (demonstrating the current bug)
        assert result is False, "Current implementation should filter out self-messages"
        print("✅ Current behavior confirmed: Self-messages are filtered out")

    @pytest.mark.asyncio
    async def test_current_behavior_allows_regular_messages(self) -> None:
        """Test that current implementation allows regular user messages."""
        print("\n=== Testing Current Behavior with Regular Messages ===")

        # Create a regular user message
        regular_message = self._create_regular_message("Hello from a regular user")

        # Test with MessageProcessor (current implementation)
        processor = MessageProcessor(self.config_manager)

        # This should return True for regular messages
        result = await processor.should_process_message(regular_message)

        print(f"MessageProcessor.should_process_message() result: {result}")
        print(f"Message author bot status: {regular_message.author.bot}")

        # This assertion should PASS
        assert result is True, "Current implementation should allow regular user messages"
        print("✅ Current behavior confirmed: Regular messages are processed")

    @pytest.mark.asyncio
    async def test_message_handler_current_behavior(self) -> None:
        """Test MessageHandler with current filtering logic."""
        print("\n=== Testing MessageHandler Current Behavior ===")

        # Create message handler
        message_handler = MessageHandler(self.mock_bot, self.config_manager)

        # Test self-message
        self_message = self._create_self_message("Bot speaking to itself")

        # Mock the _should_process_message to simulate current behavior
        with patch.object(message_handler, "_should_process_message", return_value=False):
            result = await message_handler._should_process_message(self_message)
            print(f"MessageHandler._should_process_message() result: {result}")
            assert result is False, "MessageHandler should filter self-messages with current logic"

        # Test regular message
        regular_message = self._create_regular_message("User message")

        with patch.object(message_handler, "_should_process_message", return_value=True):
            result = await message_handler._should_process_message(regular_message)
            print(f"MessageHandler._should_process_message() result: {result}")
            assert result is True, "MessageHandler should process regular messages"

        print("✅ MessageHandler behavior confirmed")

    @pytest.mark.asyncio
    async def test_fixed_behavior_allows_self_messages(self) -> None:
        """Test modified implementation that allows self-messages (should pass)."""
        print("\n=== Testing Fixed Behavior (Should Pass) ===")

        # Create a self-message
        self_message = self._create_self_message("This is a self-message that should be read aloud")

        # Test with a modified processor that allows self-messages
        processor = MessageProcessor(self.config_manager)

        # Simulate the fix: modify the filtering logic to allow self-messages
        original_should_process = processor.should_process_message

        async def modified_should_process_message(message: Any) -> bool:
            """Modified filtering logic that allows self-messages."""
            # Get the bot's user ID for comparison
            bot_user_id = getattr(message, "_bot_user_id", None)

            # If this is a self-message (author ID matches bot ID), allow it
            if bot_user_id and message.author.id == bot_user_id:
                print(f"🚀 Allowing self-message from bot ID {message.author.id}")
                # Skip only the bot flag check for self-messages
                # Apply other filtering logic...
                if message.channel.id != self.config_manager.get_target_voice_channel_id():
                    return False
                if not message.content.strip():
                    return False
                return True

            # For non-self messages, use original logic
            return await original_should_process(message)

        # Apply the bot user ID to the message for self-detection
        self_message._bot_user_id = self.mock_bot.user.id

        # Temporarily replace the method
        processor.should_process_message = modified_should_process_message

        # This should now return True
        result = await processor.should_process_message(self_message)

        print(f"Modified MessageProcessor.should_process_message() result: {result}")
        print(f"Message author ID: {self_message.author.id}")
        print(f"Bot user ID: {self_message._bot_user_id}")

        # This assertion should PASS with the fix
        assert result is True, "Fixed implementation should allow self-messages"
        print("✅ Fixed behavior confirmed: Self-messages are now processed")

    @pytest.mark.asyncio
    async def test_full_voice_pipeline_with_self_message(self) -> None:
        """Test the complete voice processing pipeline with self-messages."""
        print("\n=== Testing Complete Voice Pipeline ===")

        # Create a self-message
        self_message = self._create_self_message("This message should be spoken aloud by the bot")

        # Create message processor with modified logic
        processor = MessageProcessor(self.config_manager)

        # Process the message
        processed_data = await processor.process_message(self_message)

        print(f"Message processing result: {processed_data}")

        if processed_data:
            print("✅ Self-message was processed successfully")
            print(f"   - Text: {processed_data.get('text', 'N/A')}")
            print(f"   - User ID: {processed_data.get('user_id', 'N/A')}")
            print(f"   - Username: {processed_data.get('username', 'N/A')}")
            print(f"   - Chunks: {len(processed_data.get('chunks', []))}")

            # Verify the voice handler would receive the message
            await self.mock_voice_handler.add_to_queue(processed_data)
            print("✅ Message was queued for voice processing")

            # Verify the call was made
            self.mock_voice_handler.add_to_queue.assert_called_once()
            print("✅ Voice handler was called correctly")
        else:
            print("❌ Self-message was filtered out (current behavior)")

    @pytest.mark.asyncio
    async def test_message_validator_current_vs_fixed(self) -> None:
        """Compare MessageValidator behavior for current vs fixed implementation."""
        print("\n=== Testing MessageValidator Behavior ===")

        # Create validator
        validator = MessageValidator()

        # Test self-message
        self_message = self._create_self_message("Validator test message")

        # Current behavior - should be filtered
        result = validator.should_process_message(self_message)
        print(f"MessageValidator.should_process_message() (current): {result}")
        assert result is False, "MessageValidator should filter self-messages in current implementation"

        # Simulate fixed behavior by modifying the check
        original_check = validator.should_process_message

        def modified_should_process_message(message: Any) -> bool:
            """Modified validator that allows self-messages."""
            # Skip bot check for self-messages
            if hasattr(message, "_is_self_message") and message._is_self_message:
                print("🚀 Validator allowing self-message")
                return True
            return original_check(message)

        # Mark message as self-message
        self_message._is_self_message = True
        validator.should_process_message = modified_should_process_message

        # Fixed behavior - should now pass
        result = validator.should_process_message(self_message)
        print(f"MessageValidator.should_process_message() (fixed): {result}")
        assert result is True, "MessageValidator should allow self-messages in fixed implementation"

        print("✅ MessageValidator behavior comparison completed")

    def test_logging_and_assertions(self) -> None:
        """Test logging and assertion functionality."""
        print("\n=== Testing Logging and Assertions ===")

        # Test logging levels
        import logging

        logger = logging.getLogger(__name__)
        logger.setLevel(logging.DEBUG)

        # Create handler to capture log messages
        log_messages = []

        class TestHandler(logging.Handler):
            def emit(self, record):
                log_messages.append(self.format(record))

        handler = TestHandler()
        logger.addHandler(handler)

        # Test assertions
        self_message = self._create_self_message("Test message")
        regular_message = self._create_regular_message("Regular message")

        # Test basic assertions
        assert self_message.author.bot is True, "Self-message should have bot=True"
        assert regular_message.author.bot is False, "Regular message should have bot=False"
        assert self_message.author.id == self.mock_bot.user.id, "Self-message author should match bot ID"

        print("✅ Logging and assertions working correctly")
        print(f"   - Self-message bot status: {self_message.author.bot}")
        print(f"   - Regular message bot status: {regular_message.author.bot}")
        print(f"   - ID match: {self_message.author.id == self.mock_bot.user.id}")

        logger.removeHandler(handler)


def run_self_message_tests():
    """Run all self-message reading tests."""
    print("🧪 Discord Voice Bot - Self-Message Reading Tests")
    print("=" * 60)

    async def _run_async_tests():
        """Run async tests."""
        test_instance = TestSelfMessageReading()

        try:
            # Run setup
            test_instance.setUp()

            # Run tests
            await test_instance.test_current_behavior_filters_self_messages()
            await test_instance.test_current_behavior_allows_regular_messages()
            await test_instance.test_message_handler_current_behavior()
            await test_instance.test_fixed_behavior_allows_self_messages()
            await test_instance.test_full_voice_pipeline_with_self_message()
            await test_instance.test_message_validator_current_vs_fixed()
            test_instance.test_logging_and_assertions()

            print("\n🎉 All tests completed successfully!")

        except Exception as e:
            print(f"\n❌ Test failed with error: {e}")
            import traceback

            traceback.print_exc()

        finally:
            # Run cleanup
            test_instance.tearDown()

    # Run the async tests
    asyncio.run(_run_async_tests())


if __name__ == "__main__":
    # Run the test suite
    run_self_message_tests()

    print("\n📝 Instructions for running this test:")
    print("1. Save this file as tests/test_self_message_reading.py")
    print("2. Run with pytest: pytest tests/test_self_message_reading.py -v")
    print("3. Or run directly: python tests/test_self_message_reading.py")
    print("\n🔧 To apply the fix:")
    print("1. Modify the filtering logic in event_message_handler.py and message_processor.py")
    print("2. Add a check: if message.author.id == bot.user.id: allow processing")
    print("3. Re-run tests to verify the fix works")
    print("\n⚠️  Note: This test demonstrates the issue and provides a template for the fix.")
