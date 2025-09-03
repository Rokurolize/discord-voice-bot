"""Bot factory for Discord Voice TTS Bot initialization and configuration."""

import dataclasses
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

from loguru import logger

from .config import Config

if TYPE_CHECKING:
    from .event_handler import EventHandler
    from .message_validator import MessageValidator
    from .status_manager import StatusManager


class ComponentRegistry:
    """Registry for managing bot components."""

    def __init__(self) -> None:
        """Initialize component registry."""
        super().__init__()
        self._components: dict[str, Any] = {}

    def register(self, name: str, component: Any) -> None:
        """Register a component.

        Args:
            name: Component name
            component: Component instance

        """
        self._components[name] = component
        logger.debug(f"Registered component: {name}")

    def get(self, name: str) -> Any:
        """Get a component by name.

        Args:
            name: Component name

        Returns:
            Component instance or None if not found

        """
        return self._components.get(name)

    def get_all(self) -> dict[str, Any]:
        """Get all registered components.

        Returns:
            Dictionary of all components

        """
        return self._components.copy()

    def clear(self) -> None:
        """Clear all registered components."""
        self._components.clear()


class BotFactory:
    """Factory for creating and configuring Discord Voice TTS Bot instances."""

    def __init__(self) -> None:
        """Initialize bot factory."""
        super().__init__()
        self.registry = ComponentRegistry()
        logger.info("Bot factory initialized")

    async def create_bot(self, config: Config | None = None, bot_class: type[Any] | None = None, *, test_mode: bool | None = None) -> Any:
        """Create, configure, and return a fully-initialized bot instance.

        Args:
            config: Optional per-bot Config; when omitted the configuration is loaded from the environment.
            bot_class: Optional bot class to instantiate; uses the default when omitted.
            test_mode: Optional override for the Config.test_mode field.

        Returns:
            The configured bot instance.

        """
        try:
            # Import here to avoid circular imports
            if bot_class is None:
                # Use TYPE_CHECKING to avoid runtime import
                import importlib

                bot_module = importlib.import_module(".bot", package="discord_voice_bot")
                bot_class = bot_module.DiscordVoiceTTSBot

            # Prepare configuration
            cfg = config or Config.from_env()
            if test_mode is not None:
                cfg = dataclasses.replace(cfg, test_mode=test_mode)

            # Create bot instance with configuration (direct dataclass injection)
            if bot_class is None:
                raise ValueError("Bot class cannot be None")
            bot: Any = bot_class(config=cfg)

            # Setup all components with config
            await self._setup_components(bot, cfg)

            # Validate configuration
            await self._validate_configuration(bot, cfg)

            logger.info("Bot instance created and configured successfully")
            return bot

        except Exception as e:
            logger.error(f"Failed to create bot instance: {e}")
            raise

    async def _setup_components(self, bot: Any, config: Config) -> None:
        """
        Set up and register all runtime components for the given bot instance.

        Creates and registers standard components, attaching them as attributes on the bot.

        Args:
            bot: The bot to attach components to.
            config: Per-bot Config for components that depend on configuration.

        Raises:
            Exception: Logged and re-raised on failure.

        """
        logger.info("Setting up bot components...")

        # Create and register components
        components_to_setup = [
            ("event_handler", self._create_event_handler),
            ("slash_handler", self._create_slash_command_handler),
            ("message_validator", self._create_message_validator),
            ("status_manager", self._create_status_manager),
            ("voice_handler", self._create_voice_handler),
            ("health_monitor", self._create_health_monitor),
        ]

        for component_name, creator_func in components_to_setup:
            try:
                # Pass config to components that need it
                if component_name in ["event_handler", "voice_handler", "health_monitor", "message_validator"]:
                    component = await creator_func(bot, config)  # type: ignore[call-arg]
                else:
                    component = await creator_func(bot)  # type: ignore[call-arg]
                if component is not None:
                    self.registry.register(component_name, component)
                    setattr(bot, component_name, component)
                    logger.debug(f"Setup component: {component_name}")
                else:
                    logger.warning(f"Component creator returned None: {component_name}")
            except Exception as e:
                logger.error(f"Failed to setup component {component_name}: {e}")
                raise

        # Setup existing components
        await self._setup_existing_components(bot)

        logger.info("All bot components setup successfully")

    def _create_component(self, import_path: str, class_name: str, *args: Any) -> Any:
        """Generic component creation helper.

        Args:
            import_path: Module path to import from
            class_name: Class name to instantiate
            *args: Arguments to pass to constructor

        Returns:
            Component instance

        """
        module = __import__(import_path, fromlist=[class_name])
        cls = getattr(module, class_name)
        return cls(*args)

    async def _execute_with_logging(self, start_msg: str, operation: Callable[[], Any] | Awaitable[Any], success_msg: str) -> None:
        """
        Run a synchronous or asynchronous operation with standardized start/success logging.

        This helper logs start_msg, executes the provided operation (which may be a callable that returns an awaitable, a coroutine, or a synchronous callable), logs success_msg on completion, and re-raises any exception after logging it.

        Args:
            start_msg: Message logged before executing the operation.
            operation: A callable (sync or returning an awaitable) or an awaitable/coroutine to execute.
            success_msg: Message logged if the operation completes successfully.

        Raises:
            Exception: Any exception raised by the operation is logged and re-raised.

        """
        import inspect

        logger.info(start_msg)
        try:
            if callable(operation):
                result = operation()
                if inspect.isawaitable(result):
                    await result
            else:
                if inspect.isawaitable(operation):
                    await operation
            logger.info(success_msg)
        except Exception as e:
            logger.error(f"Operation failed: {e}")
            raise

    async def _create_event_handler(self, bot: Any, config: Config) -> "EventHandler":
        """Create and return an EventHandler wired with a ConfigManager wrapper."""
        # Lazy import to avoid cycles
        from .config_manager import ConfigManagerImpl

        config_manager = ConfigManagerImpl(config)
        return self._create_component("discord_voice_bot.event_handler", "EventHandler", bot, config_manager)

    # NOTE: Legacy prefix CommandHandler is deprecated in favor of discord.py's
    # built-in commands extension (process_commands / hybrid commands). We keep
    # this method name reserved for backward compatibility, but it is no longer
    # used in setup.
    async def _create_command_handler(self, bot: Any) -> Any:  # pragma: no cover
        return None

    async def _create_slash_command_handler(self, bot: Any) -> Any:
        """
        Create and return a slash command registry (or None if unavailable).

        """
        try:
            return self._create_component("discord_voice_bot.slash.registry", "SlashCommandRegistry", bot)
        except (ImportError, AttributeError):
            logger.warning("Slash command handler not available")
            return None

    async def _create_message_validator(self, bot: Any, config: Config) -> "MessageValidator":
        """Create a MessageValidator using the provided per-bot Config."""
        return self._create_component("discord_voice_bot.message_validator", "MessageValidator", config)

    async def _create_status_manager(self, bot: Any) -> "StatusManager":
        """Create and return a StatusManager instance."""
        return self._create_component("discord_voice_bot.status_manager", "StatusManager")

    async def _create_voice_handler(self, bot: Any, config: Config) -> Any:
        """Create and return the bot's VoiceHandler instance."""
        try:
            return self._create_component("discord_voice_bot.voice.handler", "VoiceHandler", bot, config)
        except Exception as e:
            logger.error(f"Failed to create voice handler: {e}")
            raise

    async def _create_health_monitor(self, bot: Any, config: Config) -> Any:
        """Create and return a HealthMonitor for the given bot."""
        # Lazy imports to avoid cycles
        from .config_manager import ConfigManagerImpl
        from .tts_client import TTSClient

        config_manager = ConfigManagerImpl(config)
        tts_client = TTSClient(config)
        return self._create_component("discord_voice_bot.health_monitor", "HealthMonitor", bot, config_manager, tts_client)

    async def _setup_existing_components(self, bot: Any) -> None:
        """Setup existing components that are already part of the bot.

        Args:
            bot: Bot instance

        """
        # Voice handler should already be initialized in bot constructor
        if hasattr(bot, "voice_handler") and getattr(bot, "voice_handler", None):
            voice_handler = getattr(bot, "voice_handler")
            self.registry.register("voice_handler", voice_handler)
            logger.debug("Registered existing voice_handler component")

        # Health monitor should already be initialized in bot constructor
        if hasattr(bot, "health_monitor") and getattr(bot, "health_monitor", None):
            health_monitor = getattr(bot, "health_monitor")
            self.registry.register("health_monitor", health_monitor)
            logger.debug("Registered existing health_monitor component")

        # Register built-in Cogs (hybrid commands, etc.)
        try:
            from .cogs.status import StatusCommands

            # Avoid double-registration during tests/restarts
            if not any(isinstance(cog, StatusCommands) for cog in bot.cogs.values()):
                await bot.add_cog(StatusCommands(bot))
                logger.debug("Registered StatusCommands cog")
        except Exception as e:
            logger.debug(f"Skipping Cog registration (optional): {e}")

    async def _validate_configuration(self, bot: Any, config: Config) -> None:
        """Validate bot configuration and components."""
        await self._execute_with_logging("Validating bot configuration...", lambda: self._perform_configuration_validation(config), "Bot configuration validation completed successfully")

    def _perform_configuration_validation(self, config: Config) -> None:
        """Perform the actual configuration validation."""
        # The new Config dataclass will handle validation in its creation
        logger.debug("Configuration validation passed")

        # Validate required components
        required_components = ["event_handler", "message_validator", "status_manager"]
        component_requirements = {"event_handler": ["handle_ready"], "message_validator": ["validate_message"], "status_manager": ["record_command_usage"]}

        for component_name in required_components:
            component = self.registry.get(component_name)
            if not component:
                raise RuntimeError(f"Required component missing: {component_name}")

            # Check required methods
            if component_name in component_requirements:
                for method_name in component_requirements[component_name]:
                    if not hasattr(component, method_name):
                        raise RuntimeError(f"Component {component_name} missing required method: {method_name}")

    async def initialize_services(self, bot: Any) -> None:
        """
        Initialize external services required by the bot.

        This attaches a started Text-to-Speech engine to `bot.tts_engine`, and starts optional components found on the bot:
        - voice_handler (awaits its `start()` coroutine)
        - health_monitor (awaits its `start()` coroutine)

        Raises:
            RuntimeError: If the bot does not expose a valid `Config` dataclass instance.
            Exception: Propagates any exception raised while creating or starting the services.

        """
        logger.info("Initializing external services...")

        try:
            # Initialize TTS engine
            from .tts_engine import get_tts_engine

            # Use the bot's underlying Config dataclass
            raw_cfg: Any = getattr(bot, "config", None)
            cfg: Any = raw_cfg() if callable(raw_cfg) else raw_cfg
            if not isinstance(cfg, Config):
                raise RuntimeError("Bot is missing a valid Config instance")
            tts_engine = await get_tts_engine(cfg)  # already started inside factory
            bot.tts_engine = tts_engine
            logger.debug("TTS engine initialized")

            # Initialize voice handler
            if hasattr(bot, "voice_handler") and getattr(bot, "voice_handler", None):
                voice_handler = getattr(bot, "voice_handler")
                await voice_handler.start()
                logger.debug("Voice handler initialized")

            # Start health monitor
            if hasattr(bot, "health_monitor") and getattr(bot, "health_monitor", None):
                health_monitor = getattr(bot, "health_monitor")
                await health_monitor.start()
                logger.debug("Health monitor initialized")

            logger.info("External services initialization completed")

        except Exception as e:
            logger.error(f"Failed to initialize services: {e}")
            raise

    def get_component_info(self) -> dict[str, Any]:
        """Get information about registered components.

        Returns:
            Dictionary with component information

        """
        info: dict[str, Any] = {}
        for name, component in self.registry.get_all().items():
            info[name] = {"type": type(component).__name__, "methods": [method for method in dir(component) if not method.startswith("_")], "status": "active" if component else "inactive"}
        return info

    def get_initialization_status(self, bot: Any) -> dict[str, Any]:
        """Get comprehensive initialization status.

        Args:
            bot: Bot instance

        Returns:
            Dictionary with initialization status

        """
        status: dict[str, Any] = {"bot_configured": False, "components_registered": len(self.registry.get_all()), "services_initialized": False, "component_status": {}, "errors": []}

        # Check bot configuration
        if hasattr(bot, "config") and bot.config:
            status["bot_configured"] = True

        # Check component status
        for name, component in self.registry.get_all().items():
            status["component_status"][name] = {"initialized": component is not None, "type": type(component).__name__ if component else None}

        # Check service initialization
        services_initialized = True
        try:
            # TTS engine is now created per instance, so we can't check global state
            # Assume it's initialized if no errors occurred during creation
            pass
        except Exception as e:
            services_initialized = False
            status["errors"].append(f"TTS engine error: {e}")

        status["services_initialized"] = services_initialized

        return status

    async def shutdown_bot(self, bot: Any) -> None:
        """
        Shut down the given bot and clean up all managed resources.

        Performs an orderly, best-effort shutdown:
        - Invokes component-specific stop/cleanup/shutdown methods in a fixed reverse order:
          health_monitor, voice_handler, status_manager, message_validator, slash_handler,
          command_handler, event_handler.
        - Swallows and logs exceptions from individual components so shutdown proceeds.
        - Clears the internal component registry.
        - If the bot has a `tts_engine` attribute with a `close` coroutine, awaits it to close the engine.

        Args:
            bot: The bot instance to shut down. May be used to locate the attached TTS engine as
                `bot.tts_engine`; otherwise only the factory's component registry is acted on.

        """
        logger.info("Starting bot shutdown...")

        # Shutdown components in reverse order
        shutdown_order = [
            "health_monitor",
            "voice_handler",
            "status_manager",
            "message_validator",
            "slash_handler",
            "command_handler",
            "event_handler",
        ]

        for component_name in shutdown_order:
            component = self.registry.get(component_name)
            if component:
                try:
                    if component_name == "voice_handler" and hasattr(component, "cleanup"):
                        await component.cleanup()
                    elif component_name == "health_monitor" and hasattr(component, "stop"):
                        await component.stop()
                    elif hasattr(component, "shutdown"):
                        await component.shutdown()
                    logger.debug(f"Shutdown component: {component_name}")
                except Exception as e:
                    logger.error(f"Error shutting down {component_name}: {e}")

        # Clear registry
        self.registry.clear()

        # Stop TTS engine if attached to the bot
        try:
            tts_engine = getattr(bot, "tts_engine", None)
            if tts_engine is not None and hasattr(tts_engine, "close"):
                await tts_engine.close()
                logger.debug("Shutdown TTS engine")
        except Exception as e:
            logger.warning(f"Error shutting down TTS engine: {e}")

        logger.info("Bot shutdown completed")

    def reset_factory(self) -> None:
        """
        Reset the factory to its initial state by clearing all registered components.

        This removes every component from the internal ComponentRegistry. It does not stop or shut down any components — callers should perform graceful shutdown of components before calling this method if required.
        """
        self.registry.clear()
        logger.info("Bot factory reset")
