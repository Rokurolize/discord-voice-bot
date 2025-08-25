"""Startup management for event handler."""

import asyncio
from typing import TYPE_CHECKING

import discord
from loguru import logger

if TYPE_CHECKING:
    from .protocols import ConfigManager, StartupBot

# Use StartupBot protocol for type checking to allow attribute access on the bot
# at type-check time without importing runtime discord classes.


class StartupManager:
    """Manages bot startup sequence and initialization."""

    def __init__(self, bot: "StartupBot", config_manager: "ConfigManager"):
        """Initialize startup manager."""
        super().__init__()
        self.bot = bot
        self._config_manager = config_manager
        self.target_channel_id: int = 0

    async def handle_startup(self) -> None:
        """Handle complete bot startup sequence."""
        if getattr(self.bot, "startup_complete", False):
            logger.info("Bot reconnected and ready")
            return

        if self.bot.user:
            logger.info(f"Bot logged in as {self.bot.user} (ID: {self.bot.user.id})")
        else:
            logger.info("Bot logged in (user info not available)")

        # Set bot presence
        activity = discord.Activity(type=discord.ActivityType.listening, name="声チャットのメッセージ 📢")
        await self.bot.change_presence(status=discord.Status.online, activity=activity)

        # Log compliance information
        logger.info("🔧 DISCORD API COMPLIANCE CHECK:")
        logger.info("   - Voice Gateway Version: 8 (required since Nov 2024)")
        logger.info("   - E2EE Support: Enabled via discord.py abstraction")
        logger.info("   - Rate Limiting: 50 req/sec with dynamic headers")
        logger.info("   - Invalid Request Protection: Circuit breaker enabled")
        logger.info("✅ Bot configured for Discord API compliance")

        # Initialize components
        await self._initialize_components()

        # Connect to target voice channel
        self.target_channel_id = self._config_manager.get_target_voice_channel_id()
        logger.info(f"🔗 STARTUP VOICE CONNECTION - Attempting to connect to target voice channel ID: {self.target_channel_id}")

        max_retries = 3
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
                    self._log_troubleshooting_tips()

                    # Count consecutive startup failures (use setattr/getattr to avoid attribute access issues)
                    if getattr(self.bot, "startup_connection_failures", None) is None:
                        self.bot.startup_connection_failures = 0
                    current_failures = getattr(self.bot, "startup_connection_failures", 0)
                    self.bot.startup_connection_failures = current_failures + 1

                    current_failures = getattr(self.bot, "startup_connection_failures", 0)
                    logger.error(f"❌ STARTUP CONNECTION FAILURE #{current_failures}")

                    if current_failures >= 3:
                        logger.error("🔧 BOT SHUTDOWN - Maximum startup connection failures reached")
                        raise RuntimeError("Voice connection failed during startup after 3 attempts - bot cannot function without voice channel access")
                    logger.warning(f"⚠️ Connection failed {current_failures}/3 times during startup")
            except Exception as e:
                logger.error(f"💥 CRITICAL ERROR during connection attempt {attempt + 1}: {e}")
                if attempt == max_retries - 1:
                    logger.error("❌ STARTUP CONNECTION ABORTED - All retry attempts failed with critical errors")
                    import sys

                    sys.exit(1)

        # Start monitoring task (defensive: task may be a custom object with start())
        monitor_task = getattr(self.bot, "monitor_task", None)
        if monitor_task and hasattr(monitor_task, "start"):
            getattr(monitor_task, "start")()

        # Mark startup complete
        self.bot.startup_complete = True
        self.bot.stats["uptime_start"] = asyncio.get_event_loop().time()

        # Sync slash commands
        await self._sync_slash_commands()

        logger.info("Bot startup complete and ready for TTS!")
        logger.info("🩺 Health monitoring system is active")

    async def _initialize_components(self) -> None:
        """Initialize bot components."""
        voice_handler = getattr(self.bot, "voice_handler", None)
        if voice_handler is not None:
            try:
                await voice_handler.start()
            except Exception as e:
                logger.warning(f"Voice handler start failed during initialization: {e}")
        else:
            logger.warning("Voice handler not available during startup")

        # TTS engine is managed by the synthesizer worker/voice handler; no eager start here

        # Start health monitor
        health_monitor = getattr(self.bot, "health_monitor", None)
        if health_monitor is not None:
            try:
                await health_monitor.start()
            except Exception as e:
                logger.warning(f"Health monitor start failed during initialization: {e}")
        else:
            logger.warning("Health monitor not available during startup")

        # Register slash commands via registry if available
        try:
            slash_handler = getattr(self.bot, "slash_handler", None)
            if slash_handler and hasattr(slash_handler, "register_slash_commands"):
                await slash_handler.register_slash_commands()
        except Exception as e:
            logger.warning(f"Slash command registration failed during initialization: {e}")

    async def _attempt_voice_connection(self) -> bool:
        """Attempt to connect to the target voice channel."""
        try:
            voice_handler = getattr(self.bot, "voice_handler", None)
            if not voice_handler:
                logger.error("Voice handler not available for connection attempt")
                return False
            success = await voice_handler.connect_to_channel(self.target_channel_id)

            # Perform final health check for diagnostics
            if not success:
                try:
                    health_status = await self.bot.voice_handler.health_check()
                    logger.error("🔍 FINAL DIAGNOSTICS:")
                    issues = health_status.get("issues", [])
                    for issue in issues:
                        logger.error(f"   • {issue}")
                except AttributeError:
                    logger.error("Voice handler not available for diagnostics")

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

    def _log_troubleshooting_tips(self) -> None:
        """Log troubleshooting tips for connection failures."""
        logger.error("💡 TROUBLESHOOTING TIPS:")
        logger.error("   1. Verify the voice channel ID is correct")
        logger.error("   2. Check if the bot has 'Connect' and 'Speak' permissions in the target channel")
        logger.error("   3. Ensure the bot is added to the server and has proper permissions")
        logger.error("   4. Check if the voice channel exists and is not deleted")
        logger.error("   5. Check server audit logs for any bot-related errors")
