"""Status utilities for voice operations."""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .handler import VoiceHandlerInterface


def build_status(voice_handler: "VoiceHandlerInterface") -> dict[str, Any]:
    """Build status information for voice handler."""
    connected = bool(voice_handler.voice_client and voice_handler.voice_client.is_connected())
    channel_name = None
    channel_id = None

    try:
        if voice_handler.voice_client and getattr(voice_handler.voice_client, "channel", None):
            channel_name = voice_handler.voice_client.channel.name
            channel_id = voice_handler.voice_client.channel.id
        elif voice_handler.target_channel:
            channel_name = voice_handler.target_channel.name
            channel_id = voice_handler.target_channel.id
    except Exception as e:
        from loguru import logger

        logger.debug(f"Error getting channel info: {e}")

    return {
        "connected": connected,
        "voice_connected": connected,  # compatibility for UI/status uses
        "voice_channel_name": channel_name,
        "voice_channel_id": channel_id,
        "playing": voice_handler.is_playing,
        "synthesis_queue_size": voice_handler.synthesis_queue.qsize(),
        "audio_queue_size": voice_handler.audio_queue.qsize(),
        "total_queue_size": voice_handler.synthesis_queue.qsize() + voice_handler.audio_queue.qsize(),
        "current_group": voice_handler.current_group_id,
        "messages_played": voice_handler.stats.get("messages_played", 0),
        "messages_skipped": voice_handler.stats.get("messages_skipped", 0),
        "errors": voice_handler.stats.get("errors", 0),
        "connection_state": voice_handler.connection_state,
        "is_playing": voice_handler.is_playing,
        "max_queue_size": 50,  # Add max queue size for UI
    }
