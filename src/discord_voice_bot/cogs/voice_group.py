from __future__ import annotations

from typing import Any, cast

import discord
from discord import app_commands
from discord.ext import commands

from ..config import Config
from ..slash.autocomplete.voice import voice_autocomplete
from ..slash.embeds.voices import create_voices_embed
from ..user_settings import load_user_settings


class TTSGroup(commands.GroupCog, name="tts", description="Text-to-Speech controls"):
    """Slash command group for TTS operations (alongside existing hybrids).

    This group provides a consolidated slash UX without breaking existing
    top-level hybrid commands. It is safe to register concurrently since it
    uses a distinct group name ("/tts").
    """

    def __init__(self, bot: commands.Bot) -> None:
        super().__init__()
        self.bot = bot

    # /tts set
    @app_commands.command(name="set", description="Set or show personal voice preference")
    @app_commands.describe(speaker="Voice name or numeric ID; use 'reset' to clear")
    @app_commands.autocomplete(speaker=voice_autocomplete)
    async def tts_set(self, interaction: discord.Interaction, speaker: str | None = None) -> None:
        try:
            user_id = str(interaction.user.id)
            settings = load_user_settings()

            # Show current setting
            if speaker is None:
                current = settings.get_user_settings(user_id)
                if current:
                    embed = discord.Embed(
                        title="🎭 Your Voice Settings",
                        color=discord.Color.blue(),
                        description=f"Current voice: **{current['speaker_name']}** (ID: {current['speaker_id']})",
                    )
                    _ = embed.add_field(
                        name="Commands",
                        value="`/tts set <name>` to set\n`/tts set reset` to default\n`/tts list` to list",
                        inline=False,
                    )
                    _ = await interaction.response.send_message(embed=embed, ephemeral=True)
                else:
                    _ = await interaction.response.send_message(
                        "ℹ️ No custom voice set. Using default.", ephemeral=True
                    )
                return

            sp = speaker.strip()
            if sp.lower() == "reset":
                if settings.remove_user_speaker(user_id):
                    _ = await interaction.response.send_message(
                        "✅ Voice preference reset to default", ephemeral=True
                    )
                else:
                    _ = await interaction.response.send_message(
                        "ℹ️ You don't have a custom voice set", ephemeral=True
                    )
                return

            # Resolve available speakers from config (no engine startup)
            config_val = getattr(self.bot, "config", None)
            config_val = config_val() if callable(config_val) else config_val
            cfg = cast(Config, config_val)
            if not cfg or not hasattr(cfg, "engines") or not hasattr(cfg, "tts_engine"):
                _ = await interaction.response.send_message("❌ Configuration unavailable; try again later.", ephemeral=True)
                return

            engine_key = (cfg.tts_engine or "voicevox").lower()
            engine_cfg = cast(dict[str, Any], cfg.engines.get(engine_key, {}))
            speakers_map = cast(dict[str, int], engine_cfg.get("speakers", {}))
            if not speakers_map:
                _ = await interaction.response.send_message(
                    f"❌ No speakers configured for engine '{engine_key}'. Use `/tts list`.", ephemeral=True
                )
                return

            matched_name: str | None = None
            matched_id: int | None = None
            sp_lower = sp.lower()
            for name, sid in speakers_map.items():
                if name.lower() == sp_lower or str(sid) == sp:
                    matched_name, matched_id = name, sid
                    break

            if matched_name and matched_id is not None:
                if settings.set_user_speaker(user_id, matched_id, matched_name, cfg.tts_engine):
                    _ = await interaction.response.send_message(
                        f"✅ Voice set to **{matched_name}** (ID: {matched_id}) on {cfg.tts_engine.upper()}",
                        ephemeral=True,
                    )
                    # Optional short test
                    test_text = f"{matched_name}の声です"
                    if hasattr(self.bot, "voice_handler") and getattr(self.bot, "voice_handler"):
                        mp = getattr(self.bot, "message_processor", None)
                        chunks = mp.chunk_message(test_text) if mp and hasattr(mp, "chunk_message") else [test_text]
                        msg = {
                            "text": test_text,
                            "user_id": interaction.user.id,
                            "username": interaction.user.display_name,
                            "chunks": chunks,
                            "group_id": f"group_voice_test_{interaction.id}",
                        }
                        await self.bot.voice_handler.add_to_queue(msg)  # type: ignore[attr-defined]
                else:
                    _ = await interaction.response.send_message("❌ Failed to save voice preference", ephemeral=True)
            else:
                _ = await interaction.response.send_message(
                    f"❌ Voice '{speaker}' not found. Use `/tts list` to see available options.", ephemeral=True
                )
        except Exception:
            await self._safe_error(interaction, "❌ Error setting voice preference")

    # /tts list
    @app_commands.command(name="list", description="List all available voices")
    async def tts_list(self, interaction: discord.Interaction) -> None:
        try:
            config_val = getattr(self.bot, "config", None)
            config_val = config_val() if callable(config_val) else config_val
            cfg = cast(Config, config_val)
            tts_engine = getattr(self.bot, "tts_engine", None)
            if not cfg or not tts_engine:
                _ = await interaction.response.send_message("❌ Voice information unavailable", ephemeral=True)
                return
            user_settings = load_user_settings()
            embed = await create_voices_embed(interaction.user.id, cfg, tts_engine, user_settings)
            _ = await interaction.response.send_message(embed=embed, ephemeral=False)
        except Exception:
            await self._safe_error(interaction, "❌ Error retrieving voice information")

    # /tts check
    @app_commands.command(name="check", description="Perform voice connection health check")
    async def tts_check(self, interaction: discord.Interaction) -> None:
        try:
            if not hasattr(self.bot, "voice_handler") or not getattr(self.bot, "voice_handler"):
                embed = discord.Embed(
                    title="🔍 Voice Health Check",
                    color=discord.Color.red(),
                    description="❌ Voice handler not initialized",
                )
                _ = await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            status = cast(dict[str, Any], self.bot.voice_handler.get_status())  # type: ignore[attr-defined]
            health = cast(dict[str, Any], await self.bot.voice_handler.health_check())  # type: ignore[attr-defined]

            embed = discord.Embed(
                title="🔍 Voice Health Check Results",
                color=(discord.Color.green() if health.get("healthy") else discord.Color.red()),
                description=f"Overall Status: {'✅ HEALTHY' if health.get('healthy') else '❌ ISSUES FOUND'}",
            )
            _ = embed.add_field(
                name="🔗 Connection Status",
                value=(
                    f"Voice Client: {'✅' if health.get('voice_client_exists') else '❌'}\n"
                    f"Connected: {'✅' if health.get('voice_client_connected') else '❌'}\n"
                    f"Channel: {status.get('voice_channel_name', 'None') or 'None'}"
                ),
                inline=True,
            )
            _ = embed.add_field(
                name="🎵 Audio System",
                value=(
                    f"Playback Ready: {'✅' if health.get('audio_playback_ready') else '❌'}\n"
                    f"Synthesis: {'✅' if health.get('can_synthesize') else '❌'}\n"
                    f"Queue Size: {status.get('total_queue_size', 0)}"
                ),
                inline=True,
            )
            issues = cast(list[Any], health.get("issues") or [])
            if issues:
                _ = embed.add_field(name="⚠️ Issues Found", value="\n".join(f"• {i}" for i in issues), inline=False)
            recs = cast(list[Any], health.get("recommendations") or [])
            if recs:
                _ = embed.add_field(name="🛠️ Recommendations", value="\n".join(f"💡 {r}" for r in recs), inline=False)

            _ = await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception:
            await self._safe_error(interaction, "❌ Error during health check")

    # /tts reconnect
    @app_commands.command(name="reconnect", description="Manually attempt to reconnect to voice channel")
    async def tts_reconnect(self, interaction: discord.Interaction) -> None:
        try:
            if not hasattr(self.bot, "voice_handler") or not getattr(self.bot, "voice_handler"):
                _ = await interaction.response.send_message("❌ Voice handler not initialized", ephemeral=True)
                return

            cm = getattr(self.bot, "config_manager", None)
            target_id = cm.get_target_voice_channel_id() if cm else None

            await self.bot.voice_handler.cleanup_voice_client()  # type: ignore[attr-defined]
            success = False
            if target_id:
                success = await self.bot.voice_handler.connect_to_channel(int(target_id))  # type: ignore[attr-defined]
            _ = await interaction.response.send_message(
                "✅ Reconnected to voice channel" if success else "❌ Reconnection failed", ephemeral=True
            )
        except Exception as e:
            await self._safe_error(interaction, f"❌ Error during reconnection: {e}")

    # /tts test
    @app_commands.command(name="test", description="Test TTS with custom text")
    @app_commands.describe(text="Text to convert to speech")
    async def tts_test(self, interaction: discord.Interaction, text: str = "テストメッセージです") -> None:
        try:
            if not hasattr(self.bot, "voice_handler") or not getattr(self.bot, "voice_handler"):
                _ = await interaction.response.send_message("❌ Voice handler not available", ephemeral=True)
                return
            status = cast(dict[str, Any], self.bot.voice_handler.get_status())  # type: ignore[attr-defined]
            if not status.get("connected"):
                _ = await interaction.response.send_message("❌ Not connected to voice channel", ephemeral=True)
                return

            from ..message_processor import get_message_processor

            message_processor = get_message_processor(self.bot.config_manager)  # type: ignore[attr-defined]
            processed_text = message_processor.process_message_content(text, interaction.user.display_name)
            chunks = message_processor.chunk_message(processed_text)

            processed_message = {
                "text": processed_text,
                "user_id": interaction.user.id,
                "username": interaction.user.display_name,
                "chunks": chunks,
                "group_id": f"tts_test_{interaction.id}",
            }
            await self.bot.voice_handler.add_to_queue(processed_message)  # type: ignore[attr-defined]
            _ = await interaction.response.send_message(f"🎤 Test TTS queued: `{processed_text[:50]}...`")
        except Exception:
            await self._safe_error(interaction, "❌ Error testing TTS")

    # /tts skip
    @app_commands.command(name="skip", description="Skip current TTS playback")
    async def tts_skip(self, interaction: discord.Interaction) -> None:
        try:
            if not hasattr(self.bot, "voice_handler") or not getattr(self.bot, "voice_handler"):
                _ = await interaction.response.send_message("❌ Voice handler not available", ephemeral=True)
                return
            skipped = await self.bot.voice_handler.skip_current()  # type: ignore[attr-defined]
            _ = await interaction.response.send_message(
                "⏭️ Skipped current TTS message" if skipped else "❌ No TTS message to skip",
                ephemeral=True,
            )
        except Exception:
            await self._safe_error(interaction, "❌ Error skipping message")

    # /tts clear
    @app_commands.command(name="clear", description="Clear TTS queue")
    async def tts_clear(self, interaction: discord.Interaction) -> None:
        try:
            if not hasattr(self.bot, "voice_handler") or not getattr(self.bot, "voice_handler"):
                _ = await interaction.response.send_message("❌ Voice handler not available", ephemeral=True)
                return
            count = await self.bot.voice_handler.clear_all()  # type: ignore[attr-defined]
            _ = await interaction.response.send_message(f"🗑️ Cleared {count} messages from TTS queue", ephemeral=True)
        except Exception:
            await self._safe_error(interaction, "❌ Error clearing queue")

    async def _safe_error(self, interaction: discord.Interaction, message: str) -> None:
        try:
            if interaction.response.is_done():
                await interaction.followup.send(message, ephemeral=True)
            else:
                _ = await interaction.response.send_message(message, ephemeral=True)
        except Exception:
            pass


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(TTSGroup(bot))
