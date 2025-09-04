from __future__ import annotations

from typing import Any, cast

import discord
from discord.ext import commands


class EventBridge(commands.Cog):
    """Cog-based event listeners wired directly to manager components.

    Replaces the EventHandler facade by instantiating and delegating to the
    existing managers (StartupManager, MessageHandler, ConnectionHandler).
    """

    def __init__(self, bot: Any) -> None:
        super().__init__()
        self.bot = bot

        # Type helpers
        from ..protocols import ConfigManager, StartupBot

        # Obtain the bot's ConfigManager (DiscordVoiceTTSBot sets this)
        cm_any = getattr(bot, "config_manager", None)
        if cm_any is None:
            # Fallback to build from Config if necessary
            from ..config import Config
            from ..config_manager import ConfigManagerImpl

            raw_cfg: Any = getattr(bot, "config", None)
            cfg: Any = raw_cfg() if callable(raw_cfg) else raw_cfg
            if not isinstance(cfg, Config):
                cfg = Config.from_env()
            self.config_manager = cast(ConfigManager, ConfigManagerImpl(cfg))
        else:
            self.config_manager = cast(ConfigManager, cm_any)

        # Lazy imports to avoid cycles at module import time
        from ..event_connection_handler import ConnectionHandler
        from ..event_message_handler import MessageHandler
        from ..event_startup_manager import StartupManager

        # Instantiate managers
        self.startup_manager = StartupManager(cast(StartupBot, bot), self.config_manager)
        self.message_handler = MessageHandler(bot, self.config_manager)
        self.connection_handler = ConnectionHandler(bot, self.config_manager)
        # Propagate target channel to connection handler
        target_id = self.config_manager.get_target_voice_channel_id() if self.config_manager else 0
        self.connection_handler.set_target_channel_id(target_id)

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        await self.startup_manager.handle_startup()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        await self.message_handler.handle_message(message)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: Any, before: Any, after: Any) -> None:
        await self.connection_handler.handle_voice_state_update(member, before, after)

    @commands.Cog.listener()
    async def on_disconnect(self) -> None:
        await self.connection_handler.handle_disconnect()

    @commands.Cog.listener()
    async def on_resumed(self) -> None:
        await self.connection_handler.handle_resumed()
