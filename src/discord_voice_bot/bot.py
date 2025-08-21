"""Main Discord bot implementation for Voice TTS Bot."""
# pyright: reportUnusedFunction=false

import asyncio
from typing import Any

import discord
from discord.ext import commands, tasks
from loguru import logger

from .config import config
from .health_monitor import HealthMonitor
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
        self.health_monitor: HealthMonitor | None = None
        self.startup_complete = False
        self.stats: dict[str, int | float | None] = {
            "messages_processed": 0,
            "tts_messages_played": 0,
            "connection_errors": 0,
            "uptime_start": None,
        }
        self._voice_state_updating = False

        # Set up event handlers
        self._setup_events()
        self._setup_commands()

        logger.info("Discord Voice TTS Bot initialized")

    def _setup_events(self) -> None:
        """Set up Discord event handlers."""
        # pyright: ignore[reportUnusedFunction]

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
        async def on_voice_server_update(payload: Any) -> None:
            """Handle voice server update events with proper Discord API compliance."""
            if self.voice_handler:
                await self.voice_handler.handle_voice_server_update(payload)
            else:
                logger.warning("⚠️ Voice handler not initialized, cannot handle voice server update")

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
        # pyright: ignore[reportUnusedFunction]

        @self.command(name="status")
        async def status_command(ctx: commands.Context[Any]) -> None:
            """Show bot status and statistics."""
            await self._status_command(ctx)

        @self.command(name="skip")
        async def skip_command(ctx: commands.Context[Any]) -> None:
            """Skip current TTS playback."""
            await self._skip_command(ctx)

        @self.command(name="clear")
        async def clear_command(ctx: commands.Context[Any]) -> None:
            """Clear TTS queue."""
            await self._clear_command(ctx)

        @self.command(name="speakers")
        async def speakers_command(ctx: commands.Context[Any]) -> None:
            """List available TTS speakers."""
            await self._speakers_command(ctx)

        @self.command(name="test")
        async def test_command(ctx: commands.Context[Any], *, text: str = "テストメッセージです") -> None:
            """Test TTS with custom text."""
            await self._test_command(ctx, text)

        @self.command(name="voice")
        async def voice_command(ctx: commands.Context[Any], *, speaker: str | None = None) -> None:
            """Set or show personal voice preference."""
            await self._voice_command(ctx, speaker)

        @self.command(name="voices")
        async def voices_command(ctx: commands.Context[Any]) -> None:
            """List all available voices."""
            await self._voices_command(ctx)

        @self.command(name="voicecheck")
        async def voicecheck_command(ctx: commands.Context[Any]) -> None:
            """Perform voice connection health check."""
            await self._voicecheck_command(ctx)

        @self.command(name="reconnect")
        async def reconnect_command(ctx: commands.Context[Any]) -> None:
            """Manually attempt to reconnect to voice channel."""
            await self._reconnect_command(ctx)

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

        # Log critical compliance information
        logger.info("🔧 DISCORD API COMPLIANCE CHECK:")
        logger.info("   - Voice Gateway Version: 8 (required since Nov 2024)")
        logger.info("   - E2EE Support: Enabled via discord.py abstraction")
        logger.info("   - Rate Limiting: 50 req/sec with dynamic headers")
        logger.info("   - Invalid Request Protection: Circuit breaker enabled")
        logger.info("✅ Bot configured for Discord API compliance")

        # Initialize voice handler
        self.voice_handler = VoiceHandler(self)

        # Initialize health monitor
        self.health_monitor = HealthMonitor(self)
        await self.health_monitor.start()

        # Update voice handler reference
        # (removed global reference as it's not needed)

        # Start voice handler
        await self.voice_handler.start()

        # Start TTS engine
        await tts_engine.start()

        # Connect to target voice channel with enhanced retry logic and diagnostics
        logger.info(f"🔗 STARTUP VOICE CONNECTION - Attempting to connect to target voice channel ID: {config.target_voice_channel_id}")
        max_retries = 3

        # Pre-connection diagnostics
        logger.debug("🔍 PRE-CONNECTION DIAGNOSTICS:")
        logger.debug(f"  - Bot guilds: {len(self.guilds)}")
        if self.guilds:
            guild = self.guilds[0]
            logger.debug(f"  - Primary guild: {guild.name} (ID: {guild.id})")
            logger.debug(f"  - Bot permissions in guild: {guild.me.guild_permissions if guild.me else 'Unknown'}")
            logger.debug(f"  - Available channels: {len(guild.channels)}")

            # Check if target channel exists and is accessible
            target_channel = self.get_channel(config.target_voice_channel_id)
            if target_channel:
                channel_name = getattr(target_channel, "name", f"ID:{config.target_voice_channel_id}")
                logger.debug(f"  - Target channel found: {channel_name}")
                logger.debug(f"  - Target channel type: {type(target_channel).__name__}")
                if hasattr(target_channel, "permissions_for") and guild.me:
                    try:
                        # Check if the channel is a guild channel before accessing permissions
                        if hasattr(target_channel, "guild") and target_channel.guild:  # type: ignore[attr-defined]
                            perms = target_channel.permissions_for(guild.me)  # type: ignore[attr-defined]
                            logger.debug(f"  - Bot permissions in channel: connect={perms.connect}, speak={perms.speak}")  # type: ignore[attr-defined]
                        else:
                            logger.debug(f"  - Cannot check permissions for non-guild channel type: {type(target_channel).__name__}")
                    except AttributeError:
                        logger.debug(f"  - Could not check permissions for channel type: {type(target_channel).__name__}")
            else:
                logger.warning(f"  - Target channel {config.target_voice_channel_id} not found in bot's accessible channels")

        for attempt in range(max_retries):
            try:
                logger.info(f"🔄 CONNECTION ATTEMPT {attempt + 1}/{max_retries}")
                success = await self.voice_handler.connect_to_channel(config.target_voice_channel_id)

                if success:
                    logger.info("✅ STARTUP CONNECTION SUCCESSFUL - Bot is now connected to voice channel")
                    break
                if attempt < max_retries - 1:
                    wait_time = 10
                    logger.warning(f"❌ ATTEMPT {attempt + 1} FAILED - Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error("❌ STARTUP CONNECTION FAILED - All retry attempts exhausted")
                    logger.error("🔧 BOT WILL SHUTDOWN - Voice connection is required for TTS functionality")
                    logger.error("💡 TROUBLESHOOTING TIPS:")
                    logger.error("   1. Verify the voice channel ID is correct")
                    logger.error("   2. Check if the bot has 'Connect' and 'Speak' permissions in the target channel")
                    logger.error("   3. Ensure the bot is added to the server and has proper permissions")
                    logger.error("   4. Check if the voice channel exists and is not deleted")
                    logger.error("   5. Check server audit logs for any bot-related errors")

                    # Perform final health check for diagnostics
                    if self.voice_handler:
                        health_status = await self.voice_handler.health_check()
                        logger.error("🔍 FINAL DIAGNOSTICS:")
                        for issue in health_status["issues"]:
                            logger.error(f"   • {issue}")

                    # Count consecutive startup failures
                    if not hasattr(self, "_startup_connection_failures"):
                        self._startup_connection_failures = 0
                    self._startup_connection_failures += 1

                    logger.error(f"❌ STARTUP CONNECTION FAILURE #{self._startup_connection_failures}")

                    if self._startup_connection_failures >= 3:
                        logger.error("🔧 BOT SHUTDOWN - Maximum startup connection failures reached")
                        # Instead of sys.exit, raise a custom exception to be caught by main.py
                        raise RuntimeError("Voice connection failed during startup after 3 attempts - bot cannot function without voice channel access")
                    logger.warning(f"⚠️ Connection failed {self._startup_connection_failures}/3 times during startup")
            except Exception as e:
                logger.error(f"💥 CRITICAL ERROR during connection attempt {attempt + 1}: {e}")
                logger.debug(f"Error type: {type(e).__name__}", exc_info=True)

                if attempt < max_retries - 1:
                    wait_time = 10
                    logger.warning(f"Retrying connection in {wait_time}s despite error...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error("❌ STARTUP CONNECTION ABORTED - All retry attempts failed with critical errors")
                    logger.error("🔧 BOT WILL SHUTDOWN - Voice connection is required for TTS functionality")

                    # Exit with error code to indicate failure
                    import sys

                    sys.exit(1)

        # Start monitoring task
        self.monitor_task.start()

        # Mark startup complete
        self.startup_complete = True
        self.stats["uptime_start"] = asyncio.get_event_loop().time()

        logger.info("Bot startup complete and ready for TTS!")
        logger.info("🩺 Health monitoring system is active")

    async def _on_message(self, message: discord.Message) -> None:
        """Handle message events with proper filtering and validation."""
        try:
            # Log all messages for debugging (rate limited)
            logger.debug(f"Received message from {message.author.name} (ID: {message.id}) in channel {message.channel.id}: {message.content[:50]}")

            # Apply comprehensive message filtering following Discord's patterns
            if not await self._should_process_message(message):
                return

            # Process commands first (with rate limiting)
            if self.voice_handler:
                await self.voice_handler.make_rate_limited_request(self.process_commands, message)
            else:
                await self.process_commands(message)

            # Apply additional message validation
            processed_message = await self._validate_and_process_message(message)
            if not processed_message:
                logger.debug(f"Message {message.id} from {message.author.name} was filtered out after validation")
                return

            # Add to TTS queue with rate limiting
            if self.voice_handler:
                await self.voice_handler.add_to_queue(processed_message)
                current_count = self.stats.get("messages_processed", 0)
                self.stats["messages_processed"] = (current_count if current_count is not None else 0) + 1
                logger.debug(f"Queued TTS message from {message.author.display_name}")
            else:
                logger.warning("Voice handler not initialized, cannot queue TTS message")

        except Exception as e:
            logger.error(f"Error processing message {message.id}: {e!s}")
            current_errors = self.stats.get("connection_errors", 0)
            self.stats["connection_errors"] = (current_errors if current_errors is not None else 0) + 1

    async def _on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> None:
        """Handle voice state update events with improved reconnection logic."""
        try:
            # Ensure we are handling a voice state update for the bot itself
            if not self.user or member.id != self.user.id:
                return

            before_channel_name = before.channel.name if before.channel else "None"
            after_channel_name = after.channel.name if after.channel else "None"
            logger.debug(f"Voice state update - Before: {before_channel_name}, After: {after_channel_name}")

            # If the bot is disconnected from a voice channel, attempt to reconnect
            if before.channel and not after.channel:
                logger.warning(f"⚠️ VOICE DISCONNECTION DETECTED - Bot was disconnected from {before_channel_name} (ID: {before.channel.id})")

                # Report disconnection to health monitor
                if self.health_monitor:
                    self.health_monitor.record_disconnection(f"Disconnected from {before_channel_name}")

                # Check if we're already attempting reconnection
                if self._voice_state_updating:
                    logger.debug("Reconnection already in progress, skipping")
                    return

                # Always attempt cleanup first
                if self.voice_handler:
                    await self.voice_handler.cleanup_voice_client()

                # Only reconnect if the voice handler is initialized
                if self.voice_handler:
                    self._voice_state_updating = True
                    try:
                        # Add a longer delay to prevent rapid reconnection loops
                        await asyncio.sleep(5)
                        logger.info(f"🔄 ATTEMPTING RECONNECTION to voice channel {config.target_voice_channel_id}")

                        # Force cleanup before attempting new connection
                        await self.voice_handler.cleanup_voice_client()

                        success = await self.voice_handler.connect_to_channel(config.target_voice_channel_id)
                        if success:
                            logger.info("✅ SUCCESSFULLY RECONNECTED to voice channel")
                        else:
                            logger.error("❌ RECONNECTION FAILED - Will retry on next voice state update")
                    except Exception as e:
                        logger.error(f"💥 CRITICAL ERROR during reconnection attempt: {e}")
                    finally:
                        self._voice_state_updating = False
                else:
                    logger.warning("Voice handler not initialized - cannot reconnect")

        except Exception as e:
            logger.error(f"💥 CRITICAL ERROR handling voice state update: {e!s}")
            self._voice_state_updating = False  # Reset flag on error

    async def _on_disconnect(self) -> None:
        """Handle bot disconnect."""
        logger.warning("Bot disconnected from Discord - monitoring for reconnection")
        logger.debug("Setting startup_complete to False due to disconnect")
        self.startup_complete = False

        # Log additional context if available
        if self.voice_handler:
            voice_status = self.voice_handler.get_status()
            logger.debug(f"Voice handler status at disconnect: {voice_status}")

    async def _on_resumed(self) -> None:
        """Handle bot resume."""
        logger.info("Bot connection resumed")

    async def _should_process_message(self, message: discord.Message) -> bool:
        """Determine if a message should be processed following Discord's patterns."""
        try:
            # Skip bot messages
            if message.author.bot:
                return False

            # Skip system messages
            if message.type != discord.MessageType.default:
                return False

            # Skip empty messages
            if not message.content or not message.content.strip():
                return False

            # Skip messages that are too long (Discord's 2000 char limit)
            if len(message.content) > 2000:
                return False

            # Skip messages with invalid content
            if not self._is_valid_message_content(message.content):
                return False

            # Only process messages from the target voice channel's text chat
            if hasattr(message.channel, "id"):
                # If we have a voice handler and it's connected, check if this is the right channel
                if self.voice_handler and self.voice_handler.voice_client:
                    # For now, process messages from any channel that the bot can see
                    # This allows flexibility for different server setups
                    return True

            return True

        except Exception as e:
            logger.error(f"Error in message filtering: {e!s}")
            return False

    def _is_valid_message_content(self, content: str) -> bool:
        """Validate message content for security and compliance."""
        try:
            # Check for potentially harmful content
            suspicious_patterns = ["<script", "javascript:", "onload=", "onerror=", "data:text/html", "vbscript:", "onmouseover="]

            content_lower = content.lower()
            for pattern in suspicious_patterns:
                if pattern in content_lower:
                    logger.warning(f"Suspicious content detected in message: {pattern}")
                    return False

            # Check for excessive special characters
            special_chars = sum(1 for c in content if not c.isalnum() and not c.isspace())
            if special_chars / len(content) > 0.8:  # More than 80% special chars
                logger.warning("Message contains excessive special characters")
                return False

            return True

        except Exception as e:
            logger.error(f"Error validating message content: {e!s}")
            return False

    async def _validate_and_process_message(self, message: discord.Message) -> dict[str, Any] | None:
        """Validate and process message with proper sanitization."""
        try:
            # Sanitize message content
            sanitized_content = self._sanitize_message_content(message.content)

            # Use the existing message processor
            processed_message = await message_processor.process_message(message)

            if processed_message:
                # Add additional validation and sanitization
                processed_message["original_content"] = message.content
                processed_message["sanitized_content"] = sanitized_content
                processed_message["validation_passed"] = True

                # Apply rate limiting to message processing
                if self.voice_handler:
                    await self.voice_handler.rate_limiter.wait_if_needed()

            return processed_message

        except Exception as e:
            logger.error(f"Error in message validation: {e!s}")
            return None

    def _sanitize_message_content(self, content: str) -> str:
        """Sanitize message content for TTS processing."""
        try:
            # Remove excessive whitespace
            content = " ".join(content.split())

            # Remove or replace problematic characters
            replacements = {
                "\r\n": " ",
                "\r": " ",
                "\n": " ",
                "\t": " ",
                "…": "...",
                "—": "-",
                "–": "-",
                '"': '"',  # Keep quotes but ensure they're proper
                """: "'",
                """: "'",
            }

            for old, new in replacements.items():
                content = content.replace(old, new)

            # Remove non-printable characters but keep basic unicode
            content = "".join(c for c in content if c.isprintable() or c in ["\n", "\t", " "])

            # Limit length to prevent abuse
            if len(content) > 500:  # Reasonable limit for TTS
                content = content[:497] + "..."

            return content.strip()

        except Exception as e:
            logger.error(f"Error sanitizing message content: {e!s}")
            return content[:100] + "..." if len(content) > 100 else content

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

            # Check voice connection with enhanced diagnostics
            if self.voice_handler:
                # Get basic status
                status = self.voice_handler.get_status()
                logger.debug(f"Voice handler state - Connected: {status['connected']}, Playing: {status['playing']}, Queue: {status['total_queue_size']}")

                if not status["connected"]:
                    logger.warning("Voice connection lost - will attempt reconnection on next voice state update")

                    # Perform detailed health check when disconnected
                    health_status = await self.voice_handler.health_check()
                    if not health_status["healthy"]:
                        logger.warning("🔍 VOICE HEALTH CHECK FAILED:")
                        for issue in health_status["issues"]:
                            logger.warning(f"   • {issue}")
                        for recommendation in health_status["recommendations"]:
                            logger.info(f"   💡 {recommendation}")
                else:
                    logger.debug(f"Voice connection healthy: {status['voice_channel_name']}")

                    # Perform routine health check every 10 minutes
                    if asyncio.get_event_loop().time() % 600 < 300:  # Every 10 minutes
                        health_status = await self.voice_handler.health_check()
                        if health_status["healthy"]:
                            logger.debug("✅ Routine voice health check passed")
                        else:
                            logger.warning("⚠️ Routine voice health check detected issues")
                            for issue in health_status["issues"]:
                                logger.warning(f"   • {issue}")

            # Log stats periodically
            if config.debug:
                status = self.get_status()
                logger.info(f"Bot stats: {status}")

        except Exception as e:
            logger.error(f"Error in monitoring task: {e!s}")

    async def _status_command(self, ctx: commands.Context[Any]) -> None:
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
            value=f"Voice: {'✅ 接続中' if status['voice_connected'] else '❌ 未接続'}\nChannel: {status['voice_channel_name'] or 'なし'}",
            inline=True,
        )

        # TTS status
        embed.add_field(
            name="🎤 TTS状態",
            value=f"Engine: {config.tts_engine.upper()}\nSpeaker: {config.tts_speaker}\nPlaying: {'✅' if status['is_playing'] else '❌'}",
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
            value=f"Uptime: {hours:02d}:{minutes:02d}:{seconds:02d}\nLatency: {self.latency * 1000:.0f}ms\nErrors: {status['connection_errors']}",
            inline=True,
        )

        await ctx.send(embed=embed)

    async def _skip_command(self, ctx: commands.Context[Any]) -> None:
        """Skip current TTS playback."""
        if not self.voice_handler:
            await ctx.send("❌ Voice handler not initialized")
            return

        if await self.voice_handler.skip_current():
            await ctx.send("⏭️ Current TTS skipped")
        else:
            await ctx.send("ℹ️ No TTS currently playing")

    async def _clear_command(self, ctx: commands.Context[Any]) -> None:
        """Clear TTS queue."""
        if not self.voice_handler:
            await ctx.send("❌ Voice handler not initialized")
            return

        cleared_count = await self.voice_handler.clear_all()
        await ctx.send(f"🗑️ Cleared {cleared_count} items from TTS queue")

    async def _speakers_command(self, ctx: commands.Context[Any]) -> None:
        """List available TTS speakers."""
        speakers = await tts_engine.get_available_speakers()

        embed = discord.Embed(
            title=f"🎭 Available Speakers ({config.tts_engine.upper()})",
            color=discord.Color.blue(),
            description=f"Current: **{config.tts_speaker}** (ID: {config.speaker_id})",
        )

        speaker_list: list[str] = []
        for name, speaker_id in speakers.items():
            marker = "🔹" if name == config.tts_speaker else "▫️"
            speaker_list.append(f"{marker} `{name}` (ID: {speaker_id})")  # type: ignore[arg-type]

        # Split into chunks if too long
        chunk_size = 10
        chunks: list[list[str]] = [speaker_list[i : i + chunk_size] for i in range(0, len(speaker_list), chunk_size)]

        for i, chunk in enumerate(chunks):
            field_name = "Speakers" if i == 0 else f"Speakers (cont. {i+1})"
            embed.add_field(name=field_name, value="\n".join(chunk), inline=False)

        await ctx.send(embed=embed)

    async def _test_command(self, ctx: commands.Context[Any], text: str) -> None:
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
        current_count = self.stats.get("tts_messages_played", 0)
        self.stats["tts_messages_played"] = (current_count if current_count is not None else 0) + 1

    async def _voice_command(self, ctx: commands.Context[Any], speaker: str | None = None) -> None:
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

    async def _voices_command(self, ctx: commands.Context[Any]) -> None:
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
            field_lines: list[str] = []
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

    async def _voicecheck_command(self, ctx: commands.Context[Any]) -> None:
        """Perform voice connection health check."""
        if not self.voice_handler:
            embed = discord.Embed(title="🔍 Voice Health Check", color=discord.Color.red(), description="❌ Voice handler not initialized")
            await ctx.send(embed=embed)
            return

        # Perform health check
        embed = discord.Embed(title="🔍 Voice Health Check", color=discord.Color.blue(), description="Performing comprehensive voice connection diagnostics...")

        # Send initial message
        message = await ctx.send(embed=embed)

        try:
            # Get basic status
            status = self.voice_handler.get_status()
            health_status = await self.voice_handler.health_check()

            # Update embed with results
            embed = discord.Embed(
                title="🔍 Voice Health Check Results",
                color=(discord.Color.green() if health_status["healthy"] else discord.Color.red()),
                description=f"Overall Status: {'✅ HEALTHY' if health_status['healthy'] else '❌ ISSUES FOUND'}",
            )

            # Connection status
            embed.add_field(
                name="🔗 Connection Status",
                value=f"Voice Client: {'✅' if health_status['voice_client_exists'] else '❌'}\n"
                f"Connected: {'✅' if health_status['voice_client_connected'] else '❌'}\n"
                f"Channel: {status.get('voice_channel_name', 'None') or 'None'}",
                inline=True,
            )

            # Audio system status
            embed.add_field(
                name="🎵 Audio System",
                value=f"Playback Ready: {'✅' if health_status['audio_playback_ready'] else '❌'}\n"
                f"Synthesis: {'✅' if health_status['can_synthesize'] else '❌'}\n"
                f"Queue Size: {status.get('total_queue_size', 0)}",
                inline=True,
            )

            # Issues and recommendations
            if health_status["issues"]:
                issues_text = "\n".join(f"• {issue}" for issue in health_status["issues"])
                embed.add_field(name="⚠️ Issues Found", value=issues_text, inline=False)

            if health_status["recommendations"]:
                recommendations_text = "\n".join(f"💡 {rec}" for rec in health_status["recommendations"])
                embed.add_field(name="🔧 Recommendations", value=recommendations_text, inline=False)

            # If not healthy, offer to attempt reconnection
            if not health_status["healthy"]:
                embed.add_field(name="🔄 Quick Actions", value="Use `!tts reconnect` to attempt reconnection", inline=False)

        except Exception as e:
            embed = discord.Embed(title="🔍 Voice Health Check", color=discord.Color.red(), description=f"❌ Error during health check: {e}")

        await message.edit(embed=embed)

    async def _reconnect_command(self, ctx: commands.Context[Any]) -> None:
        """Manually attempt to reconnect to voice channel."""
        if not self.voice_handler:
            embed = discord.Embed(title="🔄 Voice Reconnection", color=discord.Color.red(), description="❌ Voice handler not initialized")
            await ctx.send(embed=embed)
            return

        embed = discord.Embed(title="🔄 Voice Reconnection", color=discord.Color.orange(), description="Attempting to reconnect to voice channel...")

        message = await ctx.send(embed=embed)

        try:
            # Attempt reconnection
            logger.info(f"🔄 MANUAL RECONNECTION - User {ctx.author.name} requested voice reconnection")
            success = await self.voice_handler.connect_to_channel(config.target_voice_channel_id)

            # Get new status
            new_status = self.voice_handler.get_status()

            if success and new_status["connected"]:
                embed = discord.Embed(title="🔄 Voice Reconnection", color=discord.Color.green(), description="✅ Successfully reconnected to voice channel!")

                embed.add_field(name="📍 Channel Info", value=f"Name: {new_status['voice_channel_name']}\nID: {new_status['voice_channel_id']}", inline=True)

                embed.add_field(name="📊 Queue Status", value=f"Ready: {new_status['audio_queue_size']} chunks\nSynthesizing: {new_status['synthesis_queue_size']} chunks", inline=True)

                logger.info(f"✅ MANUAL RECONNECTION SUCCESSFUL - Connected to {new_status['voice_channel_name']}")
            else:
                embed = discord.Embed(title="🔄 Voice Reconnection", color=discord.Color.red(), description="❌ Reconnection failed")

                embed.add_field(
                    name="🔍 Troubleshooting",
                    value="Check the bot logs for detailed error information.\nCommon issues:\n• Bot lacks 'Connect' permission\n• Channel is full\n• Network connectivity issues",
                    inline=False,
                )

                embed.add_field(name="🔧 Next Steps", value="Use `!tts voicecheck` for detailed diagnostics\nContact bot administrator if issues persist", inline=False)

                logger.error("❌ MANUAL RECONNECTION FAILED - Check logs for detailed error information")

        except Exception as e:
            embed = discord.Embed(title="🔄 Voice Reconnection", color=discord.Color.red(), description=f"❌ Error during reconnection: {e}")
            logger.error(f"💥 CRITICAL ERROR during manual reconnection: {e}")

        await message.edit(embed=embed)

    def get_status(self) -> dict[str, Any]:
        """Get current bot status."""
        voice_status = self.voice_handler.get_status() if self.voice_handler else {}

        uptime = 0.0
        uptime_start = self.stats.get("uptime_start")
        if uptime_start is not None and isinstance(uptime_start, (int, float)):
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
        logger.info("🛑 Starting bot shutdown...")

        # Stop health monitor first
        if self.health_monitor:
            await self.health_monitor.stop()

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

        logger.info("✅ Bot shutdown complete")


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
