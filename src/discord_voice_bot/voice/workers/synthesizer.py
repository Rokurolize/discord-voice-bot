"""Synthesizer worker for voice operations."""

import asyncio
import tempfile
from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from ..handler import VoiceHandler

from ...tts_engine import tts_engine
from ...user_settings import user_settings
from ..audio_utils import calculate_message_priority, get_audio_size, validate_wav_format


class SynthesizerWorker:
    """Worker for processing TTS synthesis requests."""

    def __init__(self, voice_handler: "VoiceHandler"):
        self.voice_handler = voice_handler
        self.max_buffer_size = 50 * 1024 * 1024  # 50MB limit
        self.buffer_size = 0

    async def run(self) -> None:
        """Run the synthesis worker loop."""
        while True:
            try:
                item = await self.voice_handler.synthesis_queue.get()

                # Check buffer size before processing
                if self.buffer_size >= self.max_buffer_size:
                    logger.warning("Audio buffer size limit reached, dropping synthesis request")
                    continue

                # Get user settings
                speaker_id = None
                engine_name = None
                if item.get("user_id"):
                    settings = user_settings.get_user_settings(str(item["user_id"]))
                    if settings:
                        speaker_id = settings.get("speaker_id")
                        engine_name = settings.get("engine")

                # Synthesize audio with format validation
                audio_data = await tts_engine.synthesize_audio(item["text"], speaker_id=speaker_id, engine_name=engine_name)

                if audio_data:
                    # Validate audio format
                    if not validate_wav_format(audio_data):
                        logger.error(f"Invalid audio format for: {item['text'][:50]}...")
                        continue

                    # Check audio size
                    audio_size = get_audio_size(audio_data)
                    if audio_size > 10 * 1024 * 1024:  # 10MB per audio file
                        logger.warning(f"Audio file too large ({audio_size} bytes), skipping")
                        continue

                    # Save to temporary file
                    audio_path = await self._create_temp_audio_file(audio_data)

                    # Track buffer size
                    self.buffer_size += audio_size

                    # Calculate priority and add to audio queue
                    priority = calculate_message_priority(item)
                    await self.voice_handler.audio_queue.put((audio_path, item["group_id"], priority, item["chunk_index"]))
                    logger.debug(f"Synthesized chunk {item['chunk_index'] + 1}/{item['total_chunks']} (size: {audio_size} bytes)")

                else:
                    logger.error(f"Failed to synthesize: {item['text'][:50]}...")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Synthesis error: {e}")
                self.voice_handler.stats["errors"] += 1

    async def _create_temp_audio_file(self, audio_data: bytes) -> str:
        """Create a temporary audio file with the given data."""
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".wav", delete=False) as f:
            f.write(audio_data)
            return f.name
