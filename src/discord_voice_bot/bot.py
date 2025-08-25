#!/usr/bin/env python3
"""Discord Voice TTS Bot - Main Entry Point."""

import asyncio
from typing import Any, override

from discord.ext import commands

from .bot_factory import BotFactory


class DiscordVoiceTTSBot(commands.Bot):
    """Main Discord Voice TTS Bot class."""

    def __init__(self, config_manager: Any) -> None:
        """Initialize the bot.

        Args:
            config_manager: Configuration manager instance

        """
        # Get intents and command prefix from config
        intents = config_manager.get_intents()
        command_prefix = config_manager.get_command_prefix()

        super().__init__(command_prefix=command_prefix, intents=intents)

        # Store config manager
        self.config_manager = config_manager

        # Initialize component placeholders (will be set by factory)
        self.voice_handler: Any = None
        self.event_handler: Any = None
        self.command_handler: Any = None
        self.slash_handler: Any = None
        self.message_validator: Any = None
        self.status_manager: Any = None
        self.health_monitor: Any = None

        # Bot state management
        self.startup_complete = False
        self.startup_connection_failures = 0
        self.monitor_task: Any = None

        # Statistics tracking (for StartupBot protocol)
        self.stats: dict[str, Any] = {
            "messages_processed": 0,
            "voice_connections": 0,
            "tts_requests": 0,
            "errors": 0,
        }

    async def start_with_config(self) -> None:
        """Start the bot using the stored configuration."""
        token = self.config_manager.get_discord_token()
        await self.start(token)

    async def on_ready(self) -> None:
        """Handle bot ready event and delegate to event handler."""
        print(f"🤖 {self.user} has connected to Discord!")
        if hasattr(self, "event_handler") and self.event_handler:
            await self.event_handler.handle_ready()

    @override
    async def change_presence(self, *, status: Any = None, activity: Any = None) -> None:
        """Change bot presence (required by StartupBot protocol)."""
        await super().change_presence(status=status, activity=activity)

    @property
    def config(self) -> Any:
        """Backward compatibility property for config access."""
        return self.config_manager

    @override
    async def on_message(self, message: Any) -> None:  # discord.Message at runtime
        """Delegate message events to the event handler and process commands."""
        if hasattr(self, "event_handler") and self.event_handler:
            await self.event_handler.handle_message(message)

    async def on_voice_state_update(self, member: Any, before: Any, after: Any) -> None:
        """Delegate voice state updates to the event handler."""
        if hasattr(self, "event_handler") and self.event_handler:
            await self.event_handler.handle_voice_state_update(member, before, after)

    async def on_disconnect(self) -> None:
        """Delegate disconnect events to the event handler."""
        if hasattr(self, "event_handler") and self.event_handler:
            await self.event_handler.handle_disconnect()

    async def on_resumed(self) -> None:
        """Delegate resume events to the event handler."""
        if hasattr(self, "event_handler") and self.event_handler:
            await self.event_handler.handle_resumed()

    @override
    async def on_error(self, event: str, *args: Any, **kwargs: Any) -> None:
        """Delegate errors to the event handler for centralized logging."""
        if hasattr(self, "event_handler") and self.event_handler:
            await self.event_handler.handle_error(event, *args, **kwargs)


async def run_bot() -> None:
    """Create and run the Discord bot."""
    try:
        factory = BotFactory()
        bot = await factory.create_bot()
        await bot.start_with_config()
    except Exception as e:
        print(f"Failed to start bot: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(run_bot())
