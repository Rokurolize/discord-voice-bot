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
        """Initialize the bot.

        Supports initialization via either a ConfigManager-compatible object or a
        Config dataclass. If ``config`` is provided, it will be wrapped in a
        ``ConfigManagerImpl`` internally.

        Args:
            config_manager: Configuration manager instance or Config (legacy path)
            config: Config dataclass instance

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
        """Provide the underlying Config dataclass when available.

        Many subsystems (e.g., TTSEngine) expect the concrete ``Config``
        dataclass. When running with a ConfigManager implementation that wraps
        a Config, expose it; otherwise, return whatever was provided.
        """
        cm = getattr(self, "config_manager", None)
        if cm is None:
            return None
        # ConfigManagerImpl exposes a private _get_config method; use it when present
        get_cfg = getattr(cm, "_get_config", None)
        try:
            if callable(get_cfg):
                return get_cfg()
        except Exception:
            pass
        return cm

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
        await self._delegate_event_async("event_handler", "handle_error", event, *args, **kwargs)


async def run_bot(config: Config | None = None) -> None:
    """Create and run the Discord bot using the provided Config.

    If ``config`` is not provided, configuration will be loaded from the
    environment via ``Config.from_env()``.
    """
    factory = BotFactory()
    bot: Any | None = None
    try:
        cfg = config or Config.from_env()
        bot = await factory.create_bot(cfg)
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
