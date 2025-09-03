from __future__ import annotations

from typing import Any, cast

from discord import app_commands
from discord.ext import commands

from ..config import Config
from ..slash.autocomplete.voice import voice_autocomplete
from ..slash.embeds.voices import create_voices_embed
from ..user_settings import load_user_settings


class VoiceCommands(commands.Cog):
    """Hybrid voice-related commands (prefix + slash)."""

    def __init__(self, bot: commands.Bot) -> None:
        super().__init__()
        self.bot = bot

    async def _send(self, ctx: commands.Context[Any], *args: Any, **kwargs: Any) -> None:
        # Support ephemeral when invoked as slash (HybridContext exposes interaction)
        if getattr(ctx, "interaction", None) is None and "ephemeral" in kwargs:
            kwargs.pop("ephemeral")
        _ = await ctx.send(*args, **kwargs)

    @commands.hybrid_command(name="skip", description="Skip current TTS playback")
    @commands.has_permissions(send_messages=True)
    @commands.cooldown(1, 3.0, commands.BucketType.user)
    @app_commands.default_permissions()
    async def skip(self, ctx: commands.Context[Any]) -> None:
        if not hasattr(self.bot, "voice_handler") or not getattr(self.bot, "voice_handler"):
            await self._send(ctx, "❌ Voice handler not available", ephemeral=True)
            return

        skipped = await self.bot.voice_handler.skip_current()  # type: ignore[attr-defined]
        if skipped:
            await self._send(ctx, "⏭️ Skipped current TTS message", ephemeral=True)
        else:
            await self._send(ctx, "❌ No TTS message to skip", ephemeral=True)

    @commands.hybrid_command(name="clear", description="Clear TTS queue")
    @commands.has_permissions(send_messages=True)
    @commands.cooldown(1, 3.0, commands.BucketType.user)
    @app_commands.default_permissions()
    async def clear(self, ctx: commands.Context[Any]) -> None:
        if not hasattr(self.bot, "voice_handler") or not getattr(self.bot, "voice_handler"):
            await self._send(ctx, "❌ Voice handler not available", ephemeral=True)
            return

        count = await self.bot.voice_handler.clear_all()  # type: ignore[attr-defined]
        await self._send(ctx, f"🗑️ Cleared {count} messages from TTS queue", ephemeral=True)

    @commands.hybrid_command(name="voices", description="List all available voices")
    @commands.has_permissions(send_messages=True)
    @commands.cooldown(1, 3.0, commands.BucketType.user)
    @app_commands.default_permissions()
    async def voices(self, ctx: commands.Context[Any]) -> None:
        # Resolve config (dataclass) and engine
        config = getattr(self.bot, "config", None)
        config = config() if callable(config) else config
        tts_engine = getattr(self.bot, "tts_engine", None)
        if not config or not tts_engine:
            await self._send(ctx, "❌ Voice information unavailable", ephemeral=True)
            return

        user_settings = load_user_settings()
        cfg = cast(Config, config)
        embed = await create_voices_embed(ctx.author.id, cfg, tts_engine, user_settings)
        await self._send(ctx, embed=embed)

    @commands.hybrid_command(name="voicecheck", description="Perform voice connection health check")
    @commands.has_permissions(send_messages=True)
    @commands.cooldown(1, 10.0, commands.BucketType.user)
    @app_commands.default_permissions()
    async def voicecheck(self, ctx: commands.Context[Any]) -> None:
        if not hasattr(self.bot, "voice_handler") or not getattr(self.bot, "voice_handler"):
            await self._send(ctx, "❌ Voice handler not initialized", ephemeral=True)
            return

        status = cast(dict[str, Any], self.bot.voice_handler.get_status())  # type: ignore[attr-defined]
        health = cast(dict[str, Any], await self.bot.voice_handler.health_check())  # type: ignore[attr-defined]

        # Minimal embed mirroring the slash handler
        from discord import Color, Embed

        embed = Embed(
            title="🔍 Voice Health Check Results",
            color=(Color.green() if health.get("healthy") else Color.red()),
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
                f"Playback Ready: {'✅' if health.get('audio_playback_ready') else '❌'}\nSynthesis: {'✅' if health.get('can_synthesize') else '❌'}\nQueue Size: {status.get('total_queue_size', 0)}"
            ),
            inline=True,
        )
        issues = cast(list[Any], health.get("issues") or [])
        if issues:
            _ = embed.add_field(name="⚠️ Issues Found", value="\n".join(f"• {i}" for i in issues), inline=False)
        recs = cast(list[Any], health.get("recommendations") or [])
        if recs:
            _ = embed.add_field(name="🛠️ Recommendations", value="\n".join(f"💡 {r}" for r in recs), inline=False)

        await self._send(ctx, embed=embed, ephemeral=True)

    @commands.hybrid_command(name="reconnect", description="Manually attempt to reconnect to voice channel")
    @commands.has_permissions(send_messages=True)
    @commands.cooldown(1, 10.0, commands.BucketType.user)
    @app_commands.default_permissions()
    async def reconnect(self, ctx: commands.Context[Any]) -> None:
        if not hasattr(self.bot, "voice_handler") or not getattr(self.bot, "voice_handler"):
            await self._send(ctx, "❌ Voice handler not initialized", ephemeral=True)
            return

        # Determine target voice channel from config manager if available
        cm = getattr(self.bot, "config_manager", None)
        target_id = cm.get_target_voice_channel_id() if cm else None

        try:
            await self.bot.voice_handler.cleanup_voice_client()  # type: ignore[attr-defined]
            success = False
            if target_id:
                success = await self.bot.voice_handler.connect_to_channel(int(target_id))  # type: ignore[attr-defined]
            await self._send(ctx, "✅ Reconnected to voice channel" if success else "❌ Reconnection failed", ephemeral=True)
        except Exception as e:
            await self._send(ctx, f"❌ Error during reconnection: {e}", ephemeral=True)

    @commands.hybrid_command(name="test", description="Test TTS with custom text")
    @app_commands.describe(text="Text to convert to speech")
    @commands.has_permissions(send_messages=True)
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    @app_commands.default_permissions()
    async def test_tts(self, ctx: commands.Context[Any], *, text: str = "テストメッセージです") -> None:
        if not hasattr(self.bot, "voice_handler") or not getattr(self.bot, "voice_handler"):
            await self._send(ctx, "❌ Voice handler not available", ephemeral=True)
            return

        status = cast(dict[str, Any], self.bot.voice_handler.get_status())  # type: ignore[attr-defined]
        if not status.get("connected"):
            await self._send(ctx, "❌ Not connected to voice channel", ephemeral=True)
            return

        # Process text using existing message processor
        from ..message_processor import get_message_processor

        message_processor = get_message_processor(self.bot.config_manager)  # type: ignore[attr-defined]
        processed_text = message_processor.process_message_content(text, ctx.author.display_name)
        chunks = message_processor.chunk_message(processed_text)

        group_id = f"hybrid_test_{getattr(getattr(ctx, 'interaction', None), 'id', getattr(getattr(ctx, 'message', None), 'id', '0'))}"
        processed_message = {
            "text": processed_text,
            "user_id": ctx.author.id,
            "username": ctx.author.display_name,
            "chunks": chunks,
            "group_id": group_id,
        }

        await self.bot.voice_handler.add_to_queue(processed_message)  # type: ignore[attr-defined]
        await self._send(ctx, f"🎤 Test TTS queued: `{processed_text[:50]}...`", ephemeral=True)

    @commands.hybrid_command(name="voice", description="Set or show personal voice preference")
    @app_commands.describe(speaker="Voice name or numeric ID; use 'reset' to clear")
    @app_commands.autocomplete(speaker=voice_autocomplete)
    @commands.has_permissions(send_messages=True)
    @commands.cooldown(1, 3.0, commands.BucketType.user)
    @app_commands.default_permissions()
    async def voice(self, ctx: commands.Context[Any], speaker: str | None = None) -> None:
        user_id = str(ctx.author.id)
        settings = load_user_settings()

        # Show current setting
        if speaker is None:
            current = settings.get_user_settings(user_id)
            if current:
                from discord import Color, Embed

                embed = Embed(
                    title="🎭 Your Voice Settings",
                    color=Color.blue(),
                    description=f"Current voice: **{current['speaker_name']}** (ID: {current['speaker_id']})",
                )
                _ = embed.add_field(name="Commands", value="`/voice <name>` to set\n`/voice reset` to default\n`/voices` to list", inline=False)
                await self._send(ctx, embed=embed, ephemeral=True)
            else:
                await self._send(ctx, "ℹ️ No custom voice set. Using default.", ephemeral=True)
            return

        sp = speaker.strip()
        if sp.lower() == "reset":
            if settings.remove_user_speaker(user_id):
                await self._send(ctx, "✅ Voice preference reset to default", ephemeral=True)
            else:
                await self._send(ctx, "ℹ️ You don't have a custom voice set", ephemeral=True)
            return

        # Resolve available speakers from config (no engine startup)
        config_val = getattr(self.bot, "config", None)
        config_val = config_val() if callable(config_val) else config_val
        cfg = cast(Config, config_val)
        if not cfg or not hasattr(cfg, "engines") or not hasattr(cfg, "tts_engine"):
            await self._send(ctx, "❌ Configuration unavailable; try again later.", ephemeral=True)
            return

        engine_key = (cfg.tts_engine or "voicevox").lower()
        engine_cfg = cast(dict[str, Any], cfg.engines.get(engine_key, {}))
        speakers_map = cast(dict[str, int], engine_cfg.get("speakers", {}))
        if not speakers_map:
            await self._send(ctx, f"❌ No speakers configured for engine '{engine_key}'. Use `/voices`.", ephemeral=True)
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
                await self._send(ctx, f"✅ Voice set to **{matched_name}** (ID: {matched_id}) on {cfg.tts_engine.upper()}", ephemeral=True)
                # Optional short test
                test_text = f"{matched_name}の声です"
                if hasattr(self.bot, "voice_handler") and getattr(self.bot, "voice_handler"):
                    mp = getattr(self.bot, "message_processor", None)
                    chunks = mp.chunk_message(test_text) if mp and hasattr(mp, "chunk_message") else [test_text]
                    msg = {
                        "text": test_text,
                        "user_id": ctx.author.id,
                        "username": ctx.author.display_name,
                        "chunks": chunks,
                        "group_id": f"hybrid_voice_test_{getattr(getattr(ctx, 'interaction', None), 'id', getattr(getattr(ctx, 'message', None), 'id', '0'))}",
                    }
                    await self.bot.voice_handler.add_to_queue(msg)  # type: ignore[attr-defined]
            else:
                await self._send(ctx, "❌ Failed to save voice preference", ephemeral=True)
        else:
            await self._send(ctx, f"❌ Voice '{speaker}' not found. Use `/voices` to see available options.", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(VoiceCommands(bot))
