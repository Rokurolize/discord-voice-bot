#!/usr/bin/env python3
"""Discord Voice TTS Bot - Main Entry Point."""

import asyncio
from typing import TYPE_CHECKING, Any, override

import discord
from discord.ext import commands

from .bot_factory import BotFactory

if TYPE_CHECKING:
    from .config import Config


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

    def __init__(self, config: Config) -> None:
        """Initialize the bot.

        Args:
            config: Configuration object

        """
        # Get intents and command prefix from config
        intents = discord.Intents.default()
        intents.message_content = True
        intents.voice_states = True
        intents.guilds = True

        super().__init__(command_prefix=config.command_prefix, intents=intents)

        # Store config
        self.config = config

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

    async def _log_http_exception_details(self, http_exc: discord.HTTPException) -> None:
        """Log detailed HTTP exception information."""
        print(f"🔴 HTTP Error Details: status={getattr(http_exc, 'status', 'unknown')} code={getattr(http_exc, 'code', 'unknown')} text='{getattr(http_exc, 'text', 'unknown')}'")
        if hasattr(http_exc, "response") and http_exc.response:
            print(f"🔴 Response headers: {dict(http_exc.response.headers)}")
        try:
            data = getattr(http_exc, "data", None)
            if data is not None:
                print(f"🔴 Response data: {data}")
        except AttributeError:
            pass

        if hasattr(http_exc, "response") and http_exc.response:
            try:
                response = getattr(http_exc, "response", None)
                if response and hasattr(response, "text"):
                    text_method = getattr(response, "text", None)
                    if text_method and callable(text_method):
                        try:
                            result = text_method()
                            if asyncio.iscoroutine(result):
                                print(f"🔴 Response body: {await result}")
                            elif result is not None:
                                print(f"🔴 Response body: {result}")
                        except Exception:
                            print("🔴 Could not read response body")
            except Exception:
                print("🔴 Could not read response body")

    async def start_with_config(self) -> None:
        """Start the bot using the stored configuration."""
        # Skip Discord connection in test mode
        if self.config.test_mode:
            print("🧪 Test mode enabled - skipping Discord connection")
            return

        token = self.config.discord_token

        try:
            await self.start(token)
        except Exception as e:
            # Log detailed error information for HTTP exceptions
            import traceback

            # Check if the exception is a LoginFailure caused by HTTPException
            if isinstance(e, discord.LoginFailure) and e.__cause__:
                cause = e.__cause__
                if isinstance(cause, discord.HTTPException):
                    await self._log_http_exception_details(cause)
            elif isinstance(e, discord.HTTPException):
                await self._log_http_exception_details(e)

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

        if args and isinstance(args[0], discord.HTTPException):
            http_exc = args[0]
            print(f"🔴 HTTP Error Details: {http_exc.status} {http_exc.code} - {http_exc.text}")
            if hasattr(http_exc, "response"):
                print(f"🔴 Response headers: {dict(http_exc.response.headers) if http_exc.response else 'None'}")
            print(f"🔴 Full traceback: {traceback.format_exc()}")

        await self._delegate_event_async("event_handler", "handle_error", event, *args, **kwargs)


async def run_bot(config: Config) -> None:
    """Create and run the Discord bot."""
    try:
        factory = BotFactory()
        bot = await factory.create_bot(config)
        await bot.start_with_config()
    except Exception as e:
        print(f"Failed to start bot: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(run_bot())
