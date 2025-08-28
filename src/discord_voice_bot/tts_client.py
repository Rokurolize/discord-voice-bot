"""TTS API client for managing communication with TTS services."""

import asyncio
import json
import urllib.parse
from typing import Any

import aiohttp
from loguru import logger

from .config import Config


class TTSClient:
    """Manages TTS API communication and requests."""

    def __init__(self, config: Config) -> None:
        """Initialize TTS client with a configuration object."""
        self.config = config
        self._session: aiohttp.ClientSession | None = None

    @property
    def api_url(self) -> str:
        """Get current API URL from config."""
        if self.config.tts_engine not in self.config.engines:
            logger.warning(f"Configured TTS engine '{self.config.tts_engine}' not found in engines. Falling back to default URL.")
            return "http://localhost:50021"

        engine_config = self.config.engines.get(self.config.tts_engine, {})
        return engine_config.get("url", "http://localhost:50021")

    @property
    def speaker_id(self) -> int:
        """Get current speaker ID from config."""
        val = str(self.config.tts_speaker).strip()
        if val.isdigit():
            return int(val)
        engines = self.config.engines
        engine = self.config.tts_engine
        engine_cfg = engines.get(engine, {})  # MappingProxyType is dict-like
        speakers = engine_cfg.get("speakers", {}) if isinstance(engine_cfg, dict) else {}
        return int(speakers.get(val, engine_cfg.get("default_speaker", 3)))

    @property
    def engine_name(self) -> str:
        """Get current engine name from config."""
        return self.config.tts_engine.upper()

    @property
    def session(self) -> aiohttp.ClientSession | None:
        """Get HTTP session for testing purposes."""
        return self._session

    async def start_session(self) -> None:
        """Start the HTTP session for API communication."""
        if not self._session:
            logger.debug("🔗 Creating new aiohttp ClientSession for TTS client")
            timeout = aiohttp.ClientTimeout(total=10, connect=2)
            self._session = aiohttp.ClientSession(timeout=timeout)
            logger.debug("✅ aiohttp ClientSession created successfully")

    async def close_session(self) -> None:
        """Close the HTTP session."""
        if self._session:
            logger.debug("🔗 Closing aiohttp ClientSession for TTS client")
            await self._session.close()
            self._session = None
            logger.debug("✅ aiohttp ClientSession closed successfully")

    async def check_api_availability(self) -> tuple[bool, str]:
        """Check TTS API availability with detailed error information.

        Returns:
            (is_available, error_detail): Tuple of availability status and error description

        """
        if not self._session:
            await self.start_session()

        try:
            assert self._session is not None  # Type guard for mypy
            async with self._session.get(f"{self.api_url}/version") as response:
                if response.status == 200:
                    logger.debug(f"{self.engine_name} TTS API is available")
                    return True, ""
                else:
                    error_msg = f"HTTP {response.status}"
                    logger.warning(f"{self.engine_name} TTS API returned {error_msg}")
                    return False, error_msg

        except aiohttp.ClientConnectorError:
            error_msg = "connection refused - server not running"
            logger.error(f"{self.engine_name} TTS API: {error_msg}")
            return False, error_msg

        except asyncio.TimeoutError:
            error_msg = "connection timeout - server may be starting up"
            logger.error(f"{self.engine_name} TTS API: {error_msg}")
            return False, error_msg

        except Exception as e:
            error_msg = f"unexpected error: {type(e).__name__}"
            logger.error(f"{self.engine_name} TTS API: {error_msg} - {e!s}")
            return False, error_msg

    async def generate_audio_query(self, text: str, speaker_id: int, api_url: str) -> dict[str, Any] | None:
        """Generate audio query from text.

        Args:
            text: Text to generate query for
            speaker_id: Speaker ID to use
            api_url: API URL to use

        Returns:
            Audio query dictionary or None if failed

        """
        try:
            params = {"text": text, "speaker": speaker_id}
            url = f"{api_url}/audio_query?" + urllib.parse.urlencode(params)

            assert self._session is not None  # Type guard for mypy
            async with self._session.post(url) as response:
                if response.status != 200:
                    logger.error(f"Audio query failed with status {response.status}")
                    return None

                return await response.json()

        except Exception as e:
            logger.error(f"Failed to generate audio query: {e!s}")
            return None

    async def synthesize_from_query(self, audio_query: dict[str, Any], speaker_id: int, api_url: str) -> bytes | None:
        """Synthesize audio from audio query.

        Args:
            audio_query: Audio query dictionary
            speaker_id: Speaker ID to use
            api_url: API URL to use

        Returns:
            Synthesized audio data or None if failed

        """
        try:
            params = {"speaker": speaker_id}
            url = f"{api_url}/synthesis?" + urllib.parse.urlencode(params)

            headers = {"Content-Type": "application/json"}
            data = json.dumps(audio_query).encode("utf-8")

            assert self._session is not None  # Type guard for mypy
            async with self._session.post(url, data=data, headers=headers) as response:
                if response.status != 200:
                    logger.error(f"Audio synthesis failed with status {response.status}")
                    return None

                return await response.read()

        except Exception as e:
            logger.error(f"Failed to synthesize from query: {e!s}")
            return None

    async def synthesize_audio(self, text: str, speaker_id: int | None = None, engine_name: str | None = None) -> bytes | None:
        """Synthesize audio from text using the specified TTS engine.

        Args:
            text: Text to synthesize
            speaker_id: Optional speaker ID override
            engine_name: Optional engine name ('voicevox' or 'aivis')

        Returns:
            Audio data as bytes, or None if synthesis failed

        """
        # Check for empty text early
        if not text or not text.strip():
            logger.debug("Empty text provided, returning None")
            return None

        if not self._session:
            await self.start_session()

        # Determine engine and speaker
        target_engine = (engine_name or self.config.tts_engine).lower()
        engines = self.config.engines
        engine_config = engines.get(target_engine)
        if not engine_config:
            fallback = "voicevox" if "voicevox" in engines else (next(iter(engines.keys()), None))
            logger.error("Unknown TTS engine requested; target={} fallback={}", target_engine, fallback)
            if not fallback:
                logger.error("No TTS engines configured; aborting synthesis")
                return None
            target_engine = fallback
            engine_config = engines[target_engine]

        # Use provided speaker ID or engine default
        current_speaker_id = speaker_id or engine_config["default_speaker"]
        target_api_url = engine_config["url"]

        logger.debug(f"Using {target_engine} engine (URL: {target_api_url}) with speaker {current_speaker_id}")

        try:
            # Generate audio query using target engine
            audio_query = await self.generate_audio_query(text, current_speaker_id, target_api_url)
            if not audio_query:
                return None

            # Synthesize audio
            audio_data = await self.synthesize_from_query(audio_query, current_speaker_id, target_api_url)
            if not audio_data:
                return None

            logger.info(f"Successfully synthesized audio for text: '{text[:50]}...'")
            return audio_data

        except Exception as e:
            logger.error(f"Failed to synthesize audio: {type(e).__name__} - {e!s}")
            return None
