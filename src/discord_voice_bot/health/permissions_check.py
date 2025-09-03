from __future__ import annotations

import discord

CRITICAL_PERMISSIONS = (
    "connect",
    "speak",
    "view_channel",
)


def check_permissions_in_guild(
    guild: discord.Guild,
    perms: discord.Permissions,
    trigger_termination: bool = False,
) -> list[str]:
    issues: list[str] = []
    for name in CRITICAL_PERMISSIONS:
        if not getattr(perms, name, False):
            issues.append(f"Missing permission: {name} in guild {guild.id}")
    return issues


async def check_critical_permissions(
    bot: discord.Client,
    target_channel_id: int | None,
) -> tuple[bool, list[str]]:
    """Best-effort scan across guilds for critical permission gaps.

    Returns (healthy, issues).
    """
    issues: list[str] = []
    if not bot.guilds:
        return True, issues

    for guild in bot.guilds:
        me = guild.me
        perms = None
        if target_channel_id:
            ch = guild.get_channel(target_channel_id)
            if isinstance(ch, (discord.VoiceChannel, discord.StageChannel)):
                perms = ch.permissions_for(me)
        if perms is None:
            perms = guild.me.guild_permissions
        issues.extend(check_permissions_in_guild(guild, perms))

    return (len(issues) == 0), issues
