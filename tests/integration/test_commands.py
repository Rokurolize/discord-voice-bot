#!/usr/bin/env python3
"""Test bot commands directly through the bot instance."""

import asyncio
from unittest.mock import AsyncMock, Mock

from src.bot import DiscordVoiceTTSBot
from src.config import config


class MockContext:
    """Mock Discord context for command testing."""

    def __init__(self, command_name=""):
        self.command_name = command_name
        self.messages_sent = []
        self.author = Mock()
        self.author.display_name = "TestUser"

    async def send(self, message=None, embed=None):
        """Mock send method to capture responses."""
        if embed:
            self.messages_sent.append(f"[EMBED] {embed.title}: {embed.description}")
            for field in embed.fields:
                self.messages_sent.append(f"  {field.name}: {field.value}")
        else:
            self.messages_sent.append(str(message))
        print(f"📤 Bot Response: {self.messages_sent[-1]}")


async def test_bot_commands():
    """Test all bot commands."""
    print("🧪 Testing Bot Commands...")

    # Create bot instance (without starting Discord connection)
    bot = DiscordVoiceTTSBot()

    # Mock the latency property by overriding the parent class property
    type(bot).latency = property(lambda self: getattr(self, "_latency", 0.025))

    # Mock voice handler for testing
    mock_voice_handler = Mock()
    mock_voice_handler.get_queue_status = Mock(
        return_value={
            "queue_size": 3,
            "max_queue_size": 10,
            "is_playing": True,
            "is_connected": True,
            "voice_channel_id": config.target_voice_channel_id,
            "voice_channel_name": "ずんだもん読み上げ専用",
        }
    )
    mock_voice_handler.skip_current = AsyncMock(return_value=True)
    mock_voice_handler.clear_queue = Mock(return_value=5)
    mock_voice_handler.add_to_queue = AsyncMock(return_value=True)
    mock_voice_handler.is_connected = True

    bot.voice_handler = mock_voice_handler
    bot.stats = {
        "messages_processed": 42,
        "tts_messages_played": 38,
        "connection_errors": 1,
        "uptime_start": 1000.0,
    }
    # Mock latency property
    bot._latency = 0.025

    # Test commands
    commands_to_test = [
        ("status", "Status Command"),
        ("skip", "Skip Command"),
        ("clear", "Clear Queue Command"),
        ("speakers", "Speakers List Command"),
        ("test", "TTS Test Command"),
    ]

    for cmd_name, description in commands_to_test:
        print(f"\n--- Testing {description} ---")
        ctx = MockContext(cmd_name)

        try:
            if cmd_name == "status":
                await bot._status_command(ctx)
            elif cmd_name == "skip":
                await bot._skip_command(ctx)
            elif cmd_name == "clear":
                await bot._clear_command(ctx)
            elif cmd_name == "speakers":
                await bot._speakers_command(ctx)
            elif cmd_name == "test":
                await bot._test_command(ctx, "テストメッセージなのだ")

            print(f"✅ {description} executed successfully")

        except Exception as e:
            print(f"❌ {description} failed: {e}")

    # Test get_status method
    print("\n--- Testing Status Data ---")
    status = bot.get_status()
    print("📊 Bot Status Data:")
    for key, value in status.items():
        print(f"  {key}: {value}")

    print("\n✅ Bot commands testing completed!")


if __name__ == "__main__":
    asyncio.run(test_bot_commands())
