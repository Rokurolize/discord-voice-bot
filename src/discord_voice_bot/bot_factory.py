"""Bot factory for Discord Voice TTS Bot initialization and configuration."""

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any, cast

from loguru import logger

from .config import Config

if TYPE_CHECKING:
    from .command_handler import CommandHandler
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

    async def create_bot(self, config: Config, bot_class: type[Any] | None = None) -> Any:
        """Create and configure a new bot instance.

        Args:
            config: Configuration object
            bot_class: Bot class to instantiate (defaults to DiscordVoiceTTSBot)

        Returns:
            Configured bot instance

        """
        try:
            # Import here to avoid circular imports
            if bot_class is None:
                # Use TYPE_CHECKING to avoid runtime import
                import importlib

                bot_module = importlib.import_module(".bot", package="discord_voice_bot")
                bot_class = bot_module.DiscordVoiceTTSBot

            # Create bot instance with configuration (direct dataclass injection)
            if bot_class is None:
                raise ValueError("Bot class cannot be None")
            bot: Any = bot_class(config=config)

            # Setup all components with config
            await self._setup_components(bot, config)

            # Validate configuration
            await self._validate_configuration(bot, config)

            logger.info("Bot instance created and configured successfully")
            return bot

        except Exception as e:
            logger.error(f"Failed to create bot instance: {e}")
            raise

    async def _setup_components(self, bot: Any, config: Config) -> None:
        """Setup all bot components.

        Args:
            bot: Bot instance to setup components for
            config: Configuration object used by components during initialization.

        """
        logger.info("Setting up bot components...")

        # Create and register components
        components_to_setup = [
            ("event_handler", self._create_event_handler),
            ("command_handler", self._create_command_handler),
            ("slash_handler", self._create_slash_command_handler),
            ("message_validator", self._create_message_validator),
            ("status_manager", self._create_status_manager),
            ("voice_handler", self._create_voice_handler),
            ("health_monitor", self._create_health_monitor),
        ]

        for component_name, creator_func in components_to_setup:
            try:
                # Pass config to components that need it
                if component_name in ["event_handler", "voice_handler", "health_monitor"]:
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
        """Execute operation with standardized logging.

        Args:
            start_msg: Message to log at start
            operation: Function or coroutine to execute
            success_msg: Message to log on success

        """
        """Execute operation with standardized logging.

        Args:
            start_msg: Message to log at start
            operation: Function or coroutine to execute
            success_msg: Message to log on success

        """
        logger.info(start_msg)
        try:
            if callable(operation):
                result = operation()
                if hasattr(result, "__await__"):
                    await result
            else:
                if hasattr(operation, "__await__"):
                    await operation
            logger.info(success_msg)
        except Exception as e:
            logger.error(f"Operation failed: {e}")
            raise

    async def _create_event_handler(self, bot: Any, config: Config) -> "EventHandler":
        """Create event handler using a ConfigManager wrapper around Config."""
        # Lazy import to avoid cycles
        from .config_manager import ConfigManagerImpl

        config_manager = ConfigManagerImpl(config)
        return self._create_component("discord_voice_bot.event_handler", "EventHandler", bot, config_manager)

    async def _create_command_handler(self, bot: Any) -> "CommandHandler":
        """Create command handler."""
        return self._create_component("discord_voice_bot.command_handler", "CommandHandler", bot)

    async def _create_slash_command_handler(self, bot: Any) -> Any:
        """Create slash command handler."""
        try:
            return self._create_component("discord_voice_bot.slash.registry", "SlashCommandRegistry", bot)
        except (ImportError, AttributeError):
            logger.warning("Slash command handler not available")
            return None

    async def _create_message_validator(self, bot: Any) -> "MessageValidator":
        """Create message validator with Config dataclass injection."""
        # The validator requires the concrete Config dataclass
        cfg = bot.config if hasattr(bot, "config") else None
        return self._create_component("discord_voice_bot.message_validator", "MessageValidator", cfg)

    async def _create_status_manager(self, bot: Any) -> "StatusManager":
        """Create status manager."""
        return self._create_component("discord_voice_bot.status_manager", "StatusManager")

    async def _create_voice_handler(self, bot: Any, config: Config) -> Any:
        """Create voice handler."""
        try:
            return self._create_component("discord_voice_bot.voice.handler", "VoiceHandler", bot, config)
        except Exception as e:
            logger.error(f"Failed to create voice handler: {e}")
            raise

    async def _create_health_monitor(self, bot: Any, config: Config) -> Any:
        """Create health monitor with ConfigManager and TTS client."""
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

    async def _validate_configuration(self, bot: Any, config: Config) -> None:
        """Validate bot configuration and components."""
        await self._execute_with_logging("Validating bot configuration...", lambda: self._perform_configuration_validation(config), "Bot configuration validation completed successfully")

    def _perform_configuration_validation(self, config: Config) -> None:
        """Perform the actual configuration validation."""
        # The new Config dataclass will handle validation in its creation
        logger.debug("Configuration validation passed")

        # Validate required components
        required_components = ["event_handler", "command_handler", "message_validator", "status_manager"]
        component_requirements = {"command_handler": ["process_command"], "event_handler": ["handle_ready"], "message_validator": ["validate_message"], "status_manager": ["record_command_usage"]}

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
        """Initialize external services and dependencies.

        Args:
            bot: Bot instance

        """
        logger.info("Initializing external services...")

        try:
            # Initialize TTS engine
            from .tts_engine import get_tts_engine

            # Use the bot's underlying Config dataclass
            cfg = cast(Config, getattr(bot, "config", None))
            tts_engine = await get_tts_engine(cfg)
            await tts_engine.start()
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
        """Gracefully shutdown bot and cleanup resources.

        Args:
            bot: Bot instance to shutdown

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

        logger.info("Bot shutdown completed")

    def reset_factory(self) -> None:
        """Reset factory to initial state."""
        self.registry.clear()
        logger.info("Bot factory reset")
