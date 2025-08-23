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
from .protocols import DiscordVoiceBotTTS
from .status_manager import StatusManager
from .voice.handler import VoiceHandler

if TYPE_CHECKING:
    from .slash.registry import SlashCommandRegistry as SlashCommandHandler


class DiscordVoiceTTSBot(DiscordVoiceBotTTS, commands.Bot):
    """Truly minimal bot that delegates everything to modular handlers."""

    stats: dict[str, Any]
    config: ConfigManagerImpl | None
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
        super().__init__(
            command_prefix=config.get_command_prefix() if config else "!",
            intents=config.get_intents() if config else discord.Intents.default(),
            help_command=None,
            case_insensitive=True,
        )

        # Store config and initialize components
        self.config = config
        self.config_manager = ConfigManagerImpl()
        self.stats = {}
        self.monitor_task = None
        # Initialize attributes that are accessed by handlers
        self.startup_connection_failures = 0

        self._init_components()
        self._setup_handlers()

        logger.info("Discord Voice TTS Bot - Truly Minimal Modular")

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
        async def on_ready() -> None:  # type: ignore[reportUnusedFunction]
            await event_handler.handle_ready()

        @self.event
        async def on_message(*, message: discord.Message) -> None:  # type: ignore[reportUnusedFunction]
            await event_handler.handle_message(message)

        @self.event
        async def on_voice_state_update(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState) -> None:  # type: ignore[reportUnusedFunction]
            await event_handler.handle_voice_state_update(member, before, after)

        @self.event
        async def on_disconnect() -> None:  # type: ignore[reportUnusedFunction]
            await event_handler.handle_disconnect()

        @self.event
        async def on_error(event: str, *args: Any, **kwargs: Any) -> None:  # type: ignore[reportUnusedFunction]
            await event_handler.handle_error(event, *args, **kwargs)

    def _setup_commands(self) -> None:
        """Setup commands - all delegated to command handlers."""
        # Command handlers are now initialized, so they should not be None
        if not self.command_handler or not self.slash_handler:
            raise RuntimeError("Command handlers not initialized")

        # Type assertion for mypy since we just checked it's not None
        command_handler = self.command_handler
        slash_handler = self.slash_handler

        # Register simple prefix commands that delegate to command handler
        for name in ["status", "skip", "clear", "test", "voices", "voicecheck", "reconnect"]:
            self._add_simple_command(name, command_handler)

        # Register slash commands
        _ = asyncio.create_task(slash_handler.register_slash_commands())

    def _add_simple_command(self, name: str, command_handler: CommandHandler) -> None:
        """Add a simple command that delegates to command handler."""

        @self.command(name=name)
        async def cmd(ctx: commands.Context[Any], *, text: str = "") -> None:  # type: ignore[reportUnusedFunction]
            _ = await command_handler.process_command(ctx.message)

    async def shutdown(self) -> None:
        """Graceful shutdown."""
        logger.info("Shutting down bot...")
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
