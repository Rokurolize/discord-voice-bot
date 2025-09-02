"""TTS Engine integration for Discord Voice TTS Bot."""

import asyncio
import threading
from collections.abc import Mapping
from typing import Any
from weakref import WeakKeyDictionary, ref

__all__ = ["TTSEngine", "TTSEngineError", "get_tts_engine"]

from loguru import logger

from .audio_processor import AudioProcessor, AudioQuery
from .config import Config
from .temp_file_manager import TempFileManager
from .tts_client import TTSClient
from .tts_health_monitor import TTSHealthMonitor

# Weak cache of engines per Config to avoid repeated startups
_ENGINE_CACHE: "WeakKeyDictionary[Config, TTSEngine]" = WeakKeyDictionary()
# Creation lock must not be an asyncio lock (unsafe across event loops);
# use a short, non-IO critical section guarded by a thread lock.
_ENGINE_CREATE_LOCK = threading.RLock()


class TTSEngineError(Exception):
    """Exception raised when TTS engine encounters an error."""


class TTSEngine:
    """TTS Engine for synthesizing speech using VOICEVOX or AivisSpeech."""

    def __init__(self, config: Config) -> None:
        """
        Create a TTSEngine tied to a Config and instantiate its supporting components.

        The constructor stores a weak reference to `config` and initializes the engine's
        subsystems required for operation: the TTS client, audio processor, temporary
        file manager, and health monitor. It also initializes internal runtime state
        used to manage start/stop concurrency and preserves a session attribute for
        backward-compatible testing access.

        Args:
            config: Configuration object that controls engine behavior and
                provides values for constructing the client and manager components.

        """
        super().__init__()
        self._config_ref = ref(config)

        # Initialize manager components
        self._tts_client = TTSClient(config)
        self._audio_processor = AudioProcessor(config)
        self._temp_file_manager = TempFileManager(config, self._audio_processor)
        self._health_monitor = TTSHealthMonitor(config, self._tts_client)

        # Engine state management
        self._started = False
        self._lock = asyncio.Lock()

        # Backward compatibility: direct access to session for testing
        self._session = None

    @property
    def config(self) -> Config:
        """
        Return the live Config associated with this engine.

        If the underlying weak reference has been garbage-collected, raises TTSEngineError
        because the engine is no longer bound to a valid configuration.

        Returns:
            Config: The dereferenced configuration object.

        Raises:
            TTSEngineError: If the stored weak reference no longer points to a Config.

        """
        cfg = self._config_ref()
        if cfg is None:
            raise TTSEngineError("Config has been garbage-collected; engine is no longer bound")
        return cfg

    @property
    def api_url(self) -> str:
        """Get current API URL from TTS client."""
        return self._tts_client.api_url

    @property
    def speaker_id(self) -> int:
        """Get current speaker ID from TTS client."""
        return self._tts_client.speaker_id

    @property
    def engine_name(self) -> str:
        """Get current engine name from TTS client."""
        return self._tts_client.engine_name

    async def __aenter__(self) -> "TTSEngine":
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()

    async def start(self) -> None:
        """
        Start the TTS engine session.

        This is an idempotent async startup: acquires the engine's internal lock to ensure only
        one concurrent start occurs. If the engine is not already started, it starts the
        underlying TTS client session, marks the engine as started, and updates the stored
        session reference.

        No value is returned.
        """
        async with self._lock:
            if not self._started:
                await self._tts_client.start_session()
                self._started = True
                self._session = self._tts_client.session  # Update session reference
                logger.info("🎵 TTS Engine started successfully")

    async def close(self) -> None:
        """
        Close the TTS engine session.

        This async, idempotent method acquires the engine's internal lock and, if a session is active, closes it via the TTS client, clears the stored session reference, and marks the engine as not started. Safe to call concurrently.
        """
        async with self._lock:
            if self._started:
                await self._tts_client.close_session()
                self._started = False
                self._session = None
                logger.info("🎵 TTS Engine closed successfully")

    async def check_api_availability(self) -> tuple[bool, str]:
        """
        Check whether the configured TTS API is reachable and return any error details.

        Queries the underlying TTS client for availability and returns a two-tuple:
        - first element: True if the API is reachable and healthy, False otherwise
        - second element: an error description (empty string when available)

        Returns:
            tuple[bool, str]: (is_available, error_detail)

        """
        return await self._tts_client.check_api_availability()

    async def synthesize_audio(self, text: str, speaker_id: int | None = None, engine_name: str | None = None) -> bytes | None:
        """Synthesize audio from text using the specified TTS engine.

        Args:
            text: Text to synthesize
            speaker_id: Optional speaker ID override
            engine_name: Optional engine name ('voicevox' or 'aivis')

        Returns:
            Audio data as bytes, or None if synthesis failed

        """
        logger.debug(f"synthesize_audio called with text: '{text}' (length: {len(text)})")

        # Check for empty text early
        if not text or not text.strip():
            logger.debug("Empty text provided, returning None")
            return None

        # Ensure engine is started
        if not self._started:
            logger.debug("Engine not started, starting automatically...")
            await self.start()

        try:
            # Generate audio query using TTS client
            audio_query = await self._generate_audio_query(text, speaker_id, engine_name)
            if not audio_query:
                return None

            # Optimize audio parameters for Discord
            self._audio_processor.optimize_audio_parameters(audio_query)

            # Synthesize audio using TTS client
            audio_data = await self._synthesize_from_query(audio_query, speaker_id, engine_name)
            if not audio_data:
                return None

            # DEBUG: Save raw TTS output for analysis (only when enabled)
            if getattr(self.config, "debug", False):
                try:
                    from .audio_debugger import audio_debugger

                    metadata = {
                        "speaker_id": speaker_id or self.speaker_id,
                        "engine": engine_name or self.engine_name,
                        "original_length": len(text),
                    }
                    saved_path = audio_debugger.save_audio_stage(audio_data, "tts_raw", text, metadata)
                    logger.debug(f"🔍 Saved raw TTS audio for debugging: {saved_path}")
                except Exception as e:
                    logger.debug(f"Skipping debug audio save: {e}")

            logger.info(f"Successfully synthesized audio for text: '{text[:50]}...'")
            return audio_data

        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"Failed to synthesize audio: {type(e).__name__} - {e!s}")
            return None

    async def _generate_audio_query(self, text: str, speaker_id: int | None = None, engine_name: str | None = None) -> AudioQuery | None:
        """
        Build an AudioQuery for the given text, resolving engine and speaker defaults from the configuration.

        Determines which TTS engine to use (explicit engine_name or config.tts_engine, with a 'voicevox' fallback),
        resolves a concrete speaker ID (coercing provided speaker_id to int or mapping config.tts_speaker through
        the engine's speakers with sensible fallbacks), validates the engine URL, and delegates to the TTS client
        to generate and return the AudioQuery.

        Args:
            text: Input text to turn into an audio query.
            speaker_id: Optional explicit speaker id; if provided it will be coerced to int. If coercion fails
                a sensible default from the engine config is used.
            engine_name: Optional engine key to select a configured engine. If not found, the function
                falls back to the config entry "voicevox" when available.

        Returns:
            AudioQuery | None: The generated AudioQuery from the TTS client, or None if the client returns no result.

        Raises:
            TTSEngineError: If no suitable engine is found (neither the requested engine nor a 'voicevox' fallback)
                or if the resolved engine configuration lacks a 'url'.

        """
        _engine_config, current_speaker_id, target_api_url = self._resolve_engine_and_speaker(speaker_id, engine_name)
        result = await self._tts_client.generate_audio_query(text, current_speaker_id, target_api_url)
        return result  # type: ignore[return-value]

    async def _synthesize_from_query(self, audio_query: AudioQuery, speaker_id: int | None = None, engine_name: str | None = None) -> bytes | None:
        """
        Synthesize PCM audio bytes from an AudioQuery using the resolved TTS engine and speaker.

        Generates audio by resolving which engine configuration to use (explicit engine_name or the engine from the current Config,
        falling back to a 'voicevox' engine if available), determines the effective speaker ID (coercing provided values or mapping
        the configured speaker name to the engine's speaker table with sensible fallbacks), validates the engine URL, and delegates
        synthesis to the TTS client.

        Args:
            audio_query: Precomputed audio query object describing phoneme/timing information to synthesize.
            speaker_id: Optional speaker identifier. If provided it will be coerced to int; invalid values fall back to
                the engine's default speaker or 3. If omitted, the engine's `speakers` mapping and the Config.tts_speaker name are used.
            engine_name: Optional engine key to select a specific engine configuration from Config.engines. If omitted
                the engine from Config.tts_engine is used; if that is unavailable, a 'voicevox' entry is used as a fallback.

        Returns:
            bytes | None: Raw synthesized PCM audio bytes on success, or None if the underlying client returns None.

        Raises:
            TTSEngineError: If no suitable engine configuration is found or if the selected engine is missing a 'url'.

        """
        _engine_config, current_speaker_id, target_api_url = self._resolve_engine_and_speaker(speaker_id, engine_name)
        return await self._tts_client.synthesize_from_query(audio_query, current_speaker_id, target_api_url)  # type: ignore[arg-type]

    def _resolve_engine_and_speaker(self, speaker_id: int | None, engine_name: str | None) -> tuple[Mapping[str, Any], int, str]:
        raw_engine = engine_name if engine_name is not None else self.config.tts_engine
        target_engine = str(raw_engine).strip().lower()
        engines = self.config.engines
        engine_config = engines.get(target_engine) or engines.get("voicevox")
        if engine_config is None:
            raise TTSEngineError(f"Unknown TTS engine '{target_engine}' and no 'voicevox' fallback configured")
        if speaker_id is not None:
            try:
                resolved_speaker = int(speaker_id)
            except (TypeError, ValueError):
                ds = engine_config.get("default_speaker", 3)
                resolved_speaker = int(ds) if str(ds).isdigit() else 3
        else:
            speakers = engine_config.get("speakers", {})
            desired = str(getattr(self.config, "tts_speaker", "")).strip().lower()
            raw = speakers.get(desired, engine_config.get("default_speaker"))
            try:
                resolved_speaker = int(raw)
            except (TypeError, ValueError):
                ds = engine_config.get("default_speaker", 3)
                resolved_speaker = int(ds) if str(ds).isdigit() else 3
        url = engine_config.get("url")
        if not url:
            raise TTSEngineError(f"Engine '{target_engine}' is missing 'url' in config")
        return engine_config, resolved_speaker, url

    async def create_audio_source(self, text: str, speaker_id: int | None = None, engine_name: str | None = None) -> Any:
        """Create Discord audio source from text using temp file manager.

        Args:
            text: Text to synthesize
            speaker_id: Optional speaker ID override
            engine_name: Optional engine name ('voicevox' or 'aivis')

        Returns:
            Discord audio source, or None if creation failed

        """
        # Synthesize audio first
        audio_data = await self.synthesize_audio(text, speaker_id, engine_name)
        if not audio_data:
            return None

        # Create audio source using temp file manager
        return await self._temp_file_manager.create_audio_source(text, audio_data, speaker_id, engine_name)

    def _create_wav_header(self, data_size: int, sample_rate: int, channels: int) -> bytes:
        """Create WAV file header for raw PCM data.

        Args:
            data_size: Size of PCM data in bytes
            sample_rate: Sample rate in Hz
            channels: Number of audio channels

        Returns:
            WAV header as bytes

        """
        import struct

        # WAV file constants
        bits_per_sample = 16  # 16-bit PCM
        byte_rate = sample_rate * channels * (bits_per_sample // 8)
        block_align = channels * (bits_per_sample // 8)

        # WAV header structure
        header = struct.pack(
            "<4sL4s",  # RIFF header
            b"RIFF",  # Chunk ID
            36 + data_size,  # Chunk size
            b"WAVE",
        )  # Format

        header += struct.pack(
            "<4sLHHLLHH",  # fmt subchunk
            b"fmt ",  # Subchunk1 ID
            16,  # Subchunk1 size
            1,  # Audio format (PCM)
            channels,  # Number of channels
            sample_rate,  # Sample rate
            byte_rate,  # Byte rate
            block_align,  # Block align
            bits_per_sample,
        )  # Bits per sample

        header += struct.pack("<4sL", b"data", data_size)  # data subchunk header  # Subchunk2 ID  # Subchunk2 size

        return header

    def cleanup_audio_source(self, audio_source: Any) -> None:
        """Clean up temporary files from audio source using temp file manager."""
        self._temp_file_manager.cleanup_audio_source(audio_source)

    def get_available_speakers(self) -> dict[str, int]:
        """
        Return the available speaker name→ID mapping for the engine selected in the current config.

        Looks up the engine configuration for self.config.tts_engine and returns its "speakers" mapping as a plain dict. If the selected engine or its "speakers" entry is missing, an empty dict is returned.
        """
        engine_key = str(self.config.tts_engine).strip().lower()
        engine_config = self.config.engines.get(engine_key, {})
        return dict(engine_config.get("speakers", {}))

    async def health_check(self) -> bool:
        """Perform health check on TTS engine using health monitor."""
        return await self._health_monitor.perform_health_check()


async def get_tts_engine(config: Config) -> TTSEngine:
    """
    Return a started TTSEngine for the given Config, creating and caching one per-Config if necessary.

    This function reuses an existing TTSEngine from a module-level cache when available; if not, it creates and caches a new instance. Engine creation is serialized with a short, thread-safe lock to avoid duplicate construction across threads/event loops. The engine's async startup (engine.start()) is always awaited outside that creation lock so I/O-heavy initialization does not hold the creation lock.

    Returns:
        TTSEngine: A TTSEngine that has been started.

    """
    engine: TTSEngine | None = _ENGINE_CACHE.get(config)
    if engine is None:
        with _ENGINE_CREATE_LOCK:
            engine = _ENGINE_CACHE.get(config)
            if engine is None:
                engine = TTSEngine(config)
                _ENGINE_CACHE[config] = engine
    # Ensure started outside the global creation lock
    await engine.start()
    return engine
