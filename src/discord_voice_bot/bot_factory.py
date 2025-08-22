"""Bot factory for Discord Voice TTS Bot initialization and configuration."""

import asyncio
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Type

import discord
from discord.ext import commands
from loguru import logger

from .config import config

if TYPE_CHECKING:
    from .bot import DiscordVoiceTTSBot
    from .command_handler import CommandHandler
    from .event_handler import EventHandler
    from .message_validator import MessageValidator
    from .slash_command_handler import SlashCommandHandler
    from .status_manager import StatusManager


class ComponentRegistry:
    """Registry for managing bot components."""

    def __init__(self) -> None:
        """Initialize component registry."""
        self._components: Dict[str, Any] = {}

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

    def get_all(self) -> Dict[str, Any]:
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
        self.registry = ComponentRegistry()
        logger.info("Bot factory initialized")

    async def create_bot(self, bot_class: Type["DiscordVoiceTTSBot"] = None) -> "DiscordVoiceTTSBot":
        """Create and configure a new bot instance.

        Args:
            bot_class: Bot class to instantiate (defaults to DiscordVoiceTTSBot)

        Returns:
            Configured bot instance
        """
        try:
            # Import here to avoid circular imports
            if bot_class is None:
                from .bot import DiscordVoiceTTSBot

                bot_class = DiscordVoiceTTSBot

            # Create bot instance (current constructor doesn't take config parameter)
            bot = bot_class()

            # Setup all components with config
            await self._setup_components(bot, config)

            # Validate configuration
            await self._validate_configuration(bot)

            logger.info("Bot instance created and configured successfully")
            return bot

        except Exception as e:
            logger.error(f"Failed to create bot instance: {e}")
            raise

    async def _setup_components(self, bot: "DiscordVoiceTTSBot", config: Any) -> None:
        """Setup all bot components.

        Args:
            bot: Bot instance to setup components for
        """
        logger.info("Setting up bot components...")

        # Create and register components
        components_to_setup = [
            ("event_handler", self._create_event_handler),
            ("command_handler", self._create_command_handler),
            ("slash_handler", self._create_slash_command_handler),
            ("message_validator", self._create_message_validator),
            ("status_manager", self._create_status_manager),
        ]

        for component_name, creator_func in components_to_setup:
            try:
                component = await creator_func(bot)
                if component:
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

    async def _create_event_handler(self, bot: "DiscordVoiceTTSBot") -> "EventHandler":
        """Create event handler.

        Args:
            bot: Bot instance

        Returns:
            Configured event handler
        """
        from .event_handler import EventHandler

        return EventHandler(bot)

    async def _create_command_handler(self, bot: "DiscordVoiceTTSBot") -> "CommandHandler":
        """Create command handler.

        Args:
            bot: Bot instance

        Returns:
            Configured command handler
        """
        from .command_handler import CommandHandler

        return CommandHandler(bot)

    async def _create_slash_command_handler(self, bot: "DiscordVoiceTTSBot") -> Optional["SlashCommandHandler"]:
        """Create slash command handler.

        Args:
            bot: Bot instance

        Returns:
            Configured slash command handler or None if not available
        """
        try:
            from .slash_command_handler import SlashCommandHandler

            return SlashCommandHandler(bot)
        except ImportError:
            logger.warning("Slash command handler not available")
            return None

    async def _create_message_validator(self, bot: "DiscordVoiceTTSBot") -> "MessageValidator":
        """Create message validator.

        Args:
            bot: Bot instance

        Returns:
            Configured message validator
        """
        from .message_validator import MessageValidator

        return MessageValidator()

    async def _create_status_manager(self, bot: "DiscordVoiceTTSBot") -> "StatusManager":
        """Create status manager.

        Args:
            bot: Bot instance

        Returns:
            Configured status manager
        """
        from .status_manager import StatusManager

        return StatusManager()

    async def _setup_existing_components(self, bot: "DiscordVoiceTTSBot") -> None:
        """Setup existing components that are already part of the bot.

        Args:
            bot: Bot instance
        """
        # Voice handler should already be initialized in bot constructor
        if hasattr(bot, "voice_handler") and bot.voice_handler:
            self.registry.register("voice_handler", bot.voice_handler)
            logger.debug("Registered existing voice_handler component")

        # Health monitor should already be initialized in bot constructor
        if hasattr(bot, "health_monitor") and bot.health_monitor:
            self.registry.register("health_monitor", bot.health_monitor)
            logger.debug("Registered existing health_monitor component")

    async def _validate_configuration(self, bot: "DiscordVoiceTTSBot") -> None:
        """Validate bot configuration and components.

        Args:
            bot: Bot instance to validate

        Raises:
            ValueError: If configuration is invalid
            RuntimeError: If required components are missing
        """
        logger.info("Validating bot configuration...")

        # Validate config
        try:
            config.validate()
            logger.debug("Configuration validation passed")
        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            raise

        # Validate required components
        required_components = ["event_handler", "command_handler", "message_validator", "status_manager"]

        for component_name in required_components:
            component = self.registry.get(component_name)
            if not component:
                raise RuntimeError(f"Required component missing: {component_name}")

            # Additional component-specific validation
            if component_name == "command_handler":
                if not hasattr(component, "process_command"):
                    raise RuntimeError(f"Component {component_name} missing required method: process_command")

            elif component_name == "event_handler":
                if not hasattr(component, "handle_ready"):
                    raise RuntimeError(f"Component {component_name} missing required method: handle_ready")

            elif component_name == "message_validator":
                if not hasattr(component, "validate_message"):
                    raise RuntimeError(f"Component {component_name} missing required method: validate_message")

            elif component_name == "status_manager":
                if not hasattr(component, "record_command_usage"):
                    raise RuntimeError(f"Component {component_name} missing required method: record_command_usage")

        logger.info("Bot configuration validation completed successfully")

    async def initialize_services(self, bot: "DiscordVoiceTTSBot") -> None:
        """Initialize external services and dependencies.

        Args:
            bot: Bot instance
        """
        logger.info("Initializing external services...")

        try:
            # Initialize TTS engine
            from .tts_engine import tts_engine

            await tts_engine.start()
            logger.debug("TTS engine initialized")

            # Initialize voice handler
            if hasattr(bot, "voice_handler") and bot.voice_handler:
                await bot.voice_handler.start()
                logger.debug("Voice handler initialized")

            # Start health monitor
            if hasattr(bot, "health_monitor") and bot.health_monitor:
                await bot.health_monitor.start()
                logger.debug("Health monitor initialized")

            logger.info("External services initialization completed")

        except Exception as e:
            logger.error(f"Failed to initialize services: {e}")
            raise

    def get_component_info(self) -> Dict[str, Any]:
        """Get information about registered components.

        Returns:
            Dictionary with component information
        """
        info = {}
        for name, component in self.registry.get_all().items():
            info[name] = {"type": type(component).__name__, "methods": [method for method in dir(component) if not method.startswith("_")], "status": "active" if component else "inactive"}
        return info

    def get_initialization_status(self, bot: "DiscordVoiceTTSBot") -> Dict[str, Any]:
        """Get comprehensive initialization status.

        Args:
            bot: Bot instance

        Returns:
            Dictionary with initialization status
        """
        status = {"bot_configured": False, "components_registered": len(self.registry.get_all()), "services_initialized": False, "component_status": {}, "errors": []}

        # Check bot configuration
        if hasattr(bot, "config") and bot.config:
            status["bot_configured"] = True

        # Check component status
        for name, component in self.registry.get_all().items():
            status["component_status"][name] = {"initialized": component is not None, "type": type(component).__name__ if component else None}

        # Check service initialization
        services_initialized = True
        try:
            from .tts_engine import tts_engine

            if not hasattr(tts_engine, "_initialized") or not tts_engine._initialized:
                services_initialized = False
                status["errors"].append("TTS engine not initialized")
        except Exception as e:
            services_initialized = False
            status["errors"].append(f"TTS engine error: {e}")

        status["services_initialized"] = services_initialized

        return status

    async def shutdown_bot(self, bot: "DiscordVoiceTTSBot") -> None:
        """Gracefully shutdown bot and cleanup resources.

        Args:
            bot: Bot instance to shutdown
        """
        logger.info("Starting bot shutdown...")

        # Shutdown components in reverse order
        shutdown_order = ["status_manager", "message_validator", "slash_handler", "command_handler", "event_handler"]

        for component_name in shutdown_order:
            component = self.registry.get(component_name)
            if component and hasattr(component, "shutdown"):
                try:
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
