"""Slash command registry for Discord Voice TTS Bot."""

from typing import Any

import discord
from discord.ext import commands
from loguru import logger

# Lazy import handlers to avoid circular import
# NOTE: Legacy per-command handler imports have been removed in favor of
# hybrid Cog implementations. This module now avoids dynamic imports.


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
            _ = [c for c in self.bot.tree.get_commands() if c.name == "status"]
        except Exception:
            pass
        # If not existing, rely on Cog-based hybrid command (no-op here)

        # Skip command (skip if exists)
        try:
            _ = any(c.name == "skip" for c in self.bot.tree.get_commands())
        except Exception:
            pass
        # no-op if not exists; provided by Cog

        # Clear command (skip if exists)
        try:
            _ = any(c.name == "clear" for c in self.bot.tree.get_commands())
        except Exception:
            pass
        # no-op if not exists; provided by Cog

    async def _register_voice(self) -> None:
        """Register voice-related commands."""
        # Voice command with autocomplete (skip if exists)
        try:
            _ = any(c.name == "voice" for c in self.bot.tree.get_commands())
        except Exception:
            pass
        # no-op; hybrid Cog provides this

        # Voices command (skip if exists)
        try:
            _ = any(c.name == "voices" for c in self.bot.tree.get_commands())
        except Exception:
            pass
        # no-op; hybrid Cog provides this

        # Voice check command (skip if exists)
        try:
            _ = any(c.name == "voicecheck" for c in self.bot.tree.get_commands())
        except Exception:
            pass
        # no-op; hybrid Cog provides this

        # Reconnect command (skip if exists)
        try:
            _ = any(c.name == "reconnect" for c in self.bot.tree.get_commands())
        except Exception:
            pass
        # no-op; hybrid Cog provides this

    async def _register_util(self) -> None:
        """Register utility commands."""
        # Test command (skip if exists)
        try:
            _ = any(c.name == "test" for c in self.bot.tree.get_commands())
        except Exception:
            pass
        # no-op; hybrid Cog provides this

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
