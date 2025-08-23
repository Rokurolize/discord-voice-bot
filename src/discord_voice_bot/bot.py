"""Discord Voice TTS Bot - Type-safe Modular Implementation."""

import asyncio
from typing import TYPE_CHECKING, Any

import discord
from discord.ext import commands
from loguru import logger

from .command_handler import CommandHandler
from .config_manager import ConfigManagerImpl
from .event_handler import EventHandler
from .health_monitor import HealthMonitor
from .message_validator import MessageValidator
from .protocols import ConfigManager
from .status_manager import StatusManager
from .voice.handler import VoiceHandler
from .voice.stats_tracker import StatsTracker

if TYPE_CHECKING:
    from .slash.registry import SlashCommandRegistry as SlashCommandHandler


# DiscordVoiceBotTTS protocol is used for structural subtyping, no explicit import needed


class DiscordVoiceTTSBot(commands.Bot):
    """Truly minimal bot that delegates everything to modular handlers."""

    stats: "StatsTracker"
    config: ConfigManagerImpl | None
    config_manager: ConfigManager
    monitor_task: asyncio.Task[None] | None
    event_handler: EventHandler | None
    command_handler: CommandHandler | None
    slash_handler: "SlashCommandHandler | None"
    status_manager: StatusManager | None
    message_validator: MessageValidator | None
    voice_handler: "VoiceHandler | None"
    health_monitor: HealthMonitor | None
    startup_complete: bool

    def __init__(self, config: ConfigManagerImpl | None = None) -> None:
        """Initialize with modular components."""
        # Store config first to avoid issues with super().__init__
        self.config = config
        self.config_manager = ConfigManagerImpl()

        super().__init__(
            command_prefix=config.get_command_prefix() if config else "!",
            intents=config.get_intents() if config else discord.Intents.default(),
            help_command=None,
            case_insensitive=True,
        )

        # Initialize remaining attributes after super().__init__
        self.stats = StatsTracker()
        self.monitor_task = None
        self.startup_connection_failures = 0

        logger.debug("Discord.py v2.x initialization completed successfully")

        # Initialize attributes that need to be set before _init_components
        self.event_handler = None
        self.command_handler = None
        self.slash_handler = None
        self.status_manager = None
        self.message_validator = None
        self.voice_handler = None
        self.health_monitor = None
        self.startup_complete = False

        self._init_components()
        self._setup_handlers()

        logger.info("Discord Voice TTS Bot - Truly Minimal Modular")

    async def setup_hook(self) -> None:  # type: ignore[override]
        """Discord.py v2.x setup hook - called after login but before connecting to gateway."""
        logger.info("Running setup_hook for Discord.py v2.x compatibility")

        # Initialize slash commands after bot is logged in
        if self.slash_handler:
            try:
                await self.slash_handler.register_slash_commands()
                logger.info("Slash commands registered successfully via setup_hook")
            except Exception as e:
                logger.error(f"Failed to register slash commands in setup_hook: {e}")

        # Start any background tasks here if needed
        logger.debug("setup_hook completed successfully")

    def _init_components(self) -> None:
        """Initialize modular components."""
        # Initialize components that don't need the bot instance yet
        self.status_manager = StatusManager()
        self.message_validator = MessageValidator()

        # Initialize components that need the bot instance - defer to setup
        self.event_handler = None
        self.command_handler = None
        self.slash_handler = None
        self.voice_handler = None
        self.health_monitor = None
        self.startup_complete = False

    def _setup_handlers(self) -> None:
        """Setup event and command handlers."""
        # Initialize remaining components now that bot is fully initialized
        from .slash.registry import SlashCommandRegistry as SlashCommandHandler

        # Type ignore needed due to discord.py inheritance complexities
        self.event_handler = EventHandler(self, self.config_manager)
        self.command_handler = CommandHandler(self)
        self.slash_handler = SlashCommandHandler(self)
        self.voice_handler = VoiceHandler(self, self.config_manager)
        self.health_monitor = HealthMonitor(self, self.config_manager)

        self._setup_events()
        self._setup_commands()

    def _setup_events(self) -> None:
        """Setup Discord events - all delegated to event handler."""
        # Event handlers are now initialized, so they should not be None
        if not self.event_handler:
            raise RuntimeError("Event handler not initialized")

        # Type assertion for mypy since we just checked it's not None
        event_handler = self.event_handler

        @self.event
        async def on_ready() -> None:
            """Handle bot ready event - registered by Discord.py automatically."""
            await event_handler.handle_ready()

        # Mark function as used by Discord.py event system
        _ = on_ready

        @self.event
        async def on_message(message: discord.Message) -> None:
            """Handle message events - registered by Discord.py automatically."""
            await event_handler.handle_message(message)

        # Mark function as used by Discord.py event system
        _ = on_message

        @self.event
        async def on_voice_state_update(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState) -> None:
            """Handle voice state update events - registered by Discord.py automatically."""
            await event_handler.handle_voice_state_update(member, before, after)

        # Mark function as used by Discord.py event system
        _ = on_voice_state_update

        @self.event
        async def on_disconnect() -> None:
            """Handle bot disconnect events - registered by Discord.py automatically."""
            await event_handler.handle_disconnect()

        # Mark function as used by Discord.py event system
        _ = on_disconnect

        @self.event
        async def on_error(event: str, *args: Any, **kwargs: Any) -> None:
            """Handle error events - registered by Discord.py automatically."""
            await event_handler.handle_error(event, *args, **kwargs)

        # Mark function as used by Discord.py event system
        _ = on_error

    def _setup_commands(self) -> None:
        """Setup commands - all delegated to command handlers."""
        # Command handlers are now initialized, so they should not be None
        if not self.command_handler or not self.slash_handler:
            raise RuntimeError("Command handlers not initialized")

        # Type assertion for mypy since we just checked it's not None
        command_handler = self.command_handler
        _ = self.slash_handler  # Keep reference for type checking

        # Register simple prefix commands that delegate to command handler
        for name in ["status", "skip", "clear", "test", "voices", "voicecheck", "reconnect"]:
            self._add_simple_command(name, command_handler)

        # Note: Slash commands will be registered in setup_hook instead of here
        # to ensure proper Discord.py v2.x initialization timing
        logger.debug("Deferring slash command registration to setup_hook")

    def _add_simple_command(self, name: str, command_handler: CommandHandler) -> None:
        """Add a simple command that delegates to command handler."""

        @self.command(name=name)
        async def cmd(ctx: commands.Context[Any], *, text: str = "") -> None:
            """Handle prefix commands - registered by Discord.py automatically."""
            _ = await command_handler.process_command(ctx.message)

        # Mark function as used by Discord.py command system
        _ = cmd

    async def shutdown(self) -> None:
        """Graceful shutdown with proper voice channel cleanup."""
        logger.info("Shutting down bot...")

        # First, ensure proper voice channel cleanup before closing Discord connection
        if hasattr(self, "voice_handler") and self.voice_handler:
            try:
                logger.info("🧹 Cleaning up voice connection before shutdown...")
                if self.voice_handler.is_connected():
                    # Get voice channel info before cleanup for logging
                    voice_channel_name = "Unknown"
                    try:
                        if self.voice_handler.voice_client and self.voice_handler.voice_client.channel:
                            voice_channel_name = self.voice_handler.voice_client.channel.name
                    except Exception:
                        pass

                    logger.info(f"🎤 Leaving voice channel: {voice_channel_name}")
                    await self.voice_handler.cleanup_voice_client()
                    logger.info("✅ Voice channel cleanup completed")
                else:
                    logger.debug("No active voice connection to clean up")
            except Exception as e:
                logger.error(f"⚠️ Error during voice cleanup: {e}")
                # Continue with shutdown even if voice cleanup fails

        # Now close the Discord connection
        await self.close()
        logger.info("Bot shutdown complete")


# Factory function for easy bot creation
async def create_bot(config: Any | None = None) -> DiscordVoiceTTSBot:
    """Create a bot instance using factory pattern."""
    # Import here to avoid circular imports
    import importlib

    bot_factory_module = importlib.import_module(".bot_factory", package="discord_voice_bot")
    BotFactory = bot_factory_module.BotFactory

    factory = BotFactory()
    return await factory.create_bot()


# Run bot function
async def run_bot() -> None:
    """Create and run the Discord bot."""
    try:
        from .config_manager import ConfigManagerImpl

        # Create config manager to avoid direct config import
        config_manager = ConfigManagerImpl()
        config_manager.validate()

        bot = await create_bot(None)  # Config is handled by ConfigManagerImpl
        await bot.start(config_manager.get_discord_token())
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        raise


# Main execution
if __name__ == "__main__":
    asyncio.run(run_bot())
