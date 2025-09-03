from __future__ import annotations

from typing import Any

from discord import app_commands
from discord.ext import commands


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


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(VoiceCommands(bot))

