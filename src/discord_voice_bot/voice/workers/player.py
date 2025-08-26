"""Player worker for voice operations."""

import asyncio
from typing import TYPE_CHECKING, Any, Protocol

import discord
from loguru import logger

from ..audio_utils import cleanup_file

if TYPE_CHECKING:
    from .synthesizer import SynthesizerWorker


class VoiceHandlerProtocol(Protocol):
    """Protocol defining the interface for voice handler."""

    audio_queue: Any
    voice_client: Any
    current_group_id: str | None
    is_playing: bool
    stats: Any


class PlayerWorker:
    """Worker for processing audio playback requests."""

    def __init__(self, voice_handler: VoiceHandlerProtocol, synthesizer_worker: "SynthesizerWorker"):
        super().__init__()
        self.voice_handler = voice_handler
        self._synthesizer_worker = synthesizer_worker
        self._running = True

    async def run(self) -> None:
        """Run the playback worker loop."""
        consecutive_errors = 0
        max_consecutive_errors = 5

        try:
            while self._running:
                try:
                    # Add timeout to queue.get() to prevent indefinite blocking
                    try:
                        audio_path, group_id, priority, chunk_index, audio_size = await asyncio.wait_for(self.voice_handler.audio_queue.get(), timeout=1.0)
                    except TimeoutError:
                        # No items in queue, continue loop
                        await asyncio.sleep(0.1)
                        continue

                    if not self.voice_handler.voice_client or not self.voice_handler.voice_client.is_connected():
                        cleanup_file(audio_path)
                        logger.debug(f"Skipping playback of {audio_path} (chunk: {chunk_index}) - not connected")
                        continue

                    # Wait if already playing with timeout protection
                    wait_time = 0
                    while self.voice_handler.voice_client.is_playing() and wait_time < 30:  # 3 second max wait
                        await asyncio.sleep(0.1)
                        wait_time += 1

                    if wait_time >= 30:
                        logger.warning(f"Wait timeout for playback of {audio_path}, stopping current playback")
                        self.voice_handler.voice_client.stop()
                        await asyncio.sleep(0.1)

                    # Play audio with enhanced error handling
                    self.voice_handler.current_group_id = group_id
                    self.voice_handler.is_playing = True

                    try:
                        audio_source = discord.FFmpegPCMAudio(audio_path)
                        self.voice_handler.voice_client.play(audio_source, after=self._playback_complete)

                        # Wait for playback to complete with timeout
                        waited = 0
                        while self.voice_handler.voice_client.is_playing() and waited < 300:  # 5 minute timeout
                            await asyncio.sleep(0.1)
                            waited += 1

                        if waited >= 300:
                            logger.warning(f"Audio playback timeout for {audio_path}")
                            self.voice_handler.voice_client.stop()

                        self._synthesizer_worker.buffer_size -= audio_size
                        self.voice_handler.stats.increment_messages_played()
                        logger.debug(f"Played audio: {audio_path} (priority: {priority})")
                        consecutive_errors = 0

                    except Exception as e:
                        logger.error(f"Playback error: {e}")
                        cleanup_file(audio_path)
                        self.voice_handler.stats.increment_errors()
                        consecutive_errors += 1

                        if consecutive_errors >= max_consecutive_errors:
                            logger.error(f"Too many consecutive errors ({consecutive_errors}), stopping worker")
                            self._running = False
                            break

                except asyncio.CancelledError:
                    logger.info("PlayerWorker cancelled")
                    break
                except Exception as e:
                    logger.error(f"Playback task error: {e}")
                    consecutive_errors += 1

                    if consecutive_errors >= max_consecutive_errors:
                        logger.error(f"Too many consecutive errors ({consecutive_errors}), stopping worker")
                        self._running = False
                        break

                    # Brief pause before retrying
                    await asyncio.sleep(0.1)

        except asyncio.CancelledError:
            logger.info("PlayerWorker cancelled")
            raise

    def stop(self) -> None:
        """Stop the worker loop."""
        self._running = False

    def _playback_complete(self, error: Exception | None) -> None:
        """Handle playback completion."""
        self.voice_handler.is_playing = False
        self.voice_handler.current_group_id = None

        if error:
            logger.error(f"Playback error: {error}")
            self.voice_handler.stats.increment_errors()
