from __future__ import annotations

from typing import Any

import discord
from discord.ext import commands


class EventBridge(commands.Cog):
    """Bridges discord.py events to the existing EventHandler.

    This Cog provides idiomatic event listeners while keeping backward
    compatibility with the current EventHandler facade. It allows us to
    gradually migrate to Cog-based listeners without breaking existing
    tests or wiring.
    """

    def __init__(self, bot: commands.Bot) -> None:
        super().__init__()
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        handler = getattr(self.bot, "event_handler", None)
        if handler and hasattr(handler, "handle_ready"):
            await handler.handle_ready()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        handler = getattr(self.bot, "event_handler", None)
        if handler and hasattr(handler, "handle_message"):
            await handler.handle_message(message)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: Any, before: Any, after: Any) -> None:
        handler = getattr(self.bot, "event_handler", None)
        if handler and hasattr(handler, "handle_voice_state_update"):
            await handler.handle_voice_state_update(member, before, after)

    @commands.Cog.listener()
    async def on_disconnect(self) -> None:
        handler = getattr(self.bot, "event_handler", None)
        if handler and hasattr(handler, "handle_disconnect"):
            await handler.handle_disconnect()

    @commands.Cog.listener()
    async def on_resumed(self) -> None:
        handler = getattr(self.bot, "event_handler", None)
        if handler and hasattr(handler, "handle_resumed"):
            await handler.handle_resumed()

