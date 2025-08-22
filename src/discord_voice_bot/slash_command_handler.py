"""Slash command handling for Discord Voice TTS Bot."""

from typing import TYPE_CHECKING, Any, Dict, List, Optional

import discord
from discord import app_commands
from discord.ext import commands
from loguru import logger

if TYPE_CHECKING:
    from .bot import DiscordVoiceTTSBot


class SlashCommandHandler:
    """Handles Discord slash commands with modern app command framework."""

    def __init__(self, bot: "DiscordVoiceTTSBot"):
        """Initialize slash command handler.

        Args:
            bot: The Discord bot instance
        """
        self.bot = bot
        self._registered_commands: Dict[str, Dict[str, Any]] = {}
        self._autocomplete_handlers: Dict[str, callable] = {}
        logger.info("Slash command handler initialized")

    async def register_slash_commands(self) -> None:
        """Register all slash commands with Discord."""
        try:
            logger.info("🔧 Registering slash commands...")

            # Clear existing commands to avoid conflicts
            self.bot.tree.clear_commands(guild=None)

            # Register core commands
            await self._register_core_commands()

            # Register voice commands
            await self._register_voice_commands()

            # Register utility commands
            await self._register_utility_commands()

            # Sync with Discord
            await self._sync_commands()

            logger.info(f"✅ Successfully registered {len(self._registered_commands)} slash commands")

        except Exception as e:
            logger.error(f"❌ Failed to register slash commands: {e}")
            raise

    async def _register_core_commands(self) -> None:
        """Register core bot commands."""

        # Status command
        @self.bot.tree.command(name="status", description="Show bot status and statistics")
        async def status_slash(interaction: discord.Interaction):
            """Show bot status via slash command."""
            await self._handle_status_command(interaction)

        self._registered_commands["status"] = {
            "description": "Show bot status and statistics",
            "handler": self._handle_status_command,
        }

        # Skip command
        @self.bot.tree.command(name="skip", description="Skip current TTS playback")
        async def skip_slash(interaction: discord.Interaction):
            """Skip current TTS playback via slash command."""
            await self._handle_skip_command(interaction)

        self._registered_commands["skip"] = {
            "description": "Skip current TTS playback",
            "handler": self._handle_skip_command,
        }

        # Clear command
        @self.bot.tree.command(name="clear", description="Clear TTS queue")
        async def clear_slash(interaction: discord.Interaction):
            """Clear TTS queue via slash command."""
            await self._handle_clear_command(interaction)

        self._registered_commands["clear"] = {
            "description": "Clear TTS queue",
            "handler": self._handle_clear_command,
        }

    async def _register_voice_commands(self) -> None:
        """Register voice-related commands."""

        # Voice command with autocomplete
        @self.bot.tree.command(name="voice", description="Set or show personal voice preference")
        @app_commands.autocomplete(speaker=self._voice_autocomplete)
        async def voice_slash(interaction: discord.Interaction, speaker: Optional[str] = None):
            """Set or show personal voice preference via slash command."""
            await self._handle_voice_command(interaction, speaker)

        self._registered_commands["voice"] = {
            "description": "Set or show personal voice preference",
            "handler": self._handle_voice_command,
            "autocomplete": self._voice_autocomplete,
        }

        # Voices command
        @self.bot.tree.command(name="voices", description="List all available voices")
        async def voices_slash(interaction: discord.Interaction):
            """List all available voices via slash command."""
            await self._handle_voices_command(interaction)

        self._registered_commands["voices"] = {
            "description": "List all available voices",
            "handler": self._handle_voices_command,
        }

        # Voice check command
        @self.bot.tree.command(name="voicecheck", description="Perform voice connection health check")
        async def voicecheck_slash(interaction: discord.Interaction):
            """Perform voice connection health check via slash command."""
            await self._handle_voicecheck_command(interaction)

        self._registered_commands["voicecheck"] = {
            "description": "Perform voice connection health check",
            "handler": self._handle_voicecheck_command,
        }

        # Reconnect command
        @self.bot.tree.command(name="reconnect", description="Manually attempt to reconnect to voice channel")
        async def reconnect_slash(interaction: discord.Interaction):
            """Manually attempt to reconnect to voice channel via slash command."""
            await self._handle_reconnect_command(interaction)

        self._registered_commands["reconnect"] = {
            "description": "Manually attempt to reconnect to voice channel",
            "handler": self._handle_reconnect_command,
        }

    async def _register_utility_commands(self) -> None:
        """Register utility commands."""

        # Test command
        @self.bot.tree.command(name="test", description="Test TTS with custom text")
        @app_commands.describe(text="Text to convert to speech")
        async def test_slash(interaction: discord.Interaction, text: str = "テストメッセージです"):
            """Test TTS with custom text via slash command."""
            await self._handle_test_command(interaction, text)

        self._registered_commands["test"] = {
            "description": "Test TTS with custom text",
            "handler": self._handle_test_command,
        }

        # Speakers command (alias for voices)
        @self.bot.tree.command(name="speakers", description="List available TTS speakers")
        async def speakers_slash(interaction: discord.Interaction):
            """List available TTS speakers via slash command."""
            await self._handle_voices_command(interaction)  # Use same handler as voices

        self._registered_commands["speakers"] = {
            "description": "List available TTS speakers",
            "handler": self._handle_voices_command,
        }

    async def _sync_commands(self, guild: Optional[discord.Guild] = None) -> None:
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
            if command_name not in self._registered_commands:
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

    # Command Handlers
    async def _handle_status_command(self, interaction: discord.Interaction) -> None:
        """Handle status slash command."""
        try:
            if hasattr(self.bot, "status_manager") and self.bot.status_manager:
                status = self.bot.status_manager.get_statistics()
                embed = await self._create_status_embed(status)
            else:
                # Fallback to basic status
                embed = await self._create_basic_status_embed()

            await interaction.response.send_message(embed=embed)

        except Exception as e:
            logger.error(f"Error in status slash command: {e}")
            await interaction.response.send_message("❌ Error retrieving status", ephemeral=True)

    async def _handle_skip_command(self, interaction: discord.Interaction) -> None:
        """Handle skip slash command."""
        try:
            if not hasattr(self.bot, "voice_handler") or not self.bot.voice_handler:
                await interaction.response.send_message("❌ Voice handler not available", ephemeral=True)
                return

            skipped = await self.bot.voice_handler.skip_current()
            if skipped:
                await interaction.response.send_message("⏭️ Skipped current TTS message")
            else:
                await interaction.response.send_message("❌ No TTS message to skip", ephemeral=True)

        except Exception as e:
            logger.error(f"Error in skip slash command: {e}")
            await interaction.response.send_message("❌ Error skipping message", ephemeral=True)

    async def _handle_clear_command(self, interaction: discord.Interaction) -> None:
        """Handle clear slash command."""
        try:
            if not hasattr(self.bot, "voice_handler") or not self.bot.voice_handler:
                await interaction.response.send_message("❌ Voice handler not available", ephemeral=True)
                return

            cleared_count = await self.bot.voice_handler.clear_all()
            await interaction.response.send_message(f"🗑️ Cleared {cleared_count} messages from TTS queue")

        except Exception as e:
            logger.error(f"Error in clear slash command: {e}")
            await interaction.response.send_message("❌ Error clearing queue", ephemeral=True)

    async def _handle_voice_command(self, interaction: discord.Interaction, speaker: Optional[str] = None) -> None:
        """Handle voice slash command."""
        try:
            from .user_settings import user_settings

            user_id = str(interaction.user.id)

            # If no speaker specified, show current setting
            if speaker is None:
                current_settings = user_settings.get_user_settings(user_id)
                if current_settings:
                    embed = discord.Embed(
                        title="🎭 Your Voice Settings",
                        color=discord.Color.blue(),
                        description=f"Current voice: **{current_settings['speaker_name']}** (ID: {current_settings['speaker_id']})",
                    )
                else:
                    embed = discord.Embed(
                        title="🎭 Your Voice Settings",
                        color=discord.Color.greyple(),
                        description="No custom voice set. Using default voice.",
                    )
                embed.add_field(
                    name="Commands",
                    value="`/voice <name>` - Set voice\n`/voice reset` - Reset to default\n`/voices` - List available",
                    inline=False,
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Handle reset
            if speaker.lower() == "reset":
                if user_settings.remove_user_speaker(user_id):
                    await interaction.response.send_message("✅ Voice preference reset to default", ephemeral=True)
                else:
                    await interaction.response.send_message("ℹ️ You don't have a custom voice set", ephemeral=True)
                return

            # Get available speakers
            from .tts_engine import tts_engine

            speakers = await tts_engine.get_available_speakers()
            from .config import config

            # Find matching speaker (case-insensitive)
            speaker_lower = speaker.lower()
            matched_speaker = None
            matched_id = None

            for name, speaker_id in speakers.items():
                if name.lower() == speaker_lower or str(speaker_id) == speaker:
                    matched_speaker = name
                    matched_id = speaker_id
                    break

            if matched_speaker and matched_id is not None:
                # Pass current engine to ensure proper mapping
                if user_settings.set_user_speaker(user_id, matched_id, matched_speaker, config.tts_engine):
                    await interaction.response.send_message(f"✅ Voice set to **{matched_speaker}** (ID: {matched_id}) on {config.tts_engine.upper()}", ephemeral=True)
                    # Test the new voice
                    test_text = f"{matched_speaker}の声です"
                    if hasattr(self.bot, "voice_handler") and self.bot.voice_handler:
                        from .message_processor import message_processor

                        chunks = message_processor.chunk_message(test_text)
                        processed_message = {
                            "text": test_text,
                            "user_id": interaction.user.id,
                            "username": interaction.user.display_name,
                            "chunks": chunks,
                            "group_id": f"slash_voice_test_{interaction.id}",
                        }
                        await self.bot.voice_handler.add_to_queue(processed_message)
                else:
                    await interaction.response.send_message("❌ Failed to save voice preference", ephemeral=True)
            else:
                await interaction.response.send_message(f"❌ Voice '{speaker}' not found. Use `/voices` to see available options.", ephemeral=True)

        except Exception as e:
            logger.error(f"Error in voice slash command: {e}")
            await interaction.response.send_message("❌ Error setting voice preference", ephemeral=True)

    async def _handle_voices_command(self, interaction: discord.Interaction) -> None:
        """Handle voices slash command."""
        try:
            embed = await self._create_voices_embed()
            await interaction.response.send_message(embed=embed)

        except Exception as e:
            logger.error(f"Error in voices slash command: {e}")
            await interaction.response.send_message("❌ Error retrieving voices", ephemeral=True)

    async def _handle_voicecheck_command(self, interaction: discord.Interaction) -> None:
        """Handle voicecheck slash command."""
        try:
            if not hasattr(self.bot, "voice_handler") or not self.bot.voice_handler:
                embed = discord.Embed(title="🔍 Voice Health Check", color=discord.Color.red(), description="❌ Voice handler not initialized")
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Perform health check
            embed = discord.Embed(title="🔍 Voice Health Check", color=discord.Color.blue(), description="Performing comprehensive voice connection diagnostics...")

            # Send initial message
            await interaction.response.send_message(embed=embed, ephemeral=True)

            try:
                # Get basic status
                status = self.bot.voice_handler.get_status()
                health_status = await self.bot.voice_handler.health_check()

                # Update embed with results
                embed = discord.Embed(
                    title="🔍 Voice Health Check Results",
                    color=(discord.Color.green() if health_status["healthy"] else discord.Color.red()),
                    description=f"Overall Status: {'✅ HEALTHY' if health_status['healthy'] else '❌ ISSUES FOUND'}",
                )

                # Connection status
                embed.add_field(
                    name="🔗 Connection Status",
                    value=f"Voice Client: {'✅' if health_status['voice_client_exists'] else '❌'}\n"
                    f"Connected: {'✅' if health_status['voice_client_connected'] else '❌'}\n"
                    f"Channel: {status.get('voice_channel_name', 'None') or 'None'}",
                    inline=True,
                )

                # Audio system status
                embed.add_field(
                    name="🎵 Audio System",
                    value=f"Playback Ready: {'✅' if health_status['audio_playback_ready'] else '❌'}\n"
                    f"Synthesis: {'✅' if health_status['can_synthesize'] else '❌'}\n"
                    f"Queue Size: {status.get('total_queue_size', 0)}",
                    inline=True,
                )

                # Issues and recommendations
                if health_status["issues"]:
                    issues_text = "\n".join(f"• {issue}" for issue in health_status["issues"])
                    embed.add_field(name="⚠️ Issues Found", value=issues_text, inline=False)

                if health_status["recommendations"]:
                    recommendations_text = "\n".join(f"💡 {rec}" for rec in health_status["recommendations"])
                    embed.add_field(name="🔧 Recommendations", value=recommendations_text, inline=False)

                # If not healthy, offer to attempt reconnection
                if not health_status["healthy"]:
                    embed.add_field(name="🔄 Quick Actions", value="Use `/reconnect` to attempt reconnection", inline=False)

            except Exception as e:
                embed = discord.Embed(title="🔍 Voice Health Check", color=discord.Color.red(), description=f"❌ Error during health check: {e}")

            # Edit the original response with results
            await interaction.edit_original_response(embed=embed)

        except Exception as e:
            logger.error(f"Error in voicecheck slash command: {e}")
            await interaction.response.send_message("❌ Error during health check", ephemeral=True)

    async def _handle_reconnect_command(self, interaction: discord.Interaction) -> None:
        """Handle reconnect slash command."""
        try:
            if not hasattr(self.bot, "voice_handler") or not self.bot.voice_handler:
                embed = discord.Embed(title="🔄 Voice Reconnection", color=discord.Color.red(), description="❌ Voice handler not initialized")
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            embed = discord.Embed(title="🔄 Voice Reconnection", color=discord.Color.orange(), description="Attempting to reconnect to voice channel...")

            await interaction.response.send_message(embed=embed, ephemeral=True)

            try:
                # Attempt reconnection
                logger.info(f"🔄 MANUAL RECONNECTION - User {interaction.user.name} requested voice reconnection")
                from .config import config

                success = await self.bot.voice_handler.connect_to_channel(config.target_voice_channel_id)

                # Get new status
                new_status = self.bot.voice_handler.get_status()

                if success and new_status["connected"]:
                    embed = discord.Embed(title="🔄 Voice Reconnection", color=discord.Color.green(), description="✅ Successfully reconnected to voice channel!")

                    embed.add_field(name="📍 Channel Info", value=f"Name: {new_status['voice_channel_name']}\nID: {new_status['voice_channel_id']}", inline=True)

                    embed.add_field(name="📊 Queue Status", value=f"Ready: {new_status['audio_queue_size']} chunks\nSynthesizing: {new_status['synthesis_queue_size']} chunks", inline=True)

                    logger.info(f"✅ MANUAL RECONNECTION SUCCESSFUL - Connected to {new_status['voice_channel_name']}")
                else:
                    embed = discord.Embed(title="🔄 Voice Reconnection", color=discord.Color.red(), description="❌ Reconnection failed")

                    embed.add_field(
                        name="🔍 Troubleshooting",
                        value="Check the bot logs for detailed error information.\nCommon issues:\n• Bot lacks 'Connect' permission\n• Channel is full\n• Network connectivity issues",
                        inline=False,
                    )

                    embed.add_field(name="🔧 Next Steps", value="Use `/voicecheck` for detailed diagnostics\nContact bot administrator if issues persist", inline=False)

                    logger.error("❌ MANUAL RECONNECTION FAILED - Check logs for detailed error information")

            except Exception as e:
                embed = discord.Embed(title="🔄 Voice Reconnection", color=discord.Color.red(), description=f"❌ Error during reconnection: {e}")
                logger.error(f"💥 CRITICAL ERROR during manual reconnection: {e}")

            await interaction.edit_original_response(embed=embed)

        except Exception as e:
            logger.error(f"Error in reconnect slash command: {e}")
            await interaction.response.send_message("❌ Error during reconnection", ephemeral=True)

    async def _handle_test_command(self, interaction: discord.Interaction, text: str) -> None:
        """Handle test slash command."""
        try:
            if not hasattr(self.bot, "voice_handler") or not self.bot.voice_handler:
                await interaction.response.send_message("❌ Voice handler not available", ephemeral=True)
                return

            status = self.bot.voice_handler.get_status()
            if not status["connected"]:
                await interaction.response.send_message("❌ Not connected to voice channel", ephemeral=True)
                return

            # Process and queue the test message
            from .message_processor import message_processor
            from .config import config

            processed_text = message_processor.process_message_content(text, interaction.user.display_name)
            chunks = message_processor.chunk_message(processed_text)

            processed_message = {
                "text": processed_text,
                "user_id": interaction.user.id,
                "username": interaction.user.display_name,
                "chunks": chunks,
                "group_id": f"slash_test_{interaction.id}",
            }

            await self.bot.voice_handler.add_to_queue(processed_message)
            await interaction.response.send_message(f"🎤 Test TTS queued: `{processed_text[:50]}...`")

            # Update stats
            if hasattr(self.bot, "status_manager") and self.bot.status_manager:
                await self.bot.status_manager.record_command_usage("slash_test")
                self.bot.status_manager.record_tts_played()

        except Exception as e:
            logger.error(f"Error in test slash command: {e}")
            await interaction.response.send_message("❌ Error testing TTS", ephemeral=True)

    # Autocomplete Handlers
    async def _voice_autocomplete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        """Provide autocomplete suggestions for voice selection."""
        try:
            from .tts_engine import tts_engine

            speakers = await tts_engine.get_available_speakers()

            # Filter speakers based on current input
            choices: List[app_commands.Choice[str]] = []
            current_lower = current.lower()

            for name in speakers.keys():
                if current_lower in name.lower():
                    choices.append(app_commands.Choice(name=name, value=name))
                    if len(choices) >= 25:  # Discord's limit for autocomplete choices
                        break

            return choices

        except Exception as e:
            logger.error(f"Error in voice autocomplete: {e}")
            return []

    # Embed Creation Helpers
    async def _create_status_embed(self, status: Dict[str, Any]) -> discord.Embed:
        """Create status embed from status data."""
        embed = discord.Embed(
            title="🤖 Discord Voice TTS Bot Status",
            color=(discord.Color.green() if status.get("voice_status", {}).get("connected") else discord.Color.red()),
            description="ずんだもんボイス読み上げBot",
        )

        # Connection status
        voice_status = status.get("voice_status", {})
        embed.add_field(
            name="🔗 接続状態",
            value=f"Voice: {'✅ 接続中' if voice_status.get('connected') else '❌ 未接続'}\nChannel: {voice_status.get('channel_name') or 'なし'}",
            inline=True,
        )

        # TTS status
        from .config import config

        embed.add_field(
            name="🎤 TTS状態",
            value=f"Engine: {config.tts_engine.upper()}\nSpeaker: {config.tts_speaker}\nPlaying: {'✅' if voice_status.get('is_playing') else '❌'}",
            inline=True,
        )

        # Queue status
        embed.add_field(
            name="📋 キュー状態",
            value=f"Ready: {voice_status.get('queue_size', 0)} chunks\nTotal: {voice_status.get('queue_size', 0)}\nProcessed: {status.get('messages_processed', 0)}",
            inline=True,
        )

        # Bot info
        embed.add_field(
            name="ℹ️ Bot情報",
            value=f"Uptime: {status.get('uptime_formatted', 'Unknown')}\nErrors: {status.get('connection_errors', 0)}",
            inline=True,
        )

        return embed

    async def _create_basic_status_embed(self) -> discord.Embed:
        """Create basic status embed when status manager is not available."""
        embed = discord.Embed(title="🤖 Discord Voice TTS Bot Status", color=discord.Color.blue(), description="Status information unavailable")

        embed.add_field(name="ℹ️ Status", value="Basic status information is currently unavailable.\nThe bot may still be starting up or experiencing issues.", inline=False)

        return embed

    async def _create_voices_embed(self) -> discord.Embed:
        """Create voices embed showing available speakers."""
        try:
            from .tts_engine import tts_engine
            from .user_settings import user_settings
            from .config import config

            speakers = await tts_engine.get_available_speakers()

            # Get user's current setting
            user_id = str(getattr(self.bot, "user", None) and self.bot.user.id or "unknown")
            current_settings = user_settings.get_user_settings(user_id)
            current_speaker = current_settings["speaker_name"] if current_settings else None

            embed = discord.Embed(
                title=f"🎭 Available Voices ({config.tts_engine.upper()})",
                color=discord.Color.blue(),
                description="Use `/voice <name>` to set your personal voice",
            )

            # Group speakers by base name
            speaker_groups: Dict[str, List[tuple[str, int]]] = {}
            for name, speaker_id in speakers.items():
                # Extract base name (e.g., "zunda" from "zunda_normal")
                base_name = name.split("_")[0] if "_" in name else name
                if base_name not in speaker_groups:
                    speaker_groups[base_name] = []
                speaker_groups[base_name].append((name, speaker_id))

            # Add fields for each speaker group
            for base_name, variants in speaker_groups.items():
                field_lines: List[str] = []
                for name, speaker_id in variants:
                    marker = "🔹" if name == current_speaker else "▫️"
                    field_lines.append(f"{marker} `{name}` ({speaker_id})")

                embed.add_field(name=base_name.title(), value="\n".join(field_lines), inline=True)

            # Add current setting info
            if current_speaker:
                embed.set_footer(text=f"Your current voice: {current_speaker}")
            else:
                embed.set_footer(text="You're using the default voice")

            return embed

        except Exception as e:
            logger.error(f"Error creating voices embed: {e}")
            return discord.Embed(title="🎭 Available Voices", color=discord.Color.red(), description="❌ Error retrieving voice information")

    def get_registered_commands(self) -> Dict[str, Dict[str, Any]]:
        """Get information about registered slash commands."""
        return self._registered_commands.copy()

    def clear_commands(self) -> None:
        """Clear all registered slash commands."""
        self._registered_commands.clear()
        logger.info("Cleared all slash commands")

    async def shutdown(self) -> None:
        """Shutdown slash command handler."""
        logger.info("Slash command handler shutting down")
        self.clear_commands()
