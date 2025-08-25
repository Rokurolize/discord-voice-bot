"""Health monitoring for voice handler."""

from typing import Any

from loguru import logger

from ..protocols import ConfigManager


class HealthMonitor:
    """Monitors the health of voice-related components."""

    def __init__(self, connection_manager: Any, config_manager: ConfigManager) -> None:
        """Initialize health monitor."""
        super().__init__()
        self.connection_manager = connection_manager
        self._config_manager = config_manager

    async def perform_health_check(self) -> dict[str, Any]:
        """Perform comprehensive voice system health check."""
        logger.debug("🔍 Performing voice connection health check...")

        health_status: dict[str, Any] = {
            "healthy": False,
            "issues": [],
            "recommendations": [],
            "voice_client_exists": False,
            "voice_client_connected": False,
            "channel_accessible": False,
            "can_synthesize": False,
            "audio_playback_ready": False,
        }

        # Check voice client
        voice_client = self.connection_manager.voice_client
        health_status["voice_client_exists"] = voice_client is not None

        if not voice_client:
            health_status["issues"].append("Voice client not initialized")
            health_status["recommendations"].append("Call connect_to_channel() to establish connection")
        else:
            try:
                is_connected = voice_client.is_connected()
                health_status["voice_client_connected"] = is_connected

                if not is_connected:
                    health_status["issues"].append("Voice client not connected")
                    health_status["recommendations"].append("Check voice channel permissions and network connectivity")
                else:
                    logger.debug("✅ Voice client is connected")

                    if hasattr(voice_client, "channel") and voice_client.channel:
                        channel = voice_client.channel
                        health_status["channel_accessible"] = True
                        logger.debug(f"✅ Connected to channel: {channel.name} (ID: {channel.id})")

                        if not voice_client.is_playing():
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
            from ..config_manager import ConfigManagerImpl
            from ..tts_engine import get_tts_engine

            config_manager = ConfigManagerImpl()
            tts_engine = await get_tts_engine(config_manager)

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
