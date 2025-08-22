"""Discord Voice TTS Bot - Truly Minimal Modular Implementation."""

import asyncio
from typing import Any

import discord
from discord.ext import commands
from loguru import logger

from .command_handler import CommandHandler
from .event_handler import EventHandler
from .message_validator import MessageValidator
from .slash_command_handler import SlashCommandHandler
from .status_manager import StatusManager


class DiscordVoiceTTSBot(commands.Bot):
    """Truly minimal bot that delegates everything to modular handlers."""

    def __init__(self, config=None) -> None:
        """Initialize with modular components."""
        super().__init__(
            command_prefix=getattr(config, "command_prefix", "!"),
            intents=getattr(config, "get_intents", lambda: discord.Intents.default())(),
            help_command=None,
            case_insensitive=True,
        )

        # Store config and initialize components
        self.config = config
        self._init_components()
        self._setup_handlers()

        logger.info("Discord Voice TTS Bot - Truly Minimal Modular")

    def _init_components(self) -> None:
        """Initialize modular components."""
        self.event_handler = EventHandler(self)
        self.command_handler = CommandHandler(self)
        self.slash_handler = SlashCommandHandler(self)
        self.status_manager = StatusManager()
        self.message_validator = MessageValidator()
        self.startup_complete = False

    def _setup_handlers(self) -> None:
        """Setup event and command handlers."""
        self._setup_events()
        self._setup_commands()

    def _setup_events(self) -> None:
        """Setup Discord events - all delegated to event handler."""

        @self.event
        async def on_ready() -> None:
            await self.event_handler.handle_ready()

        @self.event
        async def on_message(message: discord.Message) -> None:
            await self.event_handler.handle_message(message)

        @self.event
        async def on_voice_state_update(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState) -> None:
            await self.event_handler.handle_voice_state_update(member, before, after)

        @self.event
        async def on_disconnect() -> None:
            await self.event_handler.handle_disconnect()

        @self.event
        async def on_error(event: str, *args: Any, **kwargs: Any) -> None:
            await self.event_handler.handle_error(event, *args, **kwargs)

    def _setup_commands(self) -> None:
        """Setup commands - all delegated to command handlers."""
        # Register simple prefix commands that delegate to command handler
        for name in ["status", "skip", "clear", "test", "voices", "voicecheck", "reconnect"]:
            self._add_simple_command(name)

        # Register slash commands
        if self.slash_handler:
            asyncio.create_task(self.slash_handler.register_slash_commands())

    def _add_simple_command(self, name: str) -> None:
        """Add a simple command that delegates to command handler."""

        @self.command(name=name)
        async def cmd(ctx: commands.Context[Any], *, text: str = "") -> None:
            if self.command_handler:
                await self.command_handler.process_command(ctx.message)

    async def shutdown(self) -> None:
        """Graceful shutdown."""
        logger.info("Shutting down bot...")
        await self.close()
        logger.info("Bot shutdown complete")


# Factory function for easy bot creation
async def create_bot(config=None) -> DiscordVoiceTTSBot:
    """Create a bot instance using factory pattern."""
    from .bot_factory import BotFactory

    factory = BotFactory()
    return await factory.create_bot()


# Run bot function
async def run_bot() -> None:
    """Create and run the Discord bot."""
    try:
        from .config import config

        config.validate()
        bot = await create_bot(config)
        await bot.start(config.discord_token)
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        raise


# Main execution
if __name__ == "__main__":
    asyncio.run(run_bot())
