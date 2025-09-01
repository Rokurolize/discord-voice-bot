"""Health monitoring for voice handler."""

from typing import Any

from loguru import logger

from ..protocols import ConfigManager
from ..tts_client import TTSClient


class HealthMonitor:
    """Monitors the health of voice-related components."""

    def __init__(self, connection_manager: Any, config_manager: ConfigManager, tts_client: TTSClient) -> None:
        """
        Initialize HealthMonitor and store references to required managers and clients.
        
        Stores the provided managers/clients on the instance for use by health checks:
        - connection_manager: provider of the voice client and connection state
        - _config_manager: configuration manager
        - _tts_client: text-to-speech client used to verify TTS API availability
        """
        super().__init__()
        self.connection_manager = connection_manager
        self._config_manager = config_manager
        self._tts_client = tts_client

    async def perform_health_check(self) -> dict[str, Any]:
        """
        Perform a comprehensive health check of the voice subsystem and return a diagnostics report.
        
        The check inspects:
        - Presence and connection state of the voice client, whether it is associated with a channel,
          and whether audio playback is currently free/ready.
        - Availability of the configured TTS API via the TTS client.
        
        All runtime errors encountered during checks are recorded in the returned report under "issues" (the function does not propagate those exceptions).
        
        Returns:
            dict[str, Any]: A health report with the following keys:
                - healthy (bool): True if voice client is connected, channel is accessible, and TTS is available.
                - issues (list[str]): Collected human-readable issues found during the checks.
                - recommendations (list[str]): Suggested remediation steps for detected issues.
                - voice_client_exists (bool): Whether a voice client instance is present.
                - voice_client_connected (bool): Whether the voice client reports being connected.
                - channel_accessible (bool): Whether the voice client is associated with an accessible channel.
                - can_synthesize (bool): Whether the TTS API was reported healthy by the TTS client.
                - audio_playback_ready (bool): True when the voice client is connected and not currently playing audio.
        """
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
            api_healthy, error_detail = await self._tts_client.check_api_availability()
            if api_healthy:
                health_status["can_synthesize"] = True
                logger.debug("✅ TTS API is healthy")
            else:
                health_status["issues"].append(f"TTS API health check failed: {error_detail}")
                health_status["recommendations"].append("Check TTS API availability and configuration")
        except Exception as e:
            health_status["issues"].append(f"TTS API check failed: {e}")
            logger.debug(f"⚠️ TTS engine check error: {e}")

        # Overall health assessment
        health_status["healthy"] = health_status["voice_client_connected"] and health_status["channel_accessible"] and health_status["can_synthesize"]

        if health_status["healthy"]:
            logger.debug("🎉 Voice system health check PASSED")
        else:
            # Create a list of specific reasons for failure
            failure_reasons: list[str] = []
            if not health_status["voice_client_connected"]:
                failure_reasons.append("Voice client not connected")
            if not health_status["channel_accessible"]:
                failure_reasons.append("Voice channel not accessible")
            if not health_status["can_synthesize"]:
                failure_reasons.append("TTS API not available")

            logger.debug(f"💥 Voice system health check FAILED: {', '.join(failure_reasons)}")

        return health_status
