from __future__ import annotations

from typing import Any

import discord


async def send_interaction(
    interaction: discord.Interaction,
    *,
    content: str | None = None,
    embed: discord.Embed | None = None,
    ephemeral: bool = False,
) -> Any:
    """Safely send or follow up to an interaction.

    Uses interaction.response when possible; falls back to followup if the
    initial response was already sent. Intended to reduce duplicated error
    handling around ``is_done()`` checks.
    """
    try:
        if interaction.response.is_done():
            if embed is not None:
                return await interaction.followup.send(content or "", embed=embed, ephemeral=ephemeral)
            return await interaction.followup.send(content or "", ephemeral=ephemeral)
        if embed is not None:
            return await interaction.response.send_message(content or "", embed=embed, ephemeral=ephemeral)
        return await interaction.response.send_message(content or "", ephemeral=ephemeral)
    except Exception:
        # Best-effort: swallow secondary failures to avoid masking original errors
        return None
