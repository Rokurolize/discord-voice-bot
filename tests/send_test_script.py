#!/usr/bin/env python3
"""Comprehensive test script to verify self-message processing and voice reading functionality.

This script will:
1. Connect to Discord using the bot's credentials
2. Send a self-message to trigger the bot's message processing
3. Monitor the message processing through the bot's event system
4. Verify that TTS audio is generated and queued for playback
5. Provide detailed logging and verification of each step
"""

import asyncio
import logging
import sys
import time
from pathlib import Path
from typing import Any

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

import discord
from discord.ext import commands
from loguru import logger

from src.discord_voice_bot.config_manager import ConfigManagerImpl


class TestMonitor:
    """Monitor for tracking message processing and TTS events."""

    def __init__(self):
        self.events: list[dict[str, Any]] = []
        self.message_processed = False
        self.tts_generated = False
        self.audio_queued = False
        self.audio_played = False
        self.errors: list[str] = []

    def log_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Log an event with timestamp."""
        event = {"timestamp": time.time(), "type": event_type, "data": data}
        self.events.append(event)
        logger.info(f"🧪 Test Event: {event_type} - {data}")

    def mark_message_processed(self, message_id: int) -> None:
        """Mark that a message was processed."""
        self.message_processed = True
        self.log_event("message_processed", {"message_id": message_id})

    def mark_tts_generated(self, message_text: str) -> None:
        """Mark that TTS audio was generated."""
        self.tts_generated = True
        self.log_event("tts_generated", {"text": message_text})

    def mark_audio_queued(self, audio_data: dict[str, Any]) -> None:
        """Mark that audio was queued for playback."""
        self.audio_queued = True
        self.log_event("audio_queued", audio_data)

    def mark_audio_played(self) -> None:
        """Mark that audio started playing."""
        self.audio_played = True
        self.log_event("audio_played", {})

    def add_error(self, error: str) -> None:
        """Add an error to the log."""
        self.errors.append(error)
        self.log_event("error", {"error": error})

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of the test results."""
        return {
            "events_count": len(self.events),
            "message_processed": self.message_processed,
            "tts_generated": self.tts_generated,
            "audio_queued": self.audio_queued,
            "audio_played": self.audio_played,
            "errors_count": len(self.errors),
            "errors": self.errors.copy(),
            "events": self.events.copy(),
        }


class SelfMessageTestBot(commands.Bot):
    """Test bot that extends Discord.py Bot with monitoring capabilities."""

    def __init__(self, config_manager: ConfigManagerImpl, monitor: TestMonitor):
        # Initialize with the same config as the main bot
        super().__init__(
            command_prefix=config_manager.get_command_prefix(),
            intents=config_manager.get_intents(),
            help_command=None,
            case_insensitive=True,
        )

        self.config_manager = config_manager
        self.monitor = monitor
        self.test_message_sent = False
        self.bot_user_id = None

    async def setup_hook(self) -> None:
        """Setup hook called after login but before connecting to gateway."""
        logger.info("🧪 Test bot setup_hook called")

        # Store bot user ID for self-message detection
        if self.user:
            self.bot_user_id = self.user.id
            logger.info(f"🧪 Test bot user ID: {self.bot_user_id}")

    async def on_ready(self) -> None:
        """Handle bot ready event."""
        logger.info(f"🧪 Test bot ready! Logged in as {self.user}")
        self.monitor.log_event("bot_ready", {"user": str(self.user), "user_id": self.user.id if self.user else None})

        # Wait a moment for the bot to fully initialize
        await asyncio.sleep(2)

        # Send test self-message
        await self.send_test_message()

    async def on_message(self, message: discord.Message) -> None:
        """Handle message events with monitoring."""
        try:
            logger.debug(f"🧪 Test bot received message: {message.content} from {message.author}")

            # Check if this is our test message
            if message.author.id == self.bot_user_id and "🎤 ボイス読み上げテスト" in message.content:
                self.monitor.log_event("self_message_received", {"message_id": message.id, "content": message.content, "author_id": message.author.id})

            # Process the message through the event handler (same as main bot)
            from src.discord_voice_bot.event_handler import EventHandler

            # Initialize components like the main bot would
            event_handler = EventHandler(self, self.config_manager)
            await event_handler.handle_message(message)

        except Exception as e:
            logger.error(f"🧪 Error in test bot on_message: {e}")
            self.monitor.add_error(f"Message processing error: {e}")

    async def send_test_message(self) -> None:
        """Send a test self-message to trigger processing."""
        try:
            # Find a suitable text channel to send the message
            for guild in self.guilds:
                for channel in guild.text_channels:
                    # Try to send message in the channel
                    try:
                        test_message = "🎤 ボイス読み上げテスト: これは自動テストメッセージです。TTS機能が正常に動作しているか確認してください。"
                        sent_message = await channel.send(test_message)

                        self.test_message_sent = True
                        self.monitor.log_event("test_message_sent", {"channel_id": channel.id, "channel_name": channel.name, "message_id": sent_message.id, "content": test_message})

                        logger.info(f"🧪 Test message sent successfully in {channel.name}")
                        return

                    except discord.Forbidden:
                        logger.debug(f"🧪 Cannot send message in {channel.name}, trying next channel")
                        continue
                    except Exception as e:
                        logger.debug(f"🧪 Error sending message in {channel.name}: {e}")
                        continue

            logger.error("🧪 Could not find a suitable channel to send test message")
            self.monitor.add_error("No suitable channel found for test message")

        except Exception as e:
            logger.error(f"🧪 Error sending test message: {e}")
            self.monitor.add_error(f"Error sending test message: {e}")


async def run_test() -> dict[str, Any]:
    """Run the comprehensive self-message test."""
    print("🚀 Starting Discord Voice Bot Self-Message Test")
    print("=" * 60)

    # Initialize monitor
    monitor = TestMonitor()

    try:
        # Load configuration
        config_manager = ConfigManagerImpl()
        config_manager.validate()

        discord_token = config_manager.get_discord_token()
        if not discord_token:
            raise ValueError("Discord token not found in configuration")

        print(f"✅ Configuration loaded: ENABLE_SELF_MESSAGE_PROCESSING = {config_manager.get_enable_self_message_processing()}")
        print(f"✅ TTS Engine: {config_manager.get_tts_engine()}")
        print(f"✅ Target Voice Channel ID: {config_manager.get_target_voice_channel_id()}")

        # Check if self-message processing is enabled
        if not config_manager.get_enable_self_message_processing():
            print("⚠️  WARNING: ENABLE_SELF_MESSAGE_PROCESSING is disabled!")
            print("   Self-messages will not be processed.")
            print("   Set ENABLE_SELF_MESSAGE_PROCESSING=true in your .env file")
            monitor.add_error("Self-message processing is disabled")
            return monitor.get_summary()

        # Create test bot
        test_bot = SelfMessageTestBot(config_manager, monitor)

        # Add event listeners for monitoring
        @test_bot.event
        async def on_voice_state_update(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState) -> None:
            """Monitor voice state changes."""
            if member.id == test_bot.bot_user_id:
                monitor.log_event(
                    "voice_state_update", {"member_id": member.id, "before_channel": before.channel.id if before.channel else None, "after_channel": after.channel.id if after.channel else None}
                )

        print("🔄 Starting test bot...")
        monitor.log_event("test_started", {"timestamp": time.time()})

        # Start the bot (this will run until interrupted)
        await test_bot.start(discord_token)

    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")
        monitor.log_event("test_interrupted", {"timestamp": time.time()})

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        monitor.add_error(f"Test execution error: {e}")

    finally:
        # Return test results
        summary = monitor.get_summary()
        print("\n📊 Test Results Summary")
        print("=" * 40)
        print(f"Events Recorded: {summary['events_count']}")
        print(f"Message Processed: {'✅' if summary['message_processed'] else '❌'}")
        print(f"TTS Generated: {'✅' if summary['tts_generated'] else '❌'}")
        print(f"Audio Queued: {'✅' if summary['audio_queued'] else '❌'}")
        print(f"Audio Played: {'✅' if summary['audio_played'] else '❌'}")
        print(f"Errors: {summary['errors_count']}")

        if summary["errors"]:
            print("\n❌ Errors encountered:")
            for i, error in enumerate(summary["errors"], 1):
                print(f"  {i}. {error}")

        if summary["events"]:
            print("\n📋 Event Timeline:")
            for event in summary["events"]:
                timestamp = time.strftime("%H:%M:%S", time.localtime(event["timestamp"]))
                print(f"  {timestamp}: {event['type']}")

        return summary


def main():
    """Main entry point."""
    try:
        # Configure logging
        logging.getLogger("discord").setLevel(logging.INFO)
        logger.remove()  # Remove default handler
        logger.add(sys.stdout, level="DEBUG", format="<green>{time:HH:mm:ss}</green> <level>{message}</level>")

        # Run the test
        result = asyncio.run(run_test())

        # Exit with appropriate code
        if result["errors_count"] > 0:
            print("\n❌ Test completed with errors")
            sys.exit(1)
        else:
            print("\n✅ Test completed successfully")
            sys.exit(0)

    except Exception as e:
        print(f"\n💥 Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
