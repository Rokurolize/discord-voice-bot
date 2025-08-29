"""Temporary file management for TTS engine."""

import tempfile
from pathlib import Path
from typing import Any
from weakref import ref

from loguru import logger

from .audio_debugger import audio_debugger
from .audio_processor import AudioProcessor
from .config import Config


class TempFileManager:
    """Manages temporary files for TTS audio processing."""

    def __init__(self, config: Config, audio_processor: AudioProcessor) -> None:
        """Initialize temp file manager with configuration and audio processor."""
        super().__init__()
        self._config_ref = ref(config)
        self._audio_processor = audio_processor

    @property
    def config(self) -> Config:
        cfg = self._config_ref()
        if cfg is None:
            raise RuntimeError("Config has been garbage-collected; TempFileManager is unbound")
        return cfg

    async def create_audio_source(self, text: str, audio_data: bytes, speaker_id: int | None = None, engine_name: str | None = None) -> Any:
        """Create Discord audio source from audio data.

        Args:
            text: Original text for debugging
            audio_data: Audio data to create source from
            speaker_id: Speaker ID used for synthesis
            engine_name: Engine name used for synthesis

        Returns:
            Discord audio source, or None if creation failed

        """
        # Import discord here to avoid circular imports
        try:
            import discord
        except ImportError:
            logger.error("discord.py not installed")
            return None

        temp_path = ""
        try:
            # Create temporary file for audio data
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                _ = f.write(audio_data)  # Write audio data to temp file
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
                logger.debug(f"🔍 Saved pre-Discord audio for debugging: {saved_pre_path}")
            except Exception as e:
                logger.warning(f"Failed to save pre-Discord debug audio: {e}")

            # Create Discord audio source with corrected FFmpeg options
            sample_rate = self.config.audio_sample_rate
            channels = self.config.audio_channels
            ffmpeg_options = f"-ar {sample_rate} -ac {channels} -f s16le"
            before_options = "-nostdin -hide_banner -loglevel warning"

            logger.debug(f"FFmpeg options: before='{before_options}' options='{ffmpeg_options}'")

            try:
                audio_source = discord.FFmpegPCMAudio(temp_path, before_options=before_options, options=ffmpeg_options)

                # Store temp path for cleanup
                audio_source._temp_path = temp_path  # type: ignore[attr-defined]

                # DEBUG: Test the created audio source and save converted audio
                await self._debug_audio_conversion(temp_path, text, ffmpeg_options)

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
                if temp_path:
                    Path(temp_path).unlink(missing_ok=True)
            except Exception:
                pass
            return None

    async def _debug_audio_conversion(self, temp_path: str, text: str, ffmpeg_options: str) -> None:
        """Debug audio conversion process for troubleshooting.

        Args:
            temp_path: Path to temporary audio file
            text: Original text
            ffmpeg_options: FFmpeg options used

        """
        try:
            # Try to read the converted audio using FFmpeg
            cmd = [
                "ffmpeg",
                "-i",
                temp_path,
                "-ar",
                str(self.config.audio_sample_rate),
                "-ac",
                str(self.config.audio_channels),
                "-f",
                "s16le",
                "-",
            ]
            import asyncio

            try:
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
            except FileNotFoundError as e:
                logger.warning("ffmpeg not found; skipping conversion test: %s", e)
                return
            try:
                async with asyncio.timeout(10):
                    stdout, stderr = await proc.communicate()
            except TimeoutError:
                proc.kill()
                stdout, stderr = await proc.communicate()
            returncode: int = 0 if proc.returncode is None else int(proc.returncode)
            out_bytes: bytes = stdout or b""
            err_bytes: bytes = stderr or b""

            if returncode == 0 and out_bytes:
                metadata_discord = {
                    "ffmpeg_options": ffmpeg_options,
                    "converted_size": len(out_bytes),
                    "conversion_success": True,
                }
                # Save as raw PCM data (add WAV header for playability)
                sample_rate = self.config.audio_sample_rate
                channels = self.config.audio_channels
                wav_header = self._audio_processor.create_wav_header(
                    len(out_bytes),
                    sample_rate,
                    channels,
                )
                wav_data = wav_header + out_bytes

                saved_discord_path = audio_debugger.save_audio_stage(wav_data, "discord_converted", text, metadata_discord)
                logger.debug(f"🔍 Saved Discord-converted audio: {saved_discord_path}")
            else:
                stderr_str = err_bytes.decode("utf-8", errors="ignore")
                logger.warning(f"FFmpeg conversion test failed: {stderr_str}")

        except Exception as e:
            logger.warning(f"Failed to save Discord-converted debug audio: {e}")

    def cleanup_audio_source(self, audio_source: Any) -> None:
        """Clean up temporary files from audio source.

        Args:
            audio_source: Discord audio source to clean up

        """
        try:
            if hasattr(audio_source, "_temp_path"):
                temp_path = getattr(audio_source, "_temp_path")
                Path(temp_path).unlink(missing_ok=True)
                logger.debug("Cleaned up temporary audio file")
        except Exception as e:
            logger.warning(f"Failed to cleanup audio source: {e!s}")

    def create_temp_audio_file(self, audio_data: bytes, suffix: str = ".wav") -> str:
        """Create a temporary audio file with the given data.

        Args:
            audio_data: Audio data to write
            suffix: File suffix (default: .wav)

        Returns:
            Path to the created temporary file

        """
        try:
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
                _ = f.write(audio_data)
                temp_path = f.name
            logger.debug(f"Created temporary audio file: {temp_path}")
            return temp_path
        except Exception as e:
            logger.error(f"Failed to create temporary audio file: {e}")
            raise

    def cleanup_temp_file(self, file_path: str) -> None:
        """Clean up a temporary file.

        Args:
            file_path: Path to the temporary file to clean up

        """
        try:
            Path(file_path).unlink(missing_ok=True)
            logger.debug(f"Cleaned up temporary file: {file_path}")
        except Exception as e:
            logger.warning(f"Failed to cleanup temporary file {file_path}: {e}")

    def get_temp_directory_info(self) -> dict[str, int | str]:
        """Get information about the temporary directory.

        Returns:
            Dictionary with temporary directory information

        """
        temp_dir = Path(tempfile.gettempdir())
        return {
            "temp_directory": str(temp_dir),
            "total_space": temp_dir.stat().st_size if temp_dir.exists() else 0,
            "available_space": 0,  # Would need platform-specific code to get this
            "temp_files_count": len(list(temp_dir.glob("*.wav"))),
        }
