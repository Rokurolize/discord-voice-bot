"""Synthesizer worker for voice operations."""

import asyncio
import tempfile
from typing import Any, Protocol

from loguru import logger

from ...config import Config
from ...tts_engine import get_tts_engine
from ...user_settings import load_user_settings
from ..audio_utils import calculate_message_priority, cleanup_file, get_audio_size, validate_wav_format


class VoiceHandlerProtocol(Protocol):
    """Protocol defining the interface for voice handler."""

    synthesis_queue: Any
    audio_queue: Any
    stats: Any

    async def add_to_queue(self, message_data: dict[str, Any]) -> None: """
Enqueue a synthesis request for asynchronous processing.

message_data should be a dict describing the synthesis job (commonly includes keys like
`text`, `group_id`, `chunk_index`, and optionally `user_id` and other metadata). This
method places the job into the voice handler's synthesis queue so a SynthesizerWorker
can consume it and produce audio. The call is asynchronous and does not return a value.
"""
...


# Provide a shim that tests can patch
def get_user_settings():
    """
    Return application user settings by delegating to load_user_settings().
    
    This thin shim exists so tests can patch or replace the settings loader
    without importing or modifying the concrete loader directly.
    
    Returns:
        The result of load_user_settings() — the application's loaded user settings (type depends on loader).
    """
    return load_user_settings()


class SynthesizerWorker:
    """Worker for processing TTS synthesis requests."""

    def __init__(self, voice_handler: VoiceHandlerProtocol, config: Config):
        """
        Create a SynthesizerWorker and initialize runtime state.
        
        Initializes worker state used by the background synthesis loop:
        - stores the provided config and voice handler,
        - sets buffer accounting (max_buffer_size default 50 MB, buffer_size start 0),
        - enables the run loop (_running True) and idle logging counters,
        - leaves the TTS engine uninitialized (None) — it will be created asynchronously in run(),
        - loads per-user settings via the testable shim get_user_settings().
        
        Parameters:
            config: Configuration used by the worker (influences TTS engine selection and runtime behavior).
        """
        super().__init__()
        self.voice_handler = voice_handler
        self.config = config
        self.max_buffer_size = 50 * 1024 * 1024  # 50MB limit
        self.buffer_size = 0
        self._running = True  # Flag to control the worker loop
        self._idle_log_counter = 0
        self._last_idle_log = 0.0

        # Initialize TTS engine and user settings with config manager
        # Note: TTS engine will be initialized asynchronously in run() method
        self._tts_engine = None
        self._user_settings = get_user_settings()

    async def run(self) -> None:
        """
        Run the synthesizer main loop.
        
        Continuously consumes synthesis requests from the voice handler's synthesis_queue, uses the configured TTS engine to produce WAV audio, validates size and format, writes audio to a temporary file, updates an internal buffer size, and enqueues prepared audio items onto the voice handler's audio_queue for playback/processing. The loop enforces timeouts on queue operations and TTS synthesis, respects a maximum buffer size to avoid memory pressure, records errors to the shared stats, and stops the worker when cancelled or when a configurable threshold of consecutive synthesis errors is exceeded.
        """
        consecutive_errors = 0
        max_consecutive_errors = 5

        # Initialize TTS engine if not already initialized
        if self._tts_engine is None:
            try:
                self._tts_engine = await get_tts_engine(self.config)
            except Exception:
                logger.exception("Failed to initialize TTS engine")
                self._running = False
                return

        while self._running:
            try:
                # Add timeout to queue.get() to prevent indefinite blocking
                try:
                    item = await asyncio.wait_for(self.voice_handler.synthesis_queue.get(), timeout=1.0)
                    self._idle_log_counter = 0
                except TimeoutError:
                    self._idle_log_counter += 1
                    now = asyncio.get_running_loop().time()
                    if now - self._last_idle_log >= 60.0:
                        logger.debug("SynthesizerWorker is idle, waiting for synthesis tasks in the queue.")
                        self._last_idle_log = now
                    await asyncio.sleep(0.1)
                    continue

                # Check buffer size before processing
                if self.buffer_size >= self.max_buffer_size:
                    logger.warning("Audio buffer size limit reached, dropping synthesis request")
                    self.voice_handler.stats.increment_errors()
                    continue

                # Get user settings
                speaker_id = None
                engine_name = None
                if item.get("user_id"):
                    settings = self._user_settings.get_user_settings(str(item["user_id"]))
                    if settings:
                        speaker_id = settings.get("speaker_id")
                        engine_name = settings.get("engine")

                # Synthesize audio with format validation and timeout protection
                try:
                    audio_data = await asyncio.wait_for(
                        self._tts_engine.synthesize_audio(item["text"], speaker_id=speaker_id, engine_name=engine_name),
                        timeout=30.0,  # 30 second timeout for TTS synthesis
                    )
                except TimeoutError:
                    logger.error(f"TTS synthesis timeout for: {item['text'][:50]}...")
                    self.voice_handler.stats.increment_errors()
                    consecutive_errors += 1
                    continue

                if audio_data:
                    # Validate audio format
                    if not validate_wav_format(audio_data):
                        logger.error(f"Invalid audio format for: {item['text'][:50]}...")
                        self.voice_handler.stats.increment_errors()
                        consecutive_errors += 1
                        continue

                    # Check audio size
                    audio_size = get_audio_size(audio_data)
                    if audio_size > 10 * 1024 * 1024:  # 10MB per audio file
                        logger.warning(f"Audio file too large ({audio_size} bytes), skipping")
                        self.voice_handler.stats.increment_errors()
                        consecutive_errors += 1
                        continue

                    # Save to temporary file
                    audio_path = await self._create_temp_audio_file(audio_data)

                    # Track buffer size
                    self.buffer_size += audio_size

                    # Calculate priority and add to audio queue with timeout protection
                    priority = calculate_message_priority(item)
                    try:
                        await asyncio.wait_for(
                            self.voice_handler.audio_queue.put((audio_path, item["group_id"], priority, item["chunk_index"], audio_size)),
                            timeout=1.0,
                        )
                    except TimeoutError:
                        logger.warning(f"Audio queue full, dropping synthesized audio for: {item['text'][:50]}...")
                        cleanup_file(audio_path)
                        self.voice_handler.stats.increment_errors()
                        self.decrement_buffer_size(audio_size)
                        continue

                    logger.debug(f"Synthesized chunk {item['chunk_index'] + 1}/{item['total_chunks']} (size: {audio_size} bytes)")
                    consecutive_errors = 0  # Reset error count on success

                else:
                    logger.error(f"Failed to synthesize: {item['text'][:50]}...")
                    self.voice_handler.stats.increment_errors()
                    consecutive_errors += 1

                # Check for too many consecutive errors
                if consecutive_errors >= max_consecutive_errors:
                    logger.error(f"Too many consecutive errors ({consecutive_errors}), stopping synthesizer worker")
                    self._running = False
                    break

            except asyncio.CancelledError:
                logger.info("SynthesizerWorker cancelled")
                break
            except Exception:
                logger.exception("Synthesis error")
                self.voice_handler.stats.increment_errors()
                consecutive_errors += 1

                if consecutive_errors >= max_consecutive_errors:
                    logger.error(f"Too many consecutive errors ({consecutive_errors}), stopping synthesizer worker")
                    self._running = False
                    break

                # Brief pause before retrying
                await asyncio.sleep(0.1)

    def stop(self) -> None:
        """Stop the worker loop."""
        self._running = False

    def decrement_buffer_size(self, size: int) -> None:
        """Decrement the buffer size."""
        before = self.buffer_size
        # Reject negative decrements, then clamp at zero to prevent underflow
        self.buffer_size = max(before - max(size, 0), 0)
        # If we went from >0 to 0 due to an excessive decrement, log it
        if self.buffer_size == 0 and before != 0 and before - size < 0:
            logger.debug(
                "Synthesizer buffer underflow prevented; clamped to 0 (before={}, decrement={}).",
                before,
                size,
            )

    async def _create_temp_audio_file(self, audio_data: bytes) -> str:
        """Create a temporary audio file with the given data."""
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".wav", delete=False) as f:
            result = f.write(audio_data)
            _ = result  # Handle unused result
            return f.name
