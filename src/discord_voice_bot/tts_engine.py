"""TTS Engine integration for Discord Voice TTS Bot."""

from typing import Any

__all__ = ["TTSEngine", "TTSEngineError", "get_tts_engine"]

from loguru import logger

from .audio_processor import AudioProcessor, AudioQuery
from .config import Config
from .temp_file_manager import TempFileManager
from .tts_client import TTSClient
from .tts_health_monitor import TTSHealthMonitor


class TTSEngineError(Exception):
    """Exception raised when TTS engine encounters an error."""


class TTSEngine:
    """TTS Engine for synthesizing speech using VOICEVOX or AivisSpeech."""

    def __init__(self, config: Config) -> None:
        """Initialize TTS engine with configuration and managers."""
        super().__init__()
        self.config = config

        # Initialize manager components
        self._tts_client = TTSClient(config)
        self._audio_processor = AudioProcessor(config)
        self._temp_file_manager = TempFileManager(config, self._audio_processor)
        self._health_monitor = TTSHealthMonitor(config, self._tts_client)

        # Engine state management
        self._started = False

        # Backward compatibility: direct access to session for testing
        self._session = None

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
        """Start the TTS engine session."""
        if not self._started:
            await self._tts_client.start_session()
            self._started = True
            self._session = self._tts_client.session  # Update session reference
            logger.info("🎵 TTS Engine started successfully")

    async def close(self) -> None:
        """Close the TTS engine session."""
        if self._started:
            await self._tts_client.close_session()
            self._started = False
            self._session = None
            logger.info("🎵 TTS Engine closed successfully")

    async def check_api_availability(self) -> tuple[bool, str]:
        """Check TTS API availability with detailed error information.

        Returns:
            (is_available, error_detail): Tuple of availability status and error description

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

            # DEBUG: Save raw TTS output for analysis
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
                logger.warning(f"Failed to save debug audio: {e}")

            logger.info(f"Successfully synthesized audio for text: '{text[:50]}...'")
            return audio_data

        except Exception as e:
            logger.error(f"Failed to synthesize audio: {type(e).__name__} - {e!s}")
            return None

    async def _generate_audio_query(self, text: str, speaker_id: int | None = None, engine_name: str | None = None) -> AudioQuery | None:
        """Generate audio query from text using TTS client."""
        # Determine engine and speaker
        target_engine = engine_name or self.config.tts_engine
        engines = self.config.engines
        engine_config = engines.get(target_engine, engines["voicevox"])

        # Use provided speaker ID or engine default
        current_speaker_id = speaker_id or engine_config["default_speaker"]
        target_api_url = engine_config["url"]

        result = await self._tts_client.generate_audio_query(text, current_speaker_id, target_api_url)
        return result  # type: ignore[return-value]

    async def _synthesize_from_query(self, audio_query: AudioQuery, speaker_id: int | None = None, engine_name: str | None = None) -> bytes | None:
        """Synthesize audio from audio query using TTS client."""
        # Determine engine and speaker
        target_engine = engine_name or self.config.tts_engine
        engines = self.config.engines
        engine_config = engines.get(target_engine, engines["voicevox"])

        # Use provided speaker ID or engine default
        current_speaker_id = speaker_id or engine_config["default_speaker"]
        target_api_url = engine_config["url"]

        return await self._tts_client.synthesize_from_query(audio_query, current_speaker_id, target_api_url)  # type: ignore[arg-type]

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

    async def get_available_speakers(self) -> dict[str, int]:
        """Get available speakers for current engine.

        Returns:
            Dictionary mapping speaker names to IDs

        """
        engine_config = self.config.engines.get(self.config.tts_engine, {})
        return engine_config.get("speakers", {}).copy()

    async def health_check(self) -> bool:
        """Perform health check on TTS engine using health monitor."""
        return await self._health_monitor.perform_health_check()


async def get_tts_engine(config: Config) -> TTSEngine:
    """Create and start new TTS engine instance with a config object."""
    engine = TTSEngine(config)
    await engine.start()
    return engine
