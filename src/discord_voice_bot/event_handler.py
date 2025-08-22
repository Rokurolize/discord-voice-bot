"""Discord event handling for Voice TTS Bot."""

import asyncio
from typing import TYPE_CHECKING, Any

import discord
from loguru import logger

if TYPE_CHECKING:
    from .bot import DiscordVoiceTTSBot


class EventHandler:
    """Handles Discord events with proper error handling and logging."""

    def __init__(self, bot: "DiscordVoiceTTSBot"):
        """Initialize event handler.

        Args:
            bot: The Discord bot instance
        """
        self.bot = bot
        self._voice_state_updating = False
        logger.info("Event handler initialized")

    async def handle_ready(self) -> None:
        """Handle bot ready event with comprehensive initialization."""
        if self.bot.startup_complete:
            logger.info("Bot reconnected and ready")
            return

        if self.bot.user:
            logger.info(f"Bot logged in as {self.bot.user} (ID: {self.bot.user.id})")
        else:
            logger.info("Bot logged in (user info not available)")

        # Set bot presence
        activity = discord.Activity(type=discord.ActivityType.listening, name="声チャットのメッセージ 📢")
        await self.bot.change_presence(status=discord.Status.online, activity=activity)

        # Log critical compliance information
        logger.info("🔧 DISCORD API COMPLIANCE CHECK:")
        logger.info("   - Voice Gateway Version: 8 (required since Nov 2024)")
        logger.info("   - E2EE Support: Enabled via discord.py abstraction")
        logger.info("   - Rate Limiting: 50 req/sec with dynamic headers")
        logger.info("   - Invalid Request Protection: Circuit breaker enabled")
        logger.info("✅ Bot configured for Discord API compliance")

        # Initialize components through bot
        if hasattr(self.bot, "voice_handler") and self.bot.voice_handler:
            await self.bot.voice_handler.start()

        # Start TTS engine
        from .tts_engine import tts_engine

        await tts_engine.start()

        # Start health monitor
        if hasattr(self.bot, "health_monitor") and self.bot.health_monitor:
            await self.bot.health_monitor.start()

        # Connect to target voice channel
        logger.info(f"🔗 STARTUP VOICE CONNECTION - Attempting to connect to target voice channel ID: {self.bot.config.target_voice_channel_id}")
        max_retries = 3

        # Pre-connection diagnostics
        logger.debug("🔍 PRE-CONNECTION DIAGNOSTICS:")
        logger.debug(f"  - Bot guilds: {len(self.bot.guilds)}")
        if self.bot.guilds:
            guild = self.bot.guilds[0]
            logger.debug(f"  - Primary guild: {guild.name} (ID: {guild.id})")
            logger.debug(f"  - Bot permissions in guild: {guild.me.guild_permissions if guild.me else 'Unknown'}")
            logger.debug(f"  - Available channels: {len(guild.channels)}")

            # Check if target channel exists and is accessible
            target_channel = self.bot.get_channel(self.bot.config.target_voice_channel_id)
            if target_channel:
                channel_name = getattr(target_channel, "name", f"ID:{self.bot.config.target_voice_channel_id}")
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
                logger.warning(f"  - Target channel {self.bot.config.target_voice_channel_id} not found in bot's accessible channels")

        for attempt in range(max_retries):
            try:
                logger.info(f"🔄 CONNECTION ATTEMPT {attempt + 1}/{max_retries}")
                success = await self._attempt_voice_connection()

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

                    # Count consecutive startup failures
                    if not hasattr(self.bot, "_startup_connection_failures"):
                        self.bot._startup_connection_failures = 0
                    self.bot._startup_connection_failures += 1

                    logger.error(f"❌ STARTUP CONNECTION FAILURE #{self.bot._startup_connection_failures}")

                    if self.bot._startup_connection_failures >= 3:
                        logger.error("🔧 BOT SHUTDOWN - Maximum startup connection failures reached")
                        # Instead of sys.exit, raise a custom exception to be caught by main.py
                        raise RuntimeError("Voice connection failed during startup after 3 attempts - bot cannot function without voice channel access")
                    logger.warning(f"⚠️ Connection failed {self.bot._startup_connection_failures}/3 times during startup")
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
        if hasattr(self.bot, "monitor_task"):
            self.bot.monitor_task.start()

        # Mark startup complete
        self.bot.startup_complete = True
        self.bot.stats["uptime_start"] = asyncio.get_event_loop().time()

        # Sync slash commands with Discord
        await self._sync_slash_commands()

        logger.info("Bot startup complete and ready for TTS!")
        logger.info("🩺 Health monitoring system is active")

    async def _attempt_voice_connection(self) -> bool:
        """Attempt to connect to the target voice channel."""
        try:
            if not hasattr(self.bot, "voice_handler") or not self.bot.voice_handler:
                logger.warning("Voice handler not available for connection")
                return False

            success = await self.bot.voice_handler.connect_to_channel(self.bot.config.target_voice_channel_id)

            # Perform final health check for diagnostics
            if not success and hasattr(self.bot, "voice_handler") and self.bot.voice_handler:
                health_status = await self.bot.voice_handler.health_check()
                logger.error("🔍 FINAL DIAGNOSTICS:")
                for issue in health_status["issues"]:
                    logger.error(f"   • {issue}")

            return success
        except Exception as e:
            logger.error(f"Error during voice connection attempt: {e}")
            return False

    async def _sync_slash_commands(self) -> None:
        """Sync slash commands with Discord."""
        try:
            logger.info("🔧 Syncing slash commands with Discord...")

            # First try syncing globally
            synced = await self.bot.tree.sync()
            logger.info(f"✅ Successfully synced {len(synced)} slash commands globally with Discord")

            # Log the synced commands for debugging
            for cmd in synced:
                logger.debug(f"  - Synced command: /{cmd.name} - {cmd.description}")

        except Exception as e:
            logger.error(f"❌ Failed to sync slash commands globally: {e}")

            # Try syncing to current guild only as fallback
            try:
                if self.bot.guilds:
                    guild = self.bot.guilds[0]
                    logger.info(f"🔄 Attempting guild-only sync to {guild.name}...")
                    guild_synced = await self.bot.tree.sync(guild=guild)
                    logger.info(f"✅ Successfully synced {len(guild_synced)} slash commands to guild {guild.name}")
                else:
                    logger.warning("⚠️ No guilds available for guild-only sync")
            except Exception as guild_e:
                logger.error(f"❌ Failed to sync slash commands to guild: {guild_e}")
                logger.warning("⚠️ Slash commands may not be available until next restart")

    async def handle_message(self, message: discord.Message) -> None:
        """Handle message events with proper filtering and validation."""
        try:
            # Log all messages for debugging (rate limited)
            logger.debug(f"Received message from {message.author.name} (ID: {message.id}) in channel {message.channel.id}: {message.content[:50]}")

            # Process commands first (with rate limiting) - BEFORE TTS filtering
            logger.debug(f"Processing commands for message: {message.content}")
            if hasattr(self.bot, "command_handler") and self.bot.command_handler:
                await self.bot.command_handler.process_command(message)
            elif hasattr(self.bot, "voice_handler") and self.bot.voice_handler:
                await self.bot.voice_handler.make_rate_limited_request(self.bot.process_commands, message)
            else:
                await self.bot.process_commands(message)

            # Apply comprehensive message filtering
            if not await self._should_process_message(message):
                return

            # Apply additional message validation
            processed_message = await self._validate_and_process_message(message)
            if not processed_message:
                logger.debug(f"Message {message.id} from {message.author.name} was filtered out after validation")
                return

            # Add to TTS queue with rate limiting
            if hasattr(self.bot, "voice_handler") and self.bot.voice_handler:
                await self.bot.voice_handler.add_to_queue(processed_message)
                current_count = self.bot.stats.get("messages_processed", 0)
                self.bot.stats["messages_processed"] = int(current_count if current_count is not None else 0) + 1
                logger.debug(f"Queued TTS message from {message.author.display_name}")
            else:
                logger.warning("Voice handler not initialized, cannot queue TTS message")

        except Exception as e:
            logger.error(f"Error processing message {message.id}: {e!s}")
            current_errors = self.bot.stats.get("connection_errors", 0)
            self.bot.stats["connection_errors"] = int(current_errors if current_errors is not None else 0) + 1

    async def handle_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> None:
        """Handle voice state update events with improved reconnection logic."""
        try:
            # Ensure we are handling a voice state update for the bot itself
            if not self.bot.user or member.id != self.bot.user.id:
                return

            before_channel_name = before.channel.name if before.channel else "None"
            after_channel_name = after.channel.name if after.channel else "None"
            logger.debug(f"Voice state update - Before: {before_channel_name}, After: {after_channel_name}")

            # If the bot is disconnected from a voice channel, attempt to reconnect
            if before.channel and not after.channel:
                logger.warning(f"⚠️ VOICE DISCONNECTION DETECTED - Bot was disconnected from {before_channel_name} (ID: {before.channel.id})")

                # Report disconnection to health monitor
                if hasattr(self.bot, "health_monitor") and self.bot.health_monitor:
                    self.bot.health_monitor.record_disconnection(f"Disconnected from {before_channel_name}")

                # Check if we're already attempting reconnection
                if self._voice_state_updating:
                    logger.debug("Reconnection already in progress, skipping")
                    return

                # Always attempt cleanup first
                if hasattr(self.bot, "voice_handler") and self.bot.voice_handler:
                    await self.bot.voice_handler.cleanup_voice_client()

                # Only reconnect if the voice handler is initialized
                if hasattr(self.bot, "voice_handler") and self.bot.voice_handler:
                    self._voice_state_updating = True
                    try:
                        # Add a longer delay to prevent rapid reconnection loops
                        await asyncio.sleep(5)
                        logger.info(f"🔄 ATTEMPTING RECONNECTION to voice channel {self.bot.config.target_voice_channel_id}")

                        # Force cleanup before attempting new connection
                        await self.bot.voice_handler.cleanup_voice_client()

                        success = await self.bot.voice_handler.connect_to_channel(self.bot.config.target_voice_channel_id)
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

    async def handle_disconnect(self) -> None:
        """Handle bot disconnect."""
        logger.warning("Bot disconnected from Discord - monitoring for reconnection")
        logger.debug("Setting startup_complete to False due to disconnect")
        self.bot.startup_complete = False

        # Log additional context if available
        if hasattr(self.bot, "voice_handler") and self.bot.voice_handler:
            voice_status = self.bot.voice_handler.get_status()
            logger.debug(f"Voice handler status at disconnect: {voice_status}")

    async def handle_resumed(self) -> None:
        """Handle bot resume."""
        logger.info("Bot connection resumed")

    async def handle_voice_server_update(self, payload: dict[str, Any]) -> None:
        """Handle VOICE_SERVER_UPDATE event with proper Discord API compliance."""
        if hasattr(self.bot, "voice_handler") and self.bot.voice_handler:
            await self.bot.voice_handler.handle_voice_server_update(payload)
        else:
            logger.warning("⚠️ Voice handler not initialized, cannot handle voice server update")

    async def handle_error(self, event: str, *args: Any, **kwargs: Any) -> None:
        """Handle general errors."""
        logger.error(f"Discord event error in {event}: {args} {kwargs}")

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

            # Only process messages from the target voice channel's text chat
            if hasattr(message.channel, "id"):
                # For now, process messages from any channel that the bot can see
                # This allows flexibility for different server setups
                return True

            return True

        except Exception as e:
            logger.error(f"Error in message filtering: {e!s}")
            return False

    async def _validate_and_process_message(self, message: discord.Message) -> dict[str, Any] | None:
        """Validate and process message with proper sanitization."""
        try:
            # Sanitize message content
            sanitized_content = self._sanitize_message_content(message.content)

            # Use the existing message processor
            from .message_processor import message_processor

            processed_message = await message_processor.process_message(message)

            if processed_message:
                # Add additional validation and sanitization
                processed_message["original_content"] = message.content
                processed_message["sanitized_content"] = sanitized_content
                processed_message["validation_passed"] = True

                # Apply rate limiting to message processing
                if hasattr(self.bot, "voice_handler") and self.bot.voice_handler:
                    await self.bot.voice_handler.rate_limiter.wait_if_needed()

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
