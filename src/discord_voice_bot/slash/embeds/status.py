"""Status embed creation for slash commands."""

from typing import Any

import discord

from ...config import Config


async def create_status_embed(status: dict[str, Any], config: Config) -> discord.Embed:
    """
    Create a Discord embed summarizing the bot's current status.
    
    Parameters
        status (dict[str, Any]): Status payload. Expected keys:
            - "voice_status" (dict, optional): May contain "connected" (bool),
              "channel_name" (str), "is_playing" (bool), and "queue_size" (int).
            - "messages_processed" (int, optional)
            - "uptime_formatted" (str, optional)
            - "connection_errors" (int, optional)
        config (Config): Configuration object exposing `tts_engine` and `tts_speaker`
            attributes used to display TTS engine and speaker.
    
    Returns
        discord.Embed: An embed with fields for connection, TTS, queue, and bot info.
        - Embed color is green when voice is connected, otherwise red.
        - First three status fields are added inline.

    """
    embed = discord.Embed(
        title="🤖 Discord Voice TTS Bot Status",
        color=(discord.Color.green() if status.get("voice_status", {}).get("connected") else discord.Color.red()),
        description="ずんだもんボイス読み上げBot",
    )

    # Connection status
    voice_status = status.get("voice_status", {})
    _ = embed.add_field(
        name="🔗 接続状態",
        value=f"Voice: {'✅ 接続中' if voice_status.get('connected') else '❌ 未接続'}\nChannel: {voice_status.get('channel_name') or 'なし'}",
        inline=True,
    )

    # TTS status
    engine = getattr(config, "tts_engine", None)
    speaker = getattr(config, "tts_speaker", None)
    engine_display = engine.upper() if engine else "Unknown"
    speaker_display = speaker if speaker else "Unknown"
    _ = embed.add_field(
        name="🎤 TTS状態",
        value=f"Engine: {engine_display}\nSpeaker: {speaker_display}\nPlaying: {'✅' if voice_status.get('is_playing') else '❌'}",
        inline=True,
    )

    # Queue status
    _ = embed.add_field(
        name="📋 キュー状態",
        value=f"Ready: {voice_status.get('queue_size', 0)} chunks\nTotal: {voice_status.get('queue_size', 0)}\nProcessed: {status.get('messages_processed', 0)}",
        inline=True,
    )

    # Bot info
    _ = embed.add_field(
        name="ℹ️ Bot情報",
        value=f"Uptime: {status.get('uptime_formatted', 'Unknown')}\nErrors: {status.get('connection_errors', 0)}",
        inline=True,
    )

    return embed


async def create_basic_status_embed() -> discord.Embed:
    """Create basic status embed when status manager is not available."""
    embed = discord.Embed(title="🤖 Discord Voice TTS Bot Status", color=discord.Color.blue(), description="Status information unavailable")

    _ = embed.add_field(name="ℹ️ Status", value="Basic status information is currently unavailable.\nThe bot may still be starting up or experiencing issues.", inline=False)

    return embed
