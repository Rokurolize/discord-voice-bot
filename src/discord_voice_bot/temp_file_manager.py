"""Temporary file management for TTS engine."""

import shutil
import tempfile
from pathlib import Path
from typing import Any
from weakref import finalize, ref

from loguru import logger

from .audio_debugger import audio_debugger
from .audio_processor import AudioProcessor
from .config import Config


class TempFileManager:
    """Manages temporary files for TTS audio processing."""

    def __init__(self, config: Config, audio_processor: AudioProcessor) -> None:
        """
        Create a TempFileManager that holds a weak reference to the provided Config and a strong reference to the AudioProcessor.

        The Config is stored as a weak reference to avoid reference cycles; attempting to access the config later may raise a RuntimeError if the original Config has been garbage-collected.
        """
        super().__init__()
        self._config_ref = ref(config)
        self._audio_processor = audio_processor

    @property
    def config(self) -> Config:
        """
        Return the live Config instance referenced by this TempFileManager.

        If the underlying weak reference has been garbage-collected, raises RuntimeError
        including the TempFileManager id and the audio processor type and id.

        Returns:
            Config: The referenced configuration object.

        """
        cfg = self._config_ref()
        if cfg is None:
            raise RuntimeError(f"Config weakref is dead; TempFileManager id={id(self)}; audio_processor={type(self._audio_processor).__name__}(id={id(self._audio_processor)})")
        return cfg

    async def create_audio_source(self, text: str, audio_data: bytes, speaker_id: int | None = None, engine_name: str | None = None) -> Any:
        """
        Create a Discord audio source from raw WAV audio bytes.

        This writes `audio_data` to a temporary WAV file, constructs an FFmpeg-based
        discord.FFmpegPCMAudio source that reads that file, and returns the created
        audio source. The temporary file path is attached to the returned audio source
        as `_temp_path` and a best-effort finalizer is registered to remove the file
        when the audio source is garbage-collected; callers may also call
        cleanup_audio_source to remove the file explicitly.

        Behavior and notable cases:
        - If the Discord library cannot be imported, the function logs an error and
          returns None.
        - On any failure creating the temp file or the FFmpeg audio source, the
          temporary file is cleaned up (if created) and the function returns None.
        - When `self.config.debug` is true, the function attempts to save a pre-Discord
          debug copy of the raw audio and (after creating the source) runs an
          FFmpeg-based conversion debug step that can save the converted audio stage.
        - FFmpeg options (sample rate and channels) are taken from the configuration.

        Args:
            text: Original text that produced the audio (used only for debugging metadata).
            audio_data: WAV-formatted audio bytes to write to the temporary file.
            speaker_id: Optional speaker identifier used for debug metadata.
            engine_name: Optional engine name used for debug metadata.

        Returns:
            discord.FFmpegPCMAudio | None: Audio source on success, or None on failure.

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

            # DEBUG: Save pre-Discord conversion audio (only when debug enabled)
            if self.config.debug:
                try:
                    metadata = {
                        "temp_path": temp_path,
                        "size_bytes": len(audio_data),
                        "stage": "pre_discord",
                        "speaker_id": speaker_id,
                        "engine_name": engine_name,
                    }
                    saved_pre_path = audio_debugger.save_audio_stage(audio_data, "pre_discord", text, metadata)
                    logger.debug(f"🔍 Saved pre-Discord audio for debugging: {saved_pre_path}")
                except Exception as e:
                    logger.warning(f"Failed to save pre-Discord debug audio: {e}")

            # Create Discord audio source with corrected FFmpeg options
            sample_rate = self.config.audio_sample_rate
            channels = self.config.audio_channels
            ffmpeg_options = f"-vn -sn -acodec pcm_s16le -ar {sample_rate} -ac {channels} -f s16le"
            before_options = "-nostdin -hide_banner -loglevel warning"

            logger.debug(f"FFmpeg options: before='{before_options}' options='{ffmpeg_options}'")

            try:
                audio_source = discord.FFmpegPCMAudio(temp_path, before_options=before_options, options=ffmpeg_options)

                # Store temp path for cleanup
                audio_source._temp_path = temp_path  # type: ignore[attr-defined]
                # Optional safety net: cleanup when audio_source is GC'ed
                try:
                    # Retain Finalize object to prevent GC from discarding it
                    audio_source._finalizer = finalize(  # type: ignore[attr-defined]
                        audio_source, Path(temp_path).unlink, missing_ok=True
                    )
                except Exception:
                    # Best-effort; explicit cleanup still happens in cleanup_audio_source
                    pass

                # DEBUG: Test the created audio source and save converted audio (only when debug enabled)
                if self.config.debug:
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
        """
        Run an FFmpeg-based conversion check on a temporary WAV file and, when successful, save a debug copy of the converted PCM (with a WAV header).

        This asynchronous helper:
        - Executes FFmpeg to convert the file at `temp_path` to raw PCM matching the configured sample rate and channel count.
        - Skips the test if FFmpeg is not installed, and aborts the test on timeout.
        - On successful conversion (non-empty stdout and exit code 0), prepends a WAV header and saves the result via the audio_debugger with metadata that includes `ffmpeg_options`, converted size, sample rate, and channels.
        - Logs warnings when conversion fails or when exceptions occur; does not raise.

        Args:
            temp_path: Path to the temporary audio file to test (expected readable WAV/PCM).
            text: Original input text associated with the audio (used for debug save metadata).
            ffmpeg_options: The FFmpeg option string used when creating the Discord source (stored in debug metadata).

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
                logger.warning(f"ffmpeg not found; skipping conversion test: {e}")
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
                    "returncode": returncode,
                    "sample_rate": self.config.audio_sample_rate,
                    "channels": self.config.audio_channels,
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
        """
        Return summary information about the system temporary directory.

        Returns a dictionary with the following keys:
        - temp_directory (str): Absolute path to the system temporary directory.
        - total_space (int): Total size of the filesystem containing the temp directory, in bytes.
        - available_space (int): Free space available to the current user on that filesystem, in bytes.
        - used_space (int): Estimated used space on that filesystem (total_space - available_space), in bytes.
        - temp_files_count (int): Number of files in the temp directory matching the pattern `*.wav`.
        """
        temp_dir = Path(tempfile.gettempdir())
        total, _used, free = shutil.disk_usage(temp_dir)
        return {
            "temp_directory": str(temp_dir),
            "total_space": int(total),
            "available_space": int(free),
            "used_space": int(total - free),
            "temp_files_count": len(list(temp_dir.glob("*.wav"))),
        }
