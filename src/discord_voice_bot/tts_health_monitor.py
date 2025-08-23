"""Health monitoring for TTS engine."""

from typing import Any

from loguru import logger

from .protocols import ConfigManager
from .tts_client import TTSClient


class TTSHealthMonitor:
    """Monitors the health of TTS engine components."""

    def __init__(self, config_manager: ConfigManager, tts_client: TTSClient) -> None:
        """Initialize TTS health monitor with configuration and TTS client."""
        super().__init__()
        self._config_manager = config_manager
        self._tts_client = tts_client

    async def perform_health_check(self) -> bool:
        """Perform comprehensive health check on TTS engine.

        Returns:
            True if TTS engine is healthy, False otherwise

        """
        try:
            # Check API availability
            if not await self._check_api_health():
                return False

            # Test synthesis with a simple phrase
            if not await self._test_synthesis():
                return False

            logger.info("TTS health check passed")
            return True

        except Exception as e:
            logger.error(f"TTS health check failed: {e!s}")
            return False

    async def _check_api_health(self) -> bool:
        """Check if TTS API is available and responding.

        Returns:
            True if API is healthy, False otherwise

        """
        try:
            is_available, error_detail = await self._tts_client.check_api_availability()

            if not is_available:
                logger.warning(f"TTS API health check failed: {error_detail}")
                return False

            return True

        except Exception as e:
            logger.error(f"Error checking TTS API health: {e!s}")
            return False

    async def _test_synthesis(self) -> bool:
        """Test actual audio synthesis to ensure TTS engine is working.

        Returns:
            True if synthesis test passes, False otherwise

        """
        try:
            # Use a very simple test phrase to minimize resource usage
            test_audio = await self._tts_client.synthesize_audio("test")

            if not test_audio:
                logger.warning("TTS health check failed: unable to synthesize test audio")
                return False

            # Basic validation of the audio data
            if len(test_audio) < 100:  # Very small minimum size
                logger.warning(f"TTS health check failed: synthesized audio too small ({len(test_audio)} bytes)")
                return False

            return True

        except Exception as e:
            logger.error(f"Error testing TTS synthesis: {e!s}")
            return False

    async def get_health_status(self) -> dict[str, Any]:
        """Get detailed health status of TTS engine.

        Returns:
            Dictionary with health status information

        """
        health_status: dict[str, Any] = {
            "healthy": False,
            "api_available": False,
            "synthesis_working": False,
            "last_check": None,
            "issues": [],
        }

        try:
            # Check API availability
            api_available, error_detail = await self._tts_client.check_api_availability()
            health_status["api_available"] = api_available

            if not api_available:
                health_status["issues"].append(f"API not available: {error_detail}")

            # Test synthesis
            test_audio = await self._tts_client.synthesize_audio("test")
            synthesis_working = test_audio is not None and len(test_audio) > 100
            health_status["synthesis_working"] = synthesis_working

            if not synthesis_working:
                health_status["issues"].append("Audio synthesis test failed")

            # Overall health
            health_status["healthy"] = api_available and synthesis_working
            health_status["last_check"] = __import__("time").time()

            if health_status["healthy"]:
                logger.debug("TTS health status: ✅ Healthy")
            else:
                logger.warning(f"TTS health status: ❌ Issues found - {health_status['issues']}")

            return health_status

        except Exception as e:
            health_status["issues"].append(f"Health check error: {e!s}")
            logger.error(f"Error getting TTS health status: {e!s}")
            return health_status

    async def diagnose_issues(self) -> list[str]:
        """Diagnose and return a list of potential issues with TTS engine.

        Returns:
            List of diagnostic messages and suggestions

        """
        issues: list[str] = []

        try:
            # Check API availability
            api_available, error_detail = await self._tts_client.check_api_availability()

            if not api_available:
                issues.append(f"🔴 API connectivity issue: {error_detail}")
                issues.append("   💡 Check if TTS engine (VOICEVOX/AivisSpeech) is running")
                issues.append("   💡 Verify the API URL is correct")
                issues.append("   💡 Check if the port is not blocked by firewall")

            # Test synthesis
            test_audio = await self._tts_client.synthesize_audio("test")
            if not test_audio:
                issues.append("🔴 Audio synthesis failed")
                issues.append("   💡 Check TTS engine configuration")
                issues.append("   💡 Verify speaker ID is valid")
                issues.append("   💡 Check if TTS engine has sufficient resources")

            # Check configuration
            try:
                engines = self._config_manager.get_engines()
                if not engines:
                    issues.append("🔴 No TTS engines configured")
                    issues.append("   💡 Check configuration file for engine settings")
                else:
                    # Check each engine configuration
                    for engine_name, engine_config in engines.items():
                        if "url" not in engine_config:
                            issues.append(f"🔴 Engine '{engine_name}' missing URL configuration")
                        if "default_speaker" not in engine_config:
                            issues.append(f"🔴 Engine '{engine_name}' missing default speaker")
            except Exception as e:
                issues.append(f"🔴 Configuration error: {e}")

            if not issues:
                issues.append("✅ No issues detected - TTS engine appears healthy")

        except Exception as e:
            issues.append(f"🔴 Diagnostic error: {e}")

        return issues
