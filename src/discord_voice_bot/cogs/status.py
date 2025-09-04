from __future__ import annotations

from typing import Any

from discord import app_commands
from discord.ext import commands

from ..slash.embeds.status import create_basic_status_embed, create_status_embed


class StatusCommands(commands.Cog):
    """Hybrid status command (prefix + slash) using discord.py primitives.

    This cog consolidates the previously separate slash implementation
    into a single hybrid command to reduce duplication.
    """

    def __init__(self, bot: commands.Bot) -> None:
        super().__init__()
        self.bot = bot

    @commands.hybrid_command(name="status", description="Show bot status and statistics")
    @commands.has_permissions(send_messages=True)
    @commands.cooldown(1, 3.0, commands.BucketType.user)
    @app_commands.checks.cooldown(1, 3.0)
    @app_commands.default_permissions()  # default: no extra permission restrictions
    async def status(self, ctx: commands.Context[Any]) -> None:
        """Display current bot status as an embed.

        Works both as a prefix command and a slash command.
        """
        try:
            if hasattr(self.bot, "status_manager") and getattr(self.bot, "status_manager"):
                status_manager = getattr(self.bot, "status_manager")
                status = status_manager.get_statistics()
                config = getattr(self.bot, "config", None)
                config = config() if callable(config) else config
                embed = await create_status_embed(status, config)  # type: ignore[arg-type]
            else:
                embed = await create_basic_status_embed()

            _ = await ctx.send(embed=embed)
        except Exception:
            # Attempt best-effort user feedback without leaking internals
            try:
                if getattr(ctx, "interaction", None):
                    _ = await ctx.send("❌ Error retrieving status", ephemeral=True)
                else:
                    _ = await ctx.send("❌ Error retrieving status")
            except Exception:
                pass


async def setup(bot: commands.Bot) -> None:  # extension-style loader (optional)
    await bot.add_cog(StatusCommands(bot))
