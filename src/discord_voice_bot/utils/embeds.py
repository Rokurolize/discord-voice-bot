from __future__ import annotations

import discord


def make_embed(title: str, description: str | None = None, *, color: discord.Color | None = None) -> discord.Embed:
    """Create an embed with optional description and color."""
    embed = discord.Embed(title=title, description=description, color=color or discord.Color.blue())
    return embed


def add_field(embed: discord.Embed, name: str, value: str, *, inline: bool = True) -> discord.Embed:
    """Add a field to an embed and return it for fluent style."""
    _ = embed.add_field(name=name, value=value, inline=inline)
    return embed

