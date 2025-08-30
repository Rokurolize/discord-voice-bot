"""Status embed creation for slash commands."""

from typing import Any

import discord

from ...config import Config


async def create_status_embed(status: dict[str, Any], config: Config) -> discord.Embed:
    """Create status embed from status data."""
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
