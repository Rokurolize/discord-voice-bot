"""Slash command registry for Discord Voice TTS Bot."""

from typing import Any

import discord
from discord import app_commands
from discord.ext import commands
from loguru import logger

# TYPE_CHECKING import removed to avoid circular import
from .autocomplete.voice import voice_autocomplete


# Lazy import handlers to avoid circular import
def _get_handler(name: str):
    """Get handler function by name."""
    handlers = {"clear": "clear", "reconnect": "reconnect", "skip": "skip", "status": "status", "test_tts": "test_tts", "voice": "voice", "voicecheck": "voicecheck", "voices": "voices"}
    if name not in handlers:
        raise ValueError(f"Unknown handler: {name}")

    # Import the handler module
    module_name = f".handlers.{handlers[name]}"
    import importlib

    module = importlib.import_module(module_name, package=__name__.rpartition(".")[0])
    return module.handle


class SlashCommandRegistry:
    """Thin orchestrator for slash command registration and sync.

    This class intentionally keeps minimal internal state and relies on
    discord.py's CommandTree as the source of truth. The `_registered`
    mapping is retained only for test visibility and backward compatibility.
    """

    def __init__(self, bot: commands.Bot):
        """Initialize slash command registry.

        Args:
            bot: The Discord bot instance

        """
        super().__init__()
        self.bot = bot
        # Back-compat minimal registry used by tests; real state lives in bot.tree
        self._registered: dict[str, dict[str, Any]] = {}
        logger.info("Slash command registry initialized")

    async def register_slash_commands(self) -> None:
        """Register all slash commands with Discord."""
        try:
            logger.info("🔧 Registering slash commands...")

            # Clear existing commands to avoid conflicts
            self.bot.tree.clear_commands(guild=None)

            # Register core commands
            await self._register_core()

            # Register voice commands
            await self._register_voice()

            # Register utility commands
            await self._register_util()

            # Sync with Discord
            await self._sync()

            logger.info(f"✅ Successfully registered {len(self._registered)} slash commands")

        except Exception as e:
            logger.error(f"❌ Failed to register slash commands: {e}")
            raise

    async def _register_core(self) -> None:
        """Register core bot commands."""
        # Status command (skip if already provided by a hybrid Cog)
        try:
            existing = [c for c in self.bot.tree.get_commands() if c.name == "status"]
        except Exception:
            existing = []
        if not existing:
            status_handler = _get_handler("status")
            self._registered["status"] = {"handler": status_handler}

            @self.bot.tree.command(name="status", description="Show bot status and statistics")
            async def _status_slash(interaction: discord.Interaction):  # type: ignore[reportUnusedFunction]
                """Show bot status via slash command."""
                await status_handler(interaction, self.bot)

        # Skip command (skip if exists)
        try:
            exists = any(c.name == "skip" for c in self.bot.tree.get_commands())
        except Exception:
            exists = False
        if not exists:
            @self.bot.tree.command(name="skip", description="Skip current TTS playback")
            async def _skip_slash(interaction: discord.Interaction):  # type: ignore[reportUnusedFunction]
                """Skip current TTS playback via slash command."""
                await _get_handler("skip")(interaction, self.bot)

            self._registered["skip"] = {"handler": _get_handler("skip")}

        # Clear command (skip if exists)
        try:
            exists = any(c.name == "clear" for c in self.bot.tree.get_commands())
        except Exception:
            exists = False
        if not exists:
            @self.bot.tree.command(name="clear", description="Clear TTS queue")
            async def _clear_slash(interaction: discord.Interaction):  # type: ignore[reportUnusedFunction]
                """Clear TTS queue via slash command."""
                await _get_handler("clear")(interaction, self.bot)

            self._registered["clear"] = {"handler": _get_handler("clear")}

    async def _register_voice(self) -> None:
        """Register voice-related commands."""
        # Voice command with autocomplete (skip if exists)
        try:
            exists = any(c.name == "voice" for c in self.bot.tree.get_commands())
        except Exception:
            exists = False
        if not exists:
            @self.bot.tree.command(name="voice", description="Set or show personal voice preference")
            @app_commands.autocomplete(speaker=voice_autocomplete)
            async def _voice_slash(interaction: discord.Interaction, speaker: str | None = None):  # type: ignore[reportUnusedFunction]
                """Set or show personal voice preference via slash command."""
                await _get_handler("voice")(interaction, self.bot, speaker)

            self._registered["voice"] = {"handler": _get_handler("voice"), "autocomplete": voice_autocomplete}

        # Voices command (skip if exists)
        try:
            exists = any(c.name == "voices" for c in self.bot.tree.get_commands())
        except Exception:
            exists = False
        if not exists:
            @self.bot.tree.command(name="voices", description="List all available voices")
            async def _voices_slash(interaction: discord.Interaction):  # type: ignore[reportUnusedFunction]
                """List all available voices via slash command."""
                await _get_handler("voices")(interaction, self.bot)

            self._registered["voices"] = {"handler": _get_handler("voices")}

        # Voice check command (skip if exists)
        try:
            exists = any(c.name == "voicecheck" for c in self.bot.tree.get_commands())
        except Exception:
            exists = False
        if not exists:
            @self.bot.tree.command(name="voicecheck", description="Perform voice connection health check")
            async def _voicecheck_slash(interaction: discord.Interaction):  # type: ignore[reportUnusedFunction]
                """Perform voice connection health check via slash command."""
                await _get_handler("voicecheck")(interaction, self.bot)

            self._registered["voicecheck"] = {"handler": _get_handler("voicecheck")}

        # Reconnect command (skip if exists)
        try:
            exists = any(c.name == "reconnect" for c in self.bot.tree.get_commands())
        except Exception:
            exists = False
        if not exists:
            @self.bot.tree.command(name="reconnect", description="Manually attempt to reconnect to voice channel")
            async def _reconnect_slash(interaction: discord.Interaction):  # type: ignore[reportUnusedFunction]
                """Manually attempt to reconnect to voice channel via slash command."""
                await _get_handler("reconnect")(interaction, self.bot)

            self._registered["reconnect"] = {"handler": _get_handler("reconnect")}

    async def _register_util(self) -> None:
        """Register utility commands."""
        # Test command (skip if exists)
        try:
            exists = any(c.name == "test" for c in self.bot.tree.get_commands())
        except Exception:
            exists = False
        if not exists:
            @self.bot.tree.command(name="test", description="Test TTS with custom text")
            @app_commands.describe(text="Text to convert to speech")
            async def _test_slash(interaction: discord.Interaction, text: str = "テストメッセージです"):  # type: ignore[reportUnusedFunction]
                """Test TTS with custom text via slash command."""
                await _get_handler("test_tts")(interaction, self.bot, text)

            self._registered["test"] = {"handler": _get_handler("test_tts")}

    async def _sync(self, guild: discord.Guild | None = None) -> None:
        """Sync slash commands with Discord.

        Args:
            guild: Optional guild to sync commands to (for testing)

        """
        try:
            logger.info("🔧 Syncing slash commands with Discord...")

            # First try syncing globally
            synced = await self.bot.tree.sync(guild=guild)
            logger.info(f"✅ Successfully synced {len(synced)} slash commands with Discord")

            # Log the synced commands for debugging
            for cmd in synced:
                logger.debug(f"  - Synced command: /{cmd.name} - {cmd.description}")

        except discord.Forbidden:
            logger.error("❌ Missing permissions to sync slash commands")
            raise
        except discord.HTTPException as e:
            logger.error(f"❌ HTTP error during slash command sync: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Failed to sync slash commands: {e}")
            raise

    def get_registered_commands(self) -> dict[str, dict[str, Any]]:
        """Get information about registered slash commands.

        Returns a merged view of commands discovered from CommandTree and the
        minimal compatibility mapping tracked locally.
        """
        try:
            tree_cmds = {c.name: {"handler": None} for c in self.bot.tree.get_commands()}
        except Exception:
            tree_cmds = {}
        merged = {**tree_cmds, **self._registered}
        return merged

    def clear_commands(self) -> None:
        """Clear all registered slash commands."""
        self._registered.clear()
        logger.info("Cleared all slash commands")

    async def shutdown(self) -> None:
        """Shutdown slash command registry."""
        logger.info("Slash command registry shutting down")
        self.clear_commands()
