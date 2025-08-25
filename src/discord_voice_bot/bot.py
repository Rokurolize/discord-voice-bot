#!/usr/bin/env python3
"""Discord Voice TTS Bot - Main Entry Point."""

import asyncio
from typing import Any, override

from discord.ext import commands

from .bot_factory import BotFactory


class BaseEventBot(commands.Bot):
    """Base class for Discord bots with unified event delegation."""

    async def _delegate_event_async(self, handler_name: str, method_name: str, *args: Any, **kwargs: Any) -> None:
        """Delegate async events to handler if available."""
        if hasattr(self, handler_name) and getattr(self, handler_name):
            handler_instance = getattr(self, handler_name)
            if hasattr(handler_instance, method_name):
                method = getattr(handler_instance, method_name)
                await method(*args, **kwargs)


class DiscordVoiceTTSBot(BaseEventBot):
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
        # Skip Discord connection in test mode
        if self.config_manager.is_test_mode():
            print("🧪 Test mode enabled - skipping Discord connection")
            return

        token = self.config_manager.get_discord_token()
        print(f"Debug: Starting bot with token (length: {len(token)})")  # Debug logging
        # Show first 10 and last 10 characters for debugging
        if len(token) >= 20:
            print(f"Debug: Token preview: {token[:10]}...{token[-10:]}")  # Debug logging
        else:
            print(f"Debug: Token: {token}")  # Debug logging

        try:
            await self.start(token)
        except Exception as e:
            # Log detailed error information for HTTP exceptions
            import traceback

            import discord

            # Check if the exception is a LoginFailure caused by HTTPException
            if isinstance(e, discord.LoginFailure) and e.__cause__:
                cause = e.__cause__
                if isinstance(cause, discord.HTTPException):
                    http_exc = cause
                    print(f"🔴 HTTP Error Details: status={getattr(http_exc, 'status', 'unknown')} code={getattr(http_exc, 'code', 'unknown')} text='{getattr(http_exc, 'text', 'unknown')}'")
                    if hasattr(http_exc, "response") and http_exc.response:
                        print(f"🔴 Response headers: {dict(http_exc.response.headers)}")
                    # Try to get response data
                    if hasattr(http_exc, "data"):
                        print(f"🔴 Response data: {http_exc.data}")
                    elif hasattr(http_exc, "response") and http_exc.response:
                        try:
                            # Try to read response body if available
                            if hasattr(http_exc.response, "text"):
                                print(f"🔴 Response body: {await http_exc.response.text()}")
                        except Exception:
                            print("🔴 Could not read response body")
            elif isinstance(e, discord.HTTPException):
                http_exc = e
                print(f"🔴 HTTP Error Details: status={getattr(http_exc, 'status', 'unknown')} code={getattr(http_exc, 'code', 'unknown')} text='{getattr(http_exc, 'text', 'unknown')}'")
                if hasattr(http_exc, "response") and http_exc.response:
                    print(f"🔴 Response headers: {dict(http_exc.response.headers)}")
                if hasattr(http_exc, "data"):
                    print(f"🔴 Response data: {http_exc.data}")

            print(f"🔴 Exception type: {type(e).__name__}")
            print(f"🔴 Exception message: {e!s}")
            print(f"🔴 Full traceback: {traceback.format_exc()}")
            raise

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
        await self._delegate_event_async("event_handler", "handle_message", message)

    async def on_voice_state_update(self, member: Any, before: Any, after: Any) -> None:
        """Delegate voice state updates to the event handler."""
        await self._delegate_event_async("event_handler", "handle_voice_state_update", member, before, after)

    async def on_disconnect(self) -> None:
        """Delegate disconnect events to the event handler."""
        await self._delegate_event_async("event_handler", "handle_disconnect")

    async def on_resumed(self) -> None:
        """Delegate resume events to the event handler."""
        await self._delegate_event_async("event_handler", "handle_resumed")

    @override
    async def on_error(self, event: str, *args: Any, **kwargs: Any) -> None:
        """Delegate errors to the event handler for centralized logging."""
        # Log detailed error information for HTTP exceptions
        import traceback

        import discord

        if args and isinstance(args[0], discord.HTTPException):
            http_exc = args[0]
            print(f"🔴 HTTP Error Details: {http_exc.status} {http_exc.code} - {http_exc.text}")
            if hasattr(http_exc, "response"):
                print(f"🔴 Response headers: {dict(http_exc.response.headers) if http_exc.response else 'None'}")
            print(f"🔴 Full traceback: {traceback.format_exc()}")

        await self._delegate_event_async("event_handler", "handle_error", event, *args, **kwargs)


async def run_bot(test_mode: bool | None = None) -> None:
    """Create and run the Discord bot."""
    try:
        factory = BotFactory()
        bot = await factory.create_bot(test_mode=test_mode)
        await bot.start_with_config()
    except Exception as e:
        print(f"Failed to start bot: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(run_bot())
