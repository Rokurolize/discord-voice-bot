"""Main Discord bot implementation for Voice TTS Bot."""

import asyncio
from typing import Any

import discord
from discord.ext import commands, tasks
from loguru import logger

from .config import config
from .message_processor import message_processor
from .tts_engine import tts_engine
from .voice_handler import VoiceHandler


class DiscordVoiceTTSBot(commands.Bot):
    """Discord Voice TTS Bot with Zundamon voice."""

    def __init__(self) -> None:
        """Initialize the Discord bot."""
        # Initialize bot with required intents
        super().__init__(
            command_prefix=config.command_prefix,
            intents=config.get_intents(),
            help_command=None,  # Disable default help command
            case_insensitive=True,
        )

        # Initialize components
        self.voice_handler: VoiceHandler | None = None
        self.startup_complete = False
        self.stats: dict[str, int | float | None] = {
            "messages_processed": 0,
            "tts_messages_played": 0,
            "connection_errors": 0,
            "uptime_start": None,
        }

        # Set up event handlers
        self._setup_events()
        self._setup_commands()

        logger.info("Discord Voice TTS Bot initialized")

    def _setup_events(self) -> None:
        """Set up Discord event handlers."""

        @self.event
        async def on_ready() -> None:
            """Handle bot ready event."""
            await self._on_ready()

        @self.event
        async def on_message(message: Any) -> None:
            """Handle message events."""
            await self._on_message(message)

        @self.event
        async def on_voice_state_update(member: Any, before: Any, after: Any) -> None:
            """Handle voice state update events."""
            await self._on_voice_state_update(member, before, after)

        @self.event
        async def on_disconnect() -> None:
            """Handle bot disconnect."""
            await self._on_disconnect()

        @self.event
        async def on_resumed() -> None:
            """Handle bot resume."""
            await self._on_resumed()

        @self.event
        async def on_error(event: str, *args: Any, **kwargs: Any) -> None:
            """Handle general errors."""
            await self._on_error(event, *args, **kwargs)

    def _setup_commands(self) -> None:
        """Set up bot commands."""

        @self.command(name="status")
        async def status_command(ctx: Any) -> None:
            """Show bot status and statistics."""
            await self._status_command(ctx)

        @self.command(name="skip")
        async def skip_command(ctx: Any) -> None:
            """Skip current TTS playback."""
            await self._skip_command(ctx)

        @self.command(name="clear")
        async def clear_command(ctx: Any) -> None:
            """Clear TTS queue."""
            await self._clear_command(ctx)

        @self.command(name="speakers")
        async def speakers_command(ctx: Any) -> None:
            """List available TTS speakers."""
            await self._speakers_command(ctx)

        @self.command(name="test")
        async def test_command(ctx: Any, *, text: str = "テストメッセージです") -> None:
            """Test TTS with custom text."""
            await self._test_command(ctx, text)

        @self.command(name="voice")
        async def voice_command(ctx: Any, *, speaker: str | None = None) -> None:
            """Set or show personal voice preference."""
            await self._voice_command(ctx, speaker)

        @self.command(name="voices")
        async def voices_command(ctx: Any) -> None:
            """List all available voices."""
            await self._voices_command(ctx)

    async def _on_ready(self) -> None:
        """Handle bot ready event."""
        if self.startup_complete:
            logger.info("Bot reconnected and ready")
            return

        if self.user:
            logger.info(f"Bot logged in as {self.user} (ID: {self.user.id})")
        else:
            logger.info("Bot logged in (user info not available)")

        # Set bot presence
        activity = discord.Activity(type=discord.ActivityType.listening, name="声チャットのメッセージ 📢")
        await self.change_presence(status=discord.Status.online, activity=activity)

        # Initialize voice handler
        self.voice_handler = VoiceHandler(self)

        # Update voice handler reference
        # (removed global reference as it's not needed)

        # Start voice handler
        await self.voice_handler.start()

        # Start TTS engine
        await tts_engine.start()

        # Connect to target voice channel
        success = await self.voice_handler.connect_to_channel(config.target_voice_channel_id)
        if success:
            logger.info("Successfully connected to target voice channel")
        else:
            logger.error("Failed to connect to target voice channel")
            current_errors = self.stats.get("connection_errors", 0)
            if isinstance(current_errors, int):
                self.stats["connection_errors"] = current_errors + 1

        # Start monitoring task
        self.monitor_task.start()

        # Mark startup complete
        self.startup_complete = True
        self.stats["uptime_start"] = asyncio.get_event_loop().time()

        logger.info("Bot startup complete and ready for TTS!")

    async def _on_message(self, message: discord.Message) -> None:
        """Handle message events."""
        # Log all messages for debugging
        logger.debug(
            f"Received message from {message.author.name} (ID: {message.id}) in channel {message.channel.id}: {message.content[:50]}"
        )

        # Process commands first
        await self.process_commands(message)

        # Skip if not in target channel or shouldn't process
        processed_message = await message_processor.process_message(message)
        if not processed_message:
            logger.debug(f"Message {message.id} from {message.author.name} was filtered out")
            return

        # Add to TTS queue
        if self.voice_handler:
            await self.voice_handler.add_to_queue(processed_message)
            self.stats["messages_processed"] = (self.stats.get("messages_processed", 0) or 0) + 1
            logger.debug(f"Queued TTS message from {message.author.display_name}")
        else:
            logger.warning("Voice handler not initialized, cannot queue TTS message")

    async def _on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> None:
        """Handle voice state update events."""
        # Auto-reconnect if bot was disconnected
        if member == self.user and before.channel and not after.channel:
            logger.warning("Bot was disconnected from voice channel")
            if self.voice_handler:
                await asyncio.sleep(1)
                await self.voice_handler.connect_to_channel(config.target_voice_channel_id)

    async def _on_disconnect(self) -> None:
        """Handle bot disconnect."""
        logger.warning("Bot disconnected from Discord")
        self.startup_complete = False

    async def _on_resumed(self) -> None:
        """Handle bot resume."""
        logger.info("Bot connection resumed")

    async def _on_error(self, event: str, *args: Any, **kwargs: Any) -> None:
        """Handle general errors."""
        logger.error(f"Discord event error in {event}: {args} {kwargs}")

    @tasks.loop(minutes=5)
    async def monitor_task(self) -> None:
        """Monitor bot health and perform periodic tasks."""
        try:
            # Check TTS engine health
            if not await tts_engine.health_check():
                logger.warning("TTS engine health check failed")

            # Check voice connection
            if self.voice_handler:
                status = self.voice_handler.get_status()
                if not status["connected"]:
                    logger.warning("Voice connection lost, attempting reconnect")
                    await self.voice_handler.connect_to_channel(config.target_voice_channel_id)

            # Log stats periodically
            if config.debug:
                status = self.get_status()
                logger.info(f"Bot stats: {status}")

        except Exception as e:
            logger.error(f"Error in monitoring task: {e!s}")

    async def _status_command(self, ctx: commands.Context) -> None:
        """Show bot status and statistics."""
        status = self.get_status()

        embed = discord.Embed(
            title="🤖 Discord Voice TTS Bot Status",
            color=(discord.Color.green() if status["voice_connected"] else discord.Color.red()),
            description="ずんだもんボイス読み上げBot",
        )

        # Connection status
        embed.add_field(
            name="🔗 接続状態",
            value=f"Voice: {'✅ 接続中' if status['voice_connected'] else '❌ 未接続'}\n"
            f"Channel: {status['voice_channel_name'] or 'なし'}",
            inline=True,
        )

        # TTS status
        embed.add_field(
            name="🎤 TTS状態",
            value=f"Engine: {config.tts_engine.upper()}\n"
            f"Speaker: {config.tts_speaker}\n"
            f"Playing: {'✅' if status['is_playing'] else '❌'}",
            inline=True,
        )

        # Queue status
        embed.add_field(
            name="📋 キュー状態",
            value=f"Ready: {status.get('audio_queue_size', 0)} chunks\n"
            f"Synthesizing: {status.get('synthesis_queue_size', 0)} chunks\n"
            f"Total: {status.get('total_queue_size', 0)}/{status['max_queue_size']}\n"
            f"Processed: {status['messages_processed']}",
            inline=True,
        )

        # Bot info
        uptime = status.get("uptime_seconds", 0)
        hours, remainder = divmod(int(uptime), 3600)
        minutes, seconds = divmod(remainder, 60)

        embed.add_field(
            name="ℹ️ Bot情報",
            value=f"Uptime: {hours:02d}:{minutes:02d}:{seconds:02d}\n"
            f"Latency: {self.latency * 1000:.0f}ms\n"
            f"Errors: {status['connection_errors']}",
            inline=True,
        )

        await ctx.send(embed=embed)

    async def _skip_command(self, ctx: commands.Context) -> None:
        """Skip current TTS playback."""
        if not self.voice_handler:
            await ctx.send("❌ Voice handler not initialized")
            return

        if await self.voice_handler.skip_current():
            await ctx.send("⏭️ Current TTS skipped")
        else:
            await ctx.send("ℹ️ No TTS currently playing")

    async def _clear_command(self, ctx: commands.Context) -> None:
        """Clear TTS queue."""
        if not self.voice_handler:
            await ctx.send("❌ Voice handler not initialized")
            return

        cleared_count = await self.voice_handler.clear_all()
        await ctx.send(f"🗑️ Cleared {cleared_count} items from TTS queue")

    async def _speakers_command(self, ctx: commands.Context) -> None:
        """List available TTS speakers."""
        speakers = await tts_engine.get_available_speakers()

        embed = discord.Embed(
            title=f"🎭 Available Speakers ({config.tts_engine.upper()})",
            color=discord.Color.blue(),
            description=f"Current: **{config.tts_speaker}** (ID: {config.speaker_id})",
        )

        speaker_list = []
        for name, speaker_id in speakers.items():
            marker = "🔹" if name == config.tts_speaker else "▫️"
            speaker_list.append(f"{marker} `{name}` (ID: {speaker_id})")

        # Split into chunks if too long
        chunk_size = 10
        chunks = [speaker_list[i : i + chunk_size] for i in range(0, len(speaker_list), chunk_size)]

        for i, chunk in enumerate(chunks):
            field_name = "Speakers" if i == 0 else f"Speakers (cont. {i+1})"
            embed.add_field(name=field_name, value="\n".join(chunk), inline=False)

        await ctx.send(embed=embed)

    async def _test_command(self, ctx: commands.Context, text: str) -> None:
        """Test TTS with custom text."""
        if not self.voice_handler:
            await ctx.send("❌ Voice handler not initialized")
            return

        status = self.voice_handler.get_status()
        if not status["connected"]:
            await ctx.send("❌ Not connected to voice channel")
            return

        # Process and queue the test message
        processed_text = message_processor.process_message_content(text, ctx.author.display_name)
        chunks = message_processor.chunk_message(processed_text)

        processed_message = {
            "text": processed_text,
            "user_id": ctx.author.id,
            "username": ctx.author.display_name,
            "chunks": chunks,
            "group_id": f"test_{ctx.message.id}",
        }

        await self.voice_handler.add_to_queue(processed_message)
        await ctx.send(f"🎤 Test TTS queued: `{processed_text[:50]}...`")
        self.stats["tts_messages_played"] = (self.stats.get("tts_messages_played", 0) or 0) + 1

    async def _voice_command(self, ctx: commands.Context, speaker: str | None = None) -> None:
        """Set or show personal voice preference."""
        from .user_settings import user_settings

        user_id = str(ctx.author.id)

        # If no speaker specified, show current setting
        if speaker is None:
            current_settings = user_settings.get_user_settings(user_id)
            if current_settings:
                embed = discord.Embed(
                    title="🎭 Your Voice Settings",
                    color=discord.Color.blue(),
                    description=f"Current voice: **{current_settings['speaker_name']}** (ID: {current_settings['speaker_id']})",
                )
            else:
                embed = discord.Embed(
                    title="🎭 Your Voice Settings",
                    color=discord.Color.greyple(),
                    description="No custom voice set. Using default voice.",
                )
            embed.add_field(
                name="Commands",
                value="`!tts voice <name>` - Set voice\n`!tts voice reset` - Reset to default\n`!tts voices` - List available",
                inline=False,
            )
            await ctx.send(embed=embed)
            return

        # Handle reset
        if speaker.lower() == "reset":
            if user_settings.remove_user_speaker(user_id):
                await ctx.send("✅ Voice preference reset to default")
            else:
                await ctx.send("ℹ️ You don't have a custom voice set")
            return

        # Get available speakers
        speakers = await tts_engine.get_available_speakers()

        # Find matching speaker (case-insensitive)
        speaker_lower = speaker.lower()
        matched_speaker = None
        matched_id = None

        for name, speaker_id in speakers.items():
            if name.lower() == speaker_lower or str(speaker_id) == speaker:
                matched_speaker = name
                matched_id = speaker_id
                break

        if matched_speaker and matched_id is not None:
            # Pass current engine to ensure proper mapping
            if user_settings.set_user_speaker(user_id, matched_id, matched_speaker, config.tts_engine):
                await ctx.send(f"✅ Voice set to **{matched_speaker}** (ID: {matched_id}) on {config.tts_engine.upper()}")
                # Test the new voice
                test_text = f"{matched_speaker}の声です"
                if self.voice_handler:
                    chunks = message_processor.chunk_message(test_text)
                    processed_message = {
                        "text": test_text,
                        "user_id": ctx.author.id,
                        "username": ctx.author.display_name,
                        "chunks": chunks,
                        "group_id": f"voice_test_{ctx.message.id}",
                    }
                    await self.voice_handler.add_to_queue(processed_message)
            else:
                await ctx.send("❌ Failed to save voice preference")
        else:
            await ctx.send(f"❌ Voice '{speaker}' not found. Use `!tts voices` to see available options.")

    async def _voices_command(self, ctx: commands.Context) -> None:
        """List all available voices with detailed information."""
        from .user_settings import user_settings

        # Get available speakers from TTS engine
        speakers = await tts_engine.get_available_speakers()

        # Get user's current setting
        user_id = str(ctx.author.id)
        current_settings = user_settings.get_user_settings(user_id)
        current_speaker = current_settings["speaker_name"] if current_settings else None

        embed = discord.Embed(
            title=f"🎭 Available Voices ({config.tts_engine.upper()})",
            color=discord.Color.blue(),
            description="Use `!tts voice <name>` to set your personal voice",
        )

        # Group speakers by base name
        speaker_groups: dict[str, list[tuple[str, int]]] = {}
        for name, speaker_id in speakers.items():
            # Extract base name (e.g., "zunda" from "zunda_normal")
            base_name = name.split("_")[0] if "_" in name else name
            if base_name not in speaker_groups:
                speaker_groups[base_name] = []
            speaker_groups[base_name].append((name, speaker_id))

        # Add fields for each speaker group
        for base_name, variants in speaker_groups.items():
            field_lines = []
            for name, speaker_id in variants:
                marker = "🔹" if name == current_speaker else "▫️"
                field_lines.append(f"{marker} `{name}` ({speaker_id})")

            embed.add_field(name=base_name.title(), value="\n".join(field_lines), inline=True)

        # Add current setting info
        if current_speaker:
            embed.set_footer(text=f"Your current voice: {current_speaker}")
        else:
            embed.set_footer(text="You're using the default voice")

        await ctx.send(embed=embed)

    def get_status(self) -> dict[str, Any]:
        """Get current bot status."""
        voice_status = self.voice_handler.get_status() if self.voice_handler else {}

        uptime = 0.0
        uptime_start = self.stats.get("uptime_start")
        if uptime_start and isinstance(uptime_start, (int, float)):
            uptime = asyncio.get_event_loop().time() - uptime_start

        return {
            **voice_status,
            "messages_processed": self.stats["messages_processed"],
            "tts_messages_played": self.stats["tts_messages_played"],
            "connection_errors": self.stats["connection_errors"],
            "uptime_seconds": uptime,
            "bot_latency_ms": self.latency * 1000,
            "tts_engine": config.tts_engine,
            "tts_speaker": config.tts_speaker,
        }

    async def shutdown(self) -> None:
        """Graceful shutdown of the bot."""
        logger.info("Starting bot shutdown...")

        # Stop monitoring task
        if hasattr(self, "monitor_task"):
            self.monitor_task.cancel()

        # Stop voice handler
        if self.voice_handler:
            await self.voice_handler.cleanup()

        # Close TTS engine
        await tts_engine.close()

        # Close bot connection
        await self.close()

        logger.info("Bot shutdown complete")


# Function to create and run the bot
async def run_bot() -> None:
    """Create and run the Discord bot."""
    bot = DiscordVoiceTTSBot()

    try:
        # Validate configuration
        config.validate()

        # Start the bot
        await bot.start(config.discord_token)

    except discord.LoginFailure:
        logger.error("Invalid Discord token provided")

    except Exception as e:
        logger.error(f"Failed to start bot: {type(e).__name__} - {e!s}")

    finally:
        if not bot.is_closed():
            await bot.shutdown()
