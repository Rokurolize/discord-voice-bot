"""Audio processing and optimization for TTS engine."""

from typing import TypedDict
from weakref import ref

from loguru import logger

from .config import Config


class AudioQuery(TypedDict, total=False):
    """TypedDict for audio query parameters with optional fields."""

    outputSamplingRate: int
    volumeScale: float
    speedScale: float
    pitchScale: float
    intonationScale: float


class AudioFormatInfo(TypedDict):
    """TypedDict for audio format information."""

    sample_rate: int
    channels: int
    bits_per_sample: int
    format: str
    byte_rate: int
    block_align: int


class AudioProcessor:
    """Handles audio processing and optimization for TTS."""

    def __init__(self, config: Config) -> None:
        """Initialize audio processor with a configuration object."""
        super().__init__()
        self._config_ref = ref(config)

    @property
    def config(self) -> Config:
        cfg = self._config_ref()
        if cfg is None:
            raise RuntimeError("Config has been garbage-collected; AudioProcessor is unbound")
        return cfg

    def optimize_audio_parameters(self, audio_query: AudioQuery) -> None:
        """Optimize audio parameters for Discord voice quality.

        Args:
            audio_query: Audio query dictionary to optimize

        """
        if not audio_query:
            return

        # Set optimal sample rate from config for Discord
        cfg = self.config
        audio_query["outputSamplingRate"] = cfg.audio_sample_rate

        # Adjust volume to prevent clipping
        if "volumeScale" in audio_query:
            volume = audio_query["volumeScale"]
            audio_query["volumeScale"] = min(max(volume, 0.0), 1.0) * 0.8

        # Ensure reasonable speed (not too fast or slow)
        if "speedScale" in audio_query:
            audio_query["speedScale"] = max(0.8, min(1.2, audio_query["speedScale"]))

        # DO NOT MODIFY pitchScale - AivisSpeech uses pitchScale=0.0 for natural voice
        # Any modification to pitchScale causes high-pitched voice distortion
        logger.debug("Preserving natural voice characteristics (pitchScale unmodified)")

    def create_wav_header(self, data_size: int, sample_rate: int, channels: int) -> bytes:
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

    def validate_audio_data(self, audio_data: bytes) -> bool:
        """Validate audio data integrity.

        Args:
            audio_data: Audio data to validate

        Returns:
            True if audio data is valid, False otherwise

        """
        if not audio_data:
            logger.warning("Audio data is empty")
            return False

        # Check minimum size (WAV header is 44 bytes)
        if len(audio_data) < 44:
            logger.warning(f"Audio data too small: {len(audio_data)} bytes")
            return False

        # Basic WAV header validation
        if not audio_data.startswith(b"RIFF") or b"WAVE" not in audio_data[:12]:
            logger.warning("Audio data does not appear to be in WAV format")
            return False

        return True

    def get_audio_format_info(self, sample_rate: int, channels: int) -> AudioFormatInfo:
        """Get audio format information for the given parameters.

        Args:
            sample_rate: Sample rate in Hz
            channels: Number of audio channels

        Returns:
            Dictionary with audio format information

        """
        return {
            "sample_rate": sample_rate,
            "channels": channels,
            "bits_per_sample": 16,
            "format": "PCM",
            "byte_rate": sample_rate * channels * 2,  # 16-bit = 2 bytes per sample
            "block_align": channels * 2,
        }

    def optimize_for_discord(self, audio_query: AudioQuery) -> AudioQuery:
        """Optimize audio query specifically for Discord voice channels.

        Args:
            audio_query: Original audio query

        Returns:
            Optimized audio query for Discord

        """
        if not audio_query:
            return {}

        # Create a copy to avoid modifying the original
        optimized = audio_query.copy()

        # Discord-specific optimizations
        sample_rate = self.config.audio_sample_rate
        optimized["outputSamplingRate"] = sample_rate

        # Ensure the audio is suitable for real-time voice communication
        if "speedScale" in optimized:
            # Slightly faster speed for more natural conversation flow
            optimized["speedScale"] = max(0.9, min(1.1, optimized["speedScale"]))

        if "volumeScale" in optimized:
            # Prevent clipping while maintaining good volume
            optimized["volumeScale"] = max(0.3, min(0.9, optimized["volumeScale"]))

        logger.debug(f"Optimized audio parameters for Discord: sample_rate={sample_rate}")
        return optimized
