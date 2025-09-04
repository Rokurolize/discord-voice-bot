from __future__ import annotations

from typing import Any

import discord
from loguru import logger


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
        # Avoid 400 Bad Request when nothing to send
        if content is None and embed is None:
            logger.warning("send_interaction: no content/embed; skip sending to avoid 400")
            return None
        if interaction.response.is_done():
            if embed is not None:
                return await interaction.followup.send(content or "", embed=embed, ephemeral=ephemeral)
            return await interaction.followup.send(content or "", ephemeral=ephemeral)
        if embed is not None:
            return await interaction.response.send_message(content or "", embed=embed, ephemeral=ephemeral)
        return await interaction.response.send_message(content or "", ephemeral=ephemeral)
    except discord.HTTPException as e:
        logger.exception(f"send_interaction: HTTPException: {e}")
        return None
    except Exception:
        logger.exception("send_interaction: unexpected exception")
        return None
