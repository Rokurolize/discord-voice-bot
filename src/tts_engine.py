"""TTS Engine integration for Discord Voice TTS Bot."""

import json
import tempfile
import urllib.parse
from pathlib import Path
from typing import Any

import aiohttp
from loguru import logger

from .audio_debugger import audio_debugger
from .config import config


class TTSEngineError(Exception):
    """Exception raised when TTS engine encounters an error."""


class TTSEngine:
    """TTS Engine for synthesizing speech using VOICEVOX or AivisSpeech."""

    def __init__(self) -> None:
        """Initialize TTS engine with configuration."""
        self._session: aiohttp.ClientSession | None = None
    
    @property
    def api_url(self) -> str:
        """Get current API URL from config."""
        return config.api_url
    
    @property
    def speaker_id(self) -> int:
        """Get current speaker ID from config."""
        return config.speaker_id
    
    @property
    def engine_name(self) -> str:
        """Get current engine name from config."""
        return config.tts_engine.upper()

    async def __aenter__(self) -> "TTSEngine":
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()

    async def start(self) -> None:
        """Start the TTS engine session."""
        if not self._session:
            timeout = aiohttp.ClientTimeout(total=10, connect=2)
            self._session = aiohttp.ClientSession(timeout=timeout)

    async def close(self) -> None:
        """Close the TTS engine session."""
        if self._session:
            await self._session.close()
            self._session = None

    async def check_api_availability(self) -> tuple[bool, str]:
        """Check TTS API availability with detailed error information.

        Returns:
            (is_available, error_detail): Tuple of availability status and error description

        """
        if not self._session:
            await self.start()

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

        except TimeoutError:
            error_msg = "connection timeout - server may be starting up"
            logger.error(f"{self.engine_name} TTS API: {error_msg}")
            return False, error_msg

        except Exception as e:
            error_msg = f"unexpected error: {type(e).__name__}"
            logger.error(f"{self.engine_name} TTS API: {error_msg} - {e!s}")
            return False, error_msg

    async def synthesize_audio(
        self, 
        text: str, 
        speaker_id: int | None = None, 
        engine_name: str | None = None
    ) -> bytes | None:
        """Synthesize audio from text using the specified TTS engine.

        Args:
            text: Text to synthesize
            speaker_id: Optional speaker ID override
            engine_name: Optional engine name ('voicevox' or 'aivis')

        Returns:
            Audio data as bytes, or None if synthesis failed

        """
        if not self._session:
            await self.start()

        # Determine engine and speaker
        target_engine = engine_name or config.tts_engine
        engine_config = config.engines.get(target_engine, config.engines["voicevox"])
        
        # Use provided speaker ID or engine default
        current_speaker_id = speaker_id or engine_config["default_speaker"]
        target_api_url = engine_config["url"]
        
        logger.debug(f"Using {target_engine} engine (URL: {target_api_url}) with speaker {current_speaker_id}")

        # No truncation here - handled by chunking in voice_handler

        try:
            # Generate audio query using target engine
            audio_query = await self._generate_audio_query(text, current_speaker_id, target_api_url)
            if not audio_query:
                return None

            # Optimize audio parameters for Discord
            self._optimize_audio_parameters(audio_query)

            # Synthesize audio
            audio_data = await self._synthesize_from_query(audio_query, current_speaker_id, target_api_url)
            if not audio_data:
                return None

            # DEBUG: Save raw AivisSpeech output for analysis
            try:
                metadata = {
                    "speaker_id": current_speaker_id,
                    "engine": target_engine,
                    "api_url": target_api_url,
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

    async def _generate_audio_query(self, text: str, speaker_id: int, api_url: str) -> dict[str, Any] | None:
        """Generate audio query from text."""
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

    def _optimize_audio_parameters(self, audio_query: dict[str, Any]) -> None:
        """Optimize audio parameters for Discord voice quality."""
        if not audio_query:
            return

        # Set optimal sample rate for Discord (48kHz)
        audio_query["outputSamplingRate"] = config.audio_sample_rate

        # Adjust volume to prevent clipping
        if "volumeScale" in audio_query:
            audio_query["volumeScale"] = min(1.0, audio_query["volumeScale"] * 0.8)

        # Ensure reasonable speed (not too fast or slow)
        if "speedScale" in audio_query:
            audio_query["speedScale"] = max(0.8, min(1.2, audio_query["speedScale"]))

        # DO NOT MODIFY pitchScale - AivisSpeech uses pitchScale=0.0 for natural voice
        # Any modification to pitchScale causes high-pitched voice distortion
        logger.debug("Preserving natural voice characteristics (pitchScale unmodified)")

    async def _synthesize_from_query(self, audio_query: dict[str, Any], speaker_id: int, api_url: str) -> bytes | None:
        """Synthesize audio from audio query."""
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

    async def create_audio_source(
        self, 
        text: str, 
        speaker_id: int | None = None, 
        engine_name: str | None = None
    ) -> Any:
        """Create Discord audio source from text.

        Args:
            text: Text to synthesize
            speaker_id: Optional speaker ID override
            engine_name: Optional engine name ('voicevox' or 'aivis')

        Returns:
            Discord audio source, or None if creation failed

        """
        # Import discord here to avoid circular imports
        try:
            import discord
        except ImportError:
            logger.error("discord.py not installed")
            return None

        # Synthesize audio
        audio_data = await self.synthesize_audio(text, speaker_id, engine_name)
        if not audio_data:
            return None

        try:
            # Create temporary file for audio data
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(audio_data)
                temp_path = f.name

            logger.debug(f"Created temp WAV file: {temp_path} ({len(audio_data)} bytes)")

            # DEBUG: Save pre-Discord conversion audio
            try:
                metadata = {
                    "temp_path": temp_path,
                    "size_bytes": len(audio_data),
                    "stage": "pre_discord_conversion",
                }
                saved_pre_path = audio_debugger.save_audio_stage(audio_data, "pre_discord", text, metadata)
                logger.debug(f"🔍 Saved pre-Discord audio: {saved_pre_path}")
            except Exception as e:
                logger.warning(f"Failed to save pre-Discord debug audio: {e}")

            # Create Discord audio source with corrected FFmpeg options
            ffmpeg_options = f"-ar {config.audio_sample_rate} -ac {config.audio_channels} -f s16le"

            logger.debug(f"FFmpeg options: {ffmpeg_options}")

            try:
                audio_source = discord.FFmpegPCMAudio(temp_path, options=ffmpeg_options)

                # Store temp path for cleanup
                audio_source._temp_path = temp_path  # type: ignore[attr-defined]

                # DEBUG: Test the created audio source and save converted audio
                try:
                    # Try to read the converted audio using FFmpeg
                    import subprocess

                    cmd = [
                        "ffmpeg",
                        "-i",
                        temp_path,
                        "-ar",
                        str(config.audio_sample_rate),
                        "-ac",
                        str(config.audio_channels),
                        "-f",
                        "s16le",
                        "-",
                    ]
                    result = subprocess.run(cmd, check=False, capture_output=True, timeout=10)

                    if result.returncode == 0 and result.stdout:
                        metadata_discord = {
                            "ffmpeg_options": ffmpeg_options,
                            "converted_size": len(result.stdout),
                            "conversion_success": True,
                        }
                        # Save as raw PCM data (add WAV header for playability)
                        wav_header = self._create_wav_header(
                            len(result.stdout),
                            config.audio_sample_rate,
                            config.audio_channels,
                        )
                        wav_data = wav_header + result.stdout

                        saved_discord_path = audio_debugger.save_audio_stage(wav_data, "discord_converted", text, metadata_discord)
                        logger.debug(f"🔍 Saved Discord-converted audio: {saved_discord_path}")
                    else:
                        stderr_str = result.stderr.decode("utf-8") if isinstance(result.stderr, bytes) else result.stderr
                        logger.warning(f"FFmpeg conversion test failed: {stderr_str}")

                except Exception as e:
                    logger.warning(f"Failed to save Discord-converted debug audio: {e}")

                logger.info(f"✅ Successfully created Discord audio source for: '{text[:50]}...'")
                return audio_source

            except Exception as ffmpeg_error:
                logger.error(f"❌ FFmpeg audio source creation failed: {type(ffmpeg_error).__name__} - {ffmpeg_error!s}")
                # Cleanup temp file
                try:
                    Path(temp_path).unlink(missing_ok=True)
                except Exception:
                    pass
                return None

        except Exception as e:
            logger.error(f"❌ Failed to create temp file or audio source: {type(e).__name__} - {e!s}")
            # Cleanup temp file if it was created
            try:
                if "temp_path" in locals():
                    Path(temp_path).unlink(missing_ok=True)
            except Exception:
                pass
            return None

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
        """Clean up temporary files from audio source."""
        try:
            if hasattr(audio_source, "_temp_path"):
                temp_path = getattr(audio_source, "_temp_path")
                Path(temp_path).unlink(missing_ok=True)
                logger.debug("Cleaned up temporary audio file")
        except Exception as e:
            logger.warning(f"Failed to cleanup audio source: {e!s}")

    async def get_available_speakers(self) -> dict[str, int]:
        """Get available speakers for current engine.

        Returns:
            Dictionary mapping speaker names to IDs

        """
        return config.engine_config["speakers"].copy()

    async def health_check(self) -> bool:
        """Perform health check on TTS engine."""
        try:
            is_available, error_detail = await self.check_api_availability()
            if not is_available:
                logger.warning(f"TTS health check failed: {error_detail}")
                return False

            # Test synthesis with a simple phrase
            test_audio = await self.synthesize_audio("テスト")
            if not test_audio:
                logger.warning("TTS health check failed: unable to synthesize test audio")
                return False

            logger.info("TTS health check passed")
            return True

        except Exception as e:
            logger.error(f"TTS health check failed: {e!s}")
            return False


# Global TTS engine instance
tts_engine = TTSEngine()
