"""Command handling for Discord Voice TTS Bot."""

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

import discord
from discord.ext import commands
from loguru import logger

from .protocols import HasStatusManager

if TYPE_CHECKING:
    pass


class CommandHandler:
    """Handles prefix-based commands with registration and execution."""

    def __init__(self, bot: HasStatusManager):
        """Initialize command handler.

        Args:
            bot: The Discord bot instance with status manager

        """
        super().__init__()
        self.bot = bot
        self._commands: dict[str, dict[str, Any]] = {}
        logger.info("Command handler initialized")

    def register_command(self, name: str, func: Callable[..., Any], aliases: list[str] | None = None, help_text: str = "", usage: str = "", permissions: list[str] | None = None) -> None:
        """Register a new command.

        Args:
            name: Command name
            func: Command function
            aliases: Optional list of command aliases
            help_text: Help description for the command
            usage: Usage instructions
            permissions: Required permissions

        """
        self._commands[name] = {
            "func": func,
            "aliases": aliases or [],
            "help_text": help_text,
            "usage": usage,
            "permissions": permissions or [],
        }
        logger.info(f"Registered command: {name}")

        # Register aliases
        for alias in self._commands[name]["aliases"]:
            self._commands[alias] = {"alias_for": name}

    async def process_command(self, message: discord.Message) -> bool:
        """Process a command message.

        Args:
            message: Discord message containing command

        Returns:
            True if command was processed, False otherwise

        """
        command_name = "<unknown>"  # Initialize for error handling
        try:
            # Extract command and arguments
            content = message.content.strip()
            prefix = str(self.bot.command_prefix)  # type: ignore[arg-type]
            if not content.startswith(prefix):
                return False

            # Remove command prefix
            content = content[len(prefix) :].strip()
            if not content:
                return False

            # Split command and arguments
            parts = content.split()
            if not parts:
                return False

            command_name = parts[0].lower()
            args = parts[1:]

            # Find command
            command = self._commands.get(command_name)
            if not command:
                return False

            # Handle aliases
            if "alias_for" in command:
                command_name = command["alias_for"]
                command = self._commands[command_name]

            # Execute command
            command_func = command["func"]

            # Create a mock context for the command
            ctx = await self._create_context(message, command_name, args)

            # Execute the command
            if command_func:
                await command_func(ctx, *args)

            # Update command statistics
            try:
                status_manager = self.bot.status_manager
                if status_manager and hasattr(status_manager, "record_command_usage"):
                    _ = status_manager.record_command_usage(command_name)
            except AttributeError:
                # Status manager not available, ignore
                pass

            logger.debug(f"Executed command: {command_name}")
            return True

        except Exception as e:
            logger.error(f"Error processing command '{command_name}': {e}")
            return False

    async def _create_context(self, message: discord.Message, command_name: str, args: list[str]) -> commands.Context[Any]:
        """Create a command context for the message.

        Args:
            message: Original Discord message
            command_name: Name of the command
            args: Command arguments

        Returns:
            Command context

        """
        # Create a mock context object
        ctx = type(
            "Context",
            (),
            {
                "message": message,
                "author": message.author,
                "guild": message.guild,
                "channel": message.channel,
                "bot": self.bot,
                "command": type("Command", (), {"name": command_name}),
                "args": args,
                "send": self._create_send_func(message),
                "reply": self._create_reply_func(message),
            },
        )()

        return ctx  # type: ignore[return-value]

    def _create_send_func(self, message: discord.Message) -> Callable[..., Any]:
        """Create a send function for the context."""

        async def send(content: Any = None, **kwargs: Any) -> Any:
            return await message.channel.send(content, **kwargs)

        return send

    def _create_reply_func(self, message: discord.Message) -> Callable[..., Any]:
        """Create a reply function for the context."""

        async def reply(content: Any = None, **kwargs: Any) -> Any:
            return await message.reply(content, **kwargs)

        return reply

    def get_command_help(self, command_name: str) -> str:
        """Get help text for a command.

        Args:
            command_name: Name of the command

        Returns:
            Help text for the command

        """
        command = self._commands.get(command_name)
        if not command or "alias_for" in command:
            return f"Command '{command_name}' not found."

        help_text = command.get("help_text", "No help available")
        usage = command.get("usage", "")

        if usage:
            prefix = str(self.bot.command_prefix)  # type: ignore[arg-type]
            help_text += f"\nUsage: {prefix}{command_name} {usage}"

        return help_text

    def list_commands(self) -> list[str]:
        """List all available commands.

        Returns:
            List of command names (excluding aliases)

        """
        return [name for name, cmd in self._commands.items() if "alias_for" not in cmd]

    def get_command_info(self, command_name: str) -> dict[str, Any] | None:
        """Get detailed information about a command.

        Args:
            command_name: Name of the command

        Returns:
            Dictionary with command information, or None if not found

        """
        command = self._commands.get(command_name)
        if not command or "alias_for" in command:
            return None

        return {
            "name": command_name,
            "aliases": command.get("aliases", []),
            "help_text": command.get("help_text", ""),
            "usage": command.get("usage", ""),
            "permissions": command.get("permissions", []),
        }

    def unregister_command(self, name: str) -> bool:
        """Unregister a command.

        Args:
            name: Command name to unregister

        Returns:
            True if command was unregistered, False otherwise

        """
        if name not in self._commands:
            return False

        # Remove command and its aliases
        command = self._commands[name]
        if "alias_for" not in command:  # Not an alias
            aliases = command.get("aliases", [])
            for alias in aliases:
                if alias in self._commands:
                    del self._commands[alias]

        del self._commands[name]
        logger.info(f"Unregistered command: {name}")
        return True

    def clear_commands(self) -> None:
        """Clear all registered commands."""
        self._commands.clear()
        logger.info("Cleared all commands")

    def has_command(self, name: str) -> bool:
        """Check if a command exists.

        Args:
            name: Command name to check

        Returns:
            True if command exists, False otherwise

        """
        return name in self._commands and "alias_for" not in self._commands[name]
