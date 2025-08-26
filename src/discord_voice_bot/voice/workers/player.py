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
        # Bound lazily in run() to avoid RuntimeError if constructed off-loop
        self._loop = None  # type: ignore[assignment]
        self._playback_event = None  # type: ignore[assignment]

    async def run(self) -> None:
        """Run the playback worker loop."""
        consecutive_errors = 0
        max_consecutive_errors = 5

        try:
            # Lazily bind loop and event
            if self._loop is None:
                self._loop = asyncio.get_running_loop()
            if self._playback_event is None:
                self._playback_event = asyncio.Event()
            while self._running:
                try:
                    # Add timeout to queue.get() to prevent indefinite blocking
                    try:
                        item = await asyncio.wait_for(self.voice_handler.audio_queue.get(), timeout=1.0)
                    except asyncio.TimeoutError:
                        # No items in queue, continue loop
                        await asyncio.sleep(0.1)
                        continue

                    # Handle different queue item formats for backward compatibility
                    if isinstance(item, tuple) and len(item) == 5:
                        audio_path, group_id, priority, chunk_index, audio_size = item
                    elif isinstance(item, tuple) and len(item) == 4:
                        audio_path, group_id, priority, audio_size = item
                        chunk_index = 0
                        logger.warning(f"Processing legacy queue item (4 elements): {audio_path}")
                    elif isinstance(item, tuple) and len(item) == 3:
                        audio_path, group_id, priority = item
                        chunk_index, audio_size = 0, 0  # Default values for older format
                        logger.warning(f"Processing legacy queue item (3 elements): {audio_path}")
                    else:
                        logger.error(f"Invalid item in queue: {item}")
                        continue

                    if not self.voice_handler.voice_client or not self.voice_handler.voice_client.is_connected():
                        cleanup_file(audio_path)
                        logger.debug(f"Skipping playback of {audio_path} (chunk: {chunk_index}) - not connected")
                        continue

                    # Wait if already playing with timeout protection
                    start = asyncio.get_running_loop().time()
                    while self.voice_handler.voice_client.is_playing() and (asyncio.get_running_loop().time() - start) < 3.0:
                        await asyncio.sleep(0.1)

                    if (asyncio.get_running_loop().time() - start) >= 3.0:
                        logger.warning(f"Wait timeout for playback of {audio_path}, stopping current playback")
                        self.voice_handler.voice_client.stop()
                        await asyncio.sleep(0.1)

                    # Play audio with enhanced error handling
                    self.voice_handler.current_group_id = group_id
                    self.voice_handler.is_playing = True
                    assert self._playback_event is not None
                    self._playback_event.clear()

                    try:
                        audio_source = discord.FFmpegPCMAudio(audio_path)
                        self.voice_handler.voice_client.play(audio_source, after=self._playback_complete)

                        # Wait for playback to complete with timeout
                        # 5 minute timeout (long-running TTS/playback safety)
                        await asyncio.wait_for(self._playback_event.wait(), timeout=300)

                        if audio_size > 0:
                            new_size = max(0, getattr(self._synthesizer_worker, "buffer_size", 0) - audio_size)
                            self._synthesizer_worker.buffer_size = new_size
                        self.voice_handler.stats.increment_messages_played()
                        logger.debug(f"Played audio: {audio_path} (priority: {priority})")
                        consecutive_errors = 0

                    except asyncio.TimeoutError:
                        logger.warning(f"Audio playback timeout for {audio_path}")
                        self.voice_handler.voice_client.stop()
                        try:
                            self.voice_handler.stats.increment_errors()
                        except Exception:
                            logger.debug("Failed to increment error stats on timeout")
                    except Exception as e:
                        logger.error(f"Playback error: {e}")
                        self.voice_handler.stats.increment_errors()
                        consecutive_errors += 1

                        if consecutive_errors >= max_consecutive_errors:
                            logger.error(f"Too many consecutive errors ({consecutive_errors}), stopping worker")
                            self._running = False
                            break
                    finally:
                        # Always cleanup the file after playback is done/aborted
                        try:
                            cleanup_file(audio_path)
                        except Exception as ce:
                            logger.debug(f"Cleanup failed for {audio_path}: {ce}")
                        self.voice_handler.is_playing = False
                        self.voice_handler.current_group_id = None

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
        loop = self._loop
        event = self._playback_event
        if error:
            logger.error(f"Playback error in callback: {error}")
            if loop:
                loop.call_soon_threadsafe(lambda: self.voice_handler.stats.increment_errors())
            else:
                # Fallback: best-effort in callback thread
                try:
                    self.voice_handler.stats.increment_errors()
                except Exception:
                    pass
        # Signal completion back to the main loop if available
        if loop and event:
            loop.call_soon_threadsafe(event.set)
        else:
            logger.debug("Playback completion signaled without initialized loop/event")
