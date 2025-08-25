"""Synthesizer worker for voice operations."""

import asyncio
import tempfile
from typing import Any, Protocol

from loguru import logger

from ...protocols import ConfigManager
from ...tts_engine import get_tts_engine
from ...user_settings import get_user_settings
from ..audio_utils import calculate_message_priority, cleanup_file, get_audio_size, validate_wav_format


class VoiceHandlerProtocol(Protocol):
    """Protocol defining the interface for voice handler."""

    synthesis_queue: Any
    audio_queue: Any
    stats: Any

    async def add_to_queue(self, message_data: dict[str, Any]) -> None: ...


class SynthesizerWorker:
    """Worker for processing TTS synthesis requests."""

    def __init__(self, voice_handler: VoiceHandlerProtocol, config_manager: ConfigManager):
        super().__init__()
        self.voice_handler = voice_handler
        self._config_manager = config_manager
        self.max_buffer_size = 50 * 1024 * 1024  # 50MB limit
        self.buffer_size = 0
        self._running = True  # Flag to control the worker loop

        # Initialize TTS engine and user settings with config manager
        # Note: TTS engine will be initialized asynchronously in run() method
        self._tts_engine = None
        self._user_settings = get_user_settings()

    async def run(self) -> None:
        """Run the synthesis worker loop."""
        consecutive_errors = 0
        max_consecutive_errors = 5

        # Initialize TTS engine if not already initialized
        if self._tts_engine is None:
            try:
                self._tts_engine = await get_tts_engine(self._config_manager)
            except Exception as e:
                logger.error(f"Failed to initialize TTS engine: {e}")
                self._running = False
                return

        while self._running:
            try:
                # Add timeout to queue.get() to prevent indefinite blocking
                try:
                    item = await asyncio.wait_for(self.voice_handler.synthesis_queue.get(), timeout=1.0)
                except TimeoutError:
                    # No items in queue, continue loop
                    await asyncio.sleep(0.1)
                    continue

                # Check buffer size before processing
                if self.buffer_size >= self.max_buffer_size:
                    logger.warning("Audio buffer size limit reached, dropping synthesis request")
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
                        consecutive_errors += 1
                        continue

                    # Check audio size
                    audio_size = get_audio_size(audio_data)
                    if audio_size > 10 * 1024 * 1024:  # 10MB per audio file
                        logger.warning(f"Audio file too large ({audio_size} bytes), skipping")
                        consecutive_errors += 1
                        continue

                    # Save to temporary file
                    audio_path = await self._create_temp_audio_file(audio_data)

                    # Track buffer size
                    self.buffer_size += audio_size

                    # Calculate priority and add to audio queue with timeout protection
                    priority = calculate_message_priority(item)
                    try:
                        await asyncio.wait_for(self.voice_handler.audio_queue.put((audio_path, item["group_id"], priority, item["chunk_index"])), timeout=1.0)
                    except TimeoutError:
                        logger.warning(f"Audio queue full, dropping synthesized audio for: {item['text'][:50]}...")
                        cleanup_file(audio_path)
                        continue

                    logger.debug(f"Synthesized chunk {item['chunk_index'] + 1}/{item['total_chunks']} (size: {audio_size} bytes)")
                    consecutive_errors = 0  # Reset error count on success

                else:
                    logger.error(f"Failed to synthesize: {item['text'][:50]}...")
                    consecutive_errors += 1

                # Check for too many consecutive errors
                if consecutive_errors >= max_consecutive_errors:
                    logger.error(f"Too many consecutive errors ({consecutive_errors}), stopping synthesizer worker")
                    self._running = False
                    break

            except asyncio.CancelledError:
                logger.info("SynthesizerWorker cancelled")
                break
            except Exception as e:
                logger.error(f"Synthesis error: {e}")
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

    async def _create_temp_audio_file(self, audio_data: bytes) -> str:
        """Create a temporary audio file with the given data."""
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".wav", delete=False) as f:
            result = f.write(audio_data)
            _ = result  # Handle unused result
            return f.name
