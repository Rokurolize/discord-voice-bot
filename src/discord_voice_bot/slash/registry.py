"""Slash command registry for Discord Voice TTS Bot."""

from typing import TYPE_CHECKING, Any, Optional

import discord
from discord import app_commands
from loguru import logger

if TYPE_CHECKING:
    from ..bot import DiscordVoiceTTSBot

from .autocomplete.voice import voice_autocomplete
from .handlers import clear, reconnect, skip, status, test_tts, voice, voicecheck, voices


class SlashCommandRegistry:
    """Manages Discord slash command registration and synchronization."""

    def __init__(self, bot: "DiscordVoiceTTSBot"):
        """Initialize slash command registry.

        Args:
            bot: The Discord bot instance

        """
        self.bot = bot
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

        # Status command
        @self.bot.tree.command(name="status", description="Show bot status and statistics")
        async def status_slash(interaction: discord.Interaction):
            """Show bot status via slash command."""
            await status.handle(interaction, self.bot)

        self._registered["status"] = {"handler": status.handle}

        # Skip command
        @self.bot.tree.command(name="skip", description="Skip current TTS playback")
        async def skip_slash(interaction: discord.Interaction):
            """Skip current TTS playback via slash command."""
            await skip.handle(interaction, self.bot)

        self._registered["skip"] = {"handler": skip.handle}

        # Clear command
        @self.bot.tree.command(name="clear", description="Clear TTS queue")
        async def clear_slash(interaction: discord.Interaction):
            """Clear TTS queue via slash command."""
            await clear.handle(interaction, self.bot)

        self._registered["clear"] = {"handler": clear.handle}

    async def _register_voice(self) -> None:
        """Register voice-related commands."""

        # Voice command with autocomplete
        @self.bot.tree.command(name="voice", description="Set or show personal voice preference")
        @app_commands.autocomplete(speaker=voice_autocomplete)
        async def voice_slash(interaction: discord.Interaction, speaker: Optional[str] = None):
            """Set or show personal voice preference via slash command."""
            await voice.handle(interaction, self.bot, speaker)

        self._registered["voice"] = {"handler": voice.handle, "autocomplete": voice_autocomplete}

        # Voices command
        @self.bot.tree.command(name="voices", description="List all available voices")
        async def voices_slash(interaction: discord.Interaction):
            """List all available voices via slash command."""
            await voices.handle(interaction, self.bot)

        self._registered["voices"] = {"handler": voices.handle}

        # Voice check command
        @self.bot.tree.command(name="voicecheck", description="Perform voice connection health check")
        async def voicecheck_slash(interaction: discord.Interaction):
            """Perform voice connection health check via slash command."""
            await voicecheck.handle(interaction, self.bot)

        self._registered["voicecheck"] = {"handler": voicecheck.handle}

        # Reconnect command
        @self.bot.tree.command(name="reconnect", description="Manually attempt to reconnect to voice channel")
        async def reconnect_slash(interaction: discord.Interaction):
            """Manually attempt to reconnect to voice channel via slash command."""
            await reconnect.handle(interaction, self.bot)

        self._registered["reconnect"] = {"handler": reconnect.handle}

    async def _register_util(self) -> None:
        """Register utility commands."""

        # Test command
        @self.bot.tree.command(name="test", description="Test TTS with custom text")
        @app_commands.describe(text="Text to convert to speech")
        async def test_slash(interaction: discord.Interaction, text: str = "テストメッセージです"):
            """Test TTS with custom text via slash command."""
            await test_tts.handle(interaction, self.bot, text)

        self._registered["test"] = {"handler": test_tts.handle}

    async def _sync(self, guild: Optional[discord.Guild] = None) -> None:
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

    async def handle_interaction(self, interaction: discord.Interaction) -> None:
        """Handle slash command interactions.

        Args:
            interaction: Discord interaction object

        """
        try:
            # Get command info
            command_name = interaction.command.name if interaction.command else "unknown"
            logger.debug(f"Received slash command interaction: /{command_name}")

            # Check if command is registered
            if command_name not in self._registered:
                logger.warning(f"Unknown slash command: {command_name}")
                await interaction.response.send_message(f"❌ Unknown command: `{command_name}`", ephemeral=True)
                return

            # Update command statistics
            if hasattr(self.bot, "status_manager") and self.bot.status_manager:
                await self.bot.status_manager.record_command_usage(f"slash_{command_name}")

            # Command is handled by the registered decorator function
            # The actual response is handled by the individual command handlers

        except Exception as e:
            logger.error(f"Error handling slash command interaction: {e}")
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message("❌ An error occurred processing this command", ephemeral=True)
            except Exception:
                pass  # Interaction already responded to or failed

    def get_registered_commands(self) -> dict[str, dict[str, Any]]:
        """Get information about registered slash commands."""
        return self._registered.copy()

    def clear_commands(self) -> None:
        """Clear all registered slash commands."""
        self._registered.clear()
        logger.info("Cleared all slash commands")

    async def shutdown(self) -> None:
        """Shutdown slash command registry."""
        logger.info("Slash command registry shutting down")
        self.clear_commands()
