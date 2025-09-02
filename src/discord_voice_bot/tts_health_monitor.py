"""Health monitoring for TTS engine."""

from typing import Any
from weakref import ref

from loguru import logger

from .config import Config
from .tts_client import TTSClient


class TTSHealthMonitor:
    """Monitors the health of TTS engine components."""

    def __init__(self, config: Config, tts_client: TTSClient) -> None:
        """
        Initialize the TTS health monitor.

        Stores a weak reference to the provided Config (so the monitor does not extend its lifetime)
        and keeps a reference to the TTS client used for health checks.
        """
        super().__init__()
        self._config_ref = ref(config)
        self._tts_client = tts_client

    @property
    def config(self) -> Config:
        """
        Return the currently bound Config instance.

        Resolves the internally stored weak reference to the Config and returns it.
        Raises a RuntimeError if the Config has been garbage-collected, indicating
        the monitor is no longer bound to a valid configuration.

        Returns:
            Config: The live configuration object.

        Raises:
            RuntimeError: If the underlying Config has been garbage-collected.

        """
        cfg = self._config_ref()
        if cfg is None:
            raise RuntimeError("Config has been garbage-collected; TTSHealthMonitor is unbound")
        return cfg

    async def perform_health_check(self) -> bool:
        """
        Run a two-step health check for the TTS engine.

        Performs an API availability check followed by a brief synthesis test. If either step fails
        or an unexpected exception occurs, the method returns False; returns True only if both checks pass.

        Returns:
            bool: True when both API and synthesis checks succeed, False otherwise.

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
        """
        Return a list of diagnostic messages describing potential TTS engine issues.

        Performs a sequence of checks: API availability, a test synthesis, and validation of configured engines.
        Each discovered problem is appended as a human-readable message (including suggested actions). Any unexpected
        exception during diagnosis is caught and added to the returned list as an error entry — the function always
        returns a list of diagnostic strings.
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
                engines = self.config.engines
                if not engines:
                    issues.append("🔴 No TTS engines configured")
                    issues.append("   💡 Check configuration file for engine settings")
                else:
                    # Check each engine configuration
                    for engine_name, engine_config in engines.items():
                        url = engine_config.get("url")
                        default_speaker = engine_config.get("default_speaker")

                        if not url:
                            issues.append(f"🔴 Engine '{engine_name}' missing URL configuration")
                        try:
                            _ = int(default_speaker)
                        except (TypeError, ValueError):
                            issues.append(f"🔴 Engine '{engine_name}' missing default speaker")
            except Exception as e:
                issues.append(f"🔴 Configuration error: {e}")

            if not issues:
                issues.append("✅ No issues detected - TTS engine appears healthy")

        except Exception as e:
            issues.append(f"🔴 Diagnostic error: {e}")

        return issues
