#!/usr/bin/env python3
"""Discord Voice TTS Bot - Main Entry Point.

This module supports both the previous ConfigManager-based initialization and the
newer direct Config dataclass injection used by tests and runtime.
"""

import asyncio
from typing import Any, override

from discord.ext import commands

from .bot_factory import BotFactory
from .config import Config
from .config_manager import ConfigManagerImpl


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

    def __init__(self, config_manager: Any | None = None, *, config: Config | None = None) -> None:
        """
        Create a DiscordVoiceTTSBot instance, normalizing configuration and initializing internal placeholders and startup state.

        This initializer accepts either:
        - a Config dataclass via the `config` keyword (preferred), or
        - a Config dataclass or a ConfigManager-compatible object via `config_manager`.
        If a Config is provided (in either parameter) it is wrapped with ConfigManagerImpl. If no configuration is supplied, the environment is used (Config.from_env()).

        Behavioral notes:
        - Retrieves intents and command prefix from the resulting config manager and passes them to the base commands.Bot initializer.
        - Stores the normalized config manager on self.config_manager.
        - Initializes component placeholders (voice_handler, command_handler, slash_handler, message_validator, status_manager, health_monitor) to None; these are expected to be wired by the surrounding factory. Event handlers are managed by the EventBridge Cog.
        - Initializes startup state (startup_complete, startup_connection_failures, monitor_task) and a stats dict with keys: "messages_processed", "voice_connections", "tts_requests", "errors".
        """
        # Normalize to a ConfigManager-compatible instance
        if config is not None:
            _cm = ConfigManagerImpl(config)
        else:
            # If a Config dataclass was passed via the legacy positional arg, wrap it
            if isinstance(config_manager, Config):
                _cm = ConfigManagerImpl(config_manager)
            else:
                _cm = config_manager

        if _cm is None:
            # Fall back to environment-derived configuration
            _cm = ConfigManagerImpl(Config.from_env())

        # Get intents and command prefix from config manager
        intents = _cm.get_intents()
        command_prefix = _cm.get_command_prefix()

        super().__init__(command_prefix=command_prefix, intents=intents)

        # Store config manager
        self.config_manager = _cm

        # Initialize component placeholders (will be set by factory)
        self.voice_handler: Any = None
        # Reserved for backward compatibility; EventBridge manages handlers now
        self.event_handler: Any = None
        # Deprecated: legacy handlers are no longer used; kept for compatibility
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
        """
        Start the bot using the configured Discord token.

        If the active configuration is in test mode, this method prints a short message and returns without connecting to Discord. Otherwise it retrieves the Discord token from the bot's configuration manager and calls the underlying `start` coroutine with that token.
        """
        # Skip Discord connection in test mode
        if self.config_manager.is_test_mode():
            print("🧪 Test mode enabled - skipping Discord connection")
            return

        token = self.config_manager.get_discord_token()
        await self.start(token)

    async def on_ready(self) -> None:
        """
        Called when the bot is fully connected to Discord.

        Prints a connection message and, if no EventBridge cog is present,
        delegates to the legacy `event_handler.handle_ready()` for backward
        compatibility. When EventBridge is registered, its listener handles
        readiness and this method becomes a no-op (aside from logging).
        """
        print(f"🤖 {self.user} has connected to Discord!")
        if any(c.__class__.__name__ == "EventBridge" for c in self.cogs.values()):
            return
        if hasattr(self, "event_handler") and self.event_handler:
            await self.event_handler.handle_ready()

    @override
    async def change_presence(self, *, status: Any = None, activity: Any = None) -> None:
        """Change bot presence (required by StartupBot protocol)."""
        await super().change_presence(status=status, activity=activity)

    @property
    def config(self) -> Any:
        """
        Return the underlying Config dataclass if available, otherwise return the stored config manager or None.

        If the bot's `config_manager` has a callable `_get_config()` method, this property calls it and returns its result (exceptions from that call are suppressed). If no `config_manager` is present, returns None; if `_get_config()` is not available, returns the `config_manager` object itself.

        Returns:
            The concrete Config dataclass, the config manager object, or None.

        """
        cm = getattr(self, "config_manager", None)
        if cm is None:
            return None
        # Prefer a concrete Config; support both attribute and callable accessors
        attr = getattr(cm, "config", None)
        if attr is not None:
            if callable(attr):
                try:
                    return attr()
                except Exception:
                    pass
            else:
                return attr
        getter = getattr(cm, "_get_config", None)
        if callable(getter):
            try:
                return getter()
            except Exception:
                pass
        return cm

    @override
    async def on_message(self, message: Any) -> None:  # discord.Message at runtime
        """
        Delegate an incoming Discord message to the configured event handler (legacy path).

        Note:
            Event handling is moving to Cog listeners (EventBridge). To avoid
            double processing, this method becomes a no-op when an EventBridge
            cog is registered on the bot.

        Args:
            message: The message object received from Discord (typed as Any at runtime).


        """
        if any(c.__class__.__name__ == "EventBridge" for c in self.cogs.values()):
            return
        await self._delegate_event_async("event_handler", "handle_message", message)

    async def on_voice_state_update(self, member: Any, before: Any, after: Any) -> None:
        """Delegate voice state updates to the event handler (legacy path)."""
        if any(c.__class__.__name__ == "EventBridge" for c in self.cogs.values()):
            return
        await self._delegate_event_async("event_handler", "handle_voice_state_update", member, before, after)

    async def on_disconnect(self) -> None:
        """Delegate disconnect events to the event handler (legacy path)."""
        if any(c.__class__.__name__ == "EventBridge" for c in self.cogs.values()):
            return
        await self._delegate_event_async("event_handler", "handle_disconnect")

    async def on_resumed(self) -> None:
        """Delegate resume events to the event handler (legacy path)."""
        if any(c.__class__.__name__ == "EventBridge" for c in self.cogs.values()):
            return
        await self._delegate_event_async("event_handler", "handle_resumed")

    @override
    async def on_error(self, event: str, *args: Any, **kwargs: Any) -> None:
        """
        Delegate an error event to ConnectionHandler via EventBridge when available.
        Falls back to legacy event_handler if present; otherwise prints a simple log line.
        """
        # Prefer EventBridge -> ConnectionHandler
        try:
            bridge = next((c for c in self.cogs.values() if c.__class__.__name__ == "EventBridge"), None)
            conn = getattr(bridge, "connection_handler", None) if bridge else None
            if conn and hasattr(conn, "handle_error"):
                await conn.handle_error(event, *args, **kwargs)
                return
        except Exception:
            pass

        # Legacy facade fallback
        if hasattr(self, "event_handler") and self.event_handler and hasattr(self.event_handler, "handle_error"):
            await self.event_handler.handle_error(event, *args, **kwargs)
        else:
            print(f"[on_error] Unhandled error event: {event}", flush=True)


async def run_bot(config: Config | None = None) -> None:
    """
    Start the Discord Voice TTS bot using the provided configuration.

    If `config` is None, the configuration is loaded from the environment via Config.from_env().
    This function creates a BotFactory, builds and initializes the bot and its services, then starts
    the bot's run flow (start_with_config). It ensures the bot is shut down by the factory when the
    start sequence completes or fails.

    Notes:
    - CancelledError is propagated unchanged.
    - Other exceptions are printed and re-raised.

    """
    factory = BotFactory()
    bot: Any | None = None
    try:
        cfg = config or Config.from_env()
        bot = await factory.create_bot(cfg)
        if not cfg.test_mode:
            await factory.initialize_services(bot)
        assert bot is not None
        await bot.start_with_config()
    except asyncio.CancelledError:
        raise
    except Exception as e:
        print(f"Failed to start bot: {e}")
        raise
    finally:
        if bot:
            await factory.shutdown_bot(bot)


if __name__ == "__main__":
    asyncio.run(run_bot())
