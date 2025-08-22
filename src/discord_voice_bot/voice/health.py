"""Health check utilities for voice operations."""

from typing import TYPE_CHECKING, Any

from loguru import logger

if TYPE_CHECKING:
    from .handler import VoiceHandler


async def health_check(voice_handler: "VoiceHandler") -> dict[str, Any]:
    """Perform comprehensive voice connection health check."""
    logger.debug("🔍 Performing voice connection health check...")

    health_status: dict[str, Any] = {
        "healthy": False,
        "issues": [],
        "recommendations": [],
        "voice_client_exists": voice_handler.voice_client is not None,
        "voice_client_connected": False,
        "channel_accessible": False,
        "can_synthesize": False,
        "audio_playback_ready": False,
    }

    # Check voice client
    if not voice_handler.voice_client:
        health_status["issues"].append("Voice client not initialized")
        health_status["recommendations"].append("Call connect_to_channel() to establish connection")
    else:
        # Check connection status
        try:
            is_connected = voice_handler.voice_client.is_connected()
            health_status["voice_client_connected"] = is_connected

            if not is_connected:
                health_status["issues"].append("Voice client not connected")
                health_status["recommendations"].append("Check voice channel permissions and network connectivity")
            else:
                logger.debug("✅ Voice client is connected")

                # Check channel accessibility
                if hasattr(voice_handler.voice_client, "channel") and voice_handler.voice_client.channel:
                    channel = voice_handler.voice_client.channel
                    health_status["channel_accessible"] = True
                    logger.debug(f"✅ Connected to channel: {channel.name} (ID: {channel.id})")

                    # Check if we can actually play audio
                    if not voice_handler.voice_client.is_playing():
                        health_status["audio_playback_ready"] = True
                        logger.debug("✅ Audio playback is ready")
                    else:
                        health_status["issues"].append("Audio is currently playing")
                        logger.debug("ℹ️ Audio is currently playing")
                else:
                    health_status["issues"].append("Voice client has no associated channel")
                    health_status["recommendations"].append("Voice client may be in disconnected state")

        except Exception as e:
            health_status["issues"].append(f"Error checking voice client: {e}")
            logger.debug(f"⚠️ Voice client check error: {e}")

    # Check TTS synthesis capability
    try:
        from ..tts_engine import tts_engine

        if await tts_engine.health_check():
            health_status["can_synthesize"] = True
            logger.debug("✅ TTS engine is healthy")
        else:
            health_status["issues"].append("TTS engine health check failed")
            health_status["recommendations"].append("Check TTS API availability and configuration")
    except Exception as e:
        health_status["issues"].append(f"TTS engine check failed: {e}")
        logger.debug(f"⚠️ TTS engine check error: {e}")

    # Overall health assessment
    critical_issues = [issue for issue in health_status["issues"] if any(keyword in issue.lower() for keyword in ["not initialized", "not connected", "failed", "error"])]

    if not critical_issues:
        health_status["healthy"] = True
        logger.debug("🎉 Voice system health check PASSED")
    else:
        logger.debug(f"💥 Voice system health check FAILED: {len(critical_issues)} critical issues")
        for issue in critical_issues:
            logger.debug(f"   - {issue}")

    return health_status
