"""Player worker for voice operations."""

import asyncio
from typing import TYPE_CHECKING, Any, Protocol

import discord
from loguru import logger

from ..audio_utils import cleanup_file


class VoiceHandlerProtocol(Protocol):
    """Protocol defining the interface for voice handler."""

    audio_queue: Any
    voice_client: Any
    current_group_id: str | None
    is_playing: bool
    stats: Any
    if TYPE_CHECKING:
        from .synthesizer import SynthesizerWorker
    synthesizer: "SynthesizerWorker | None"


class PlayerWorker:
    """Worker for processing audio playback requests."""

    def __init__(self, voice_handler: VoiceHandlerProtocol):
        super().__init__()
        self.voice_handler = voice_handler
        self._running = True  # Flag to control the worker loop
        self._idle_log_counter = 0
        self._last_idle_log = 0.0

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
                        self._idle_log_counter = 0
                    except TimeoutError:
                        self._idle_log_counter += 1
                        now = asyncio.get_running_loop().time()
                        if now - getattr(self, "_last_idle_log", 0.0) >= 60.0:
                            logger.debug("PlayerWorker is idle, waiting for audio chunks in the queue.")
                            self._last_idle_log = now
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
                        loop = asyncio.get_running_loop()
                        audio_source = discord.FFmpegPCMAudio(audio_path)

                        def after_playback(
                            error: Exception | None,
                            l: asyncio.AbstractEventLoop = loop,
                            p: str = audio_path,
                            s: int = audio_size,
                        ) -> None:
                            _ = l.call_soon_threadsafe(self._playback_complete, error, p, s)

                        # Schedule completion handling back onto the event loop thread
                        self.voice_handler.voice_client.play(audio_source, after=after_playback)

                        # Wait for playback to complete with timeout
                        waited = 0
                        max_wait_iters = 3000  # 5 minutes (0.1s * 3000 = 300s)
                        while self.voice_handler.voice_client.is_playing() and waited < max_wait_iters:
                            await asyncio.sleep(0.1)
                            waited += 1
                        if waited >= max_wait_iters and self.voice_handler.voice_client.is_playing():
                            logger.warning(f"Audio playback timeout for {audio_path}")
                            self.voice_handler.voice_client.stop()

                        logger.debug(f"Playback finished or stopped for: {audio_path} (priority: {priority})")
                        consecutive_errors = 0  # Reset error count on success

                    except Exception:
                        logger.exception("Playback error")
                        cleanup_file(audio_path)
                        self.voice_handler.stats.increment_errors()
                        consecutive_errors += 1
                        # Reset state since completion callback won't run
                        self.voice_handler.is_playing = False
                        self.voice_handler.current_group_id = None
                        # Account for buffered audio which would normally be decremented in completion
                        if audio_size and self.voice_handler.synthesizer:
                            self.voice_handler.synthesizer.decrement_buffer_size(audio_size)

                        if consecutive_errors >= max_consecutive_errors:
                            logger.error(f"Too many consecutive errors ({consecutive_errors}), stopping worker")
                            self._running = False
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

    def _playback_complete(self, error: Exception | None, audio_path: str | None = None, audio_size: int | None = None) -> None:
        """Handle playback completion."""
        self.voice_handler.is_playing = False
        self.voice_handler.current_group_id = None

        if error:
            logger.error(f"Playback error: {error}")
            self.voice_handler.stats.increment_errors()
        else:
            # Count only successful completions
            self.voice_handler.stats.increment_messages_played()

        # Clean up temp audio file after playback completes
        if audio_path:
            cleanup_file(audio_path)

        # Decrement buffer size
        if audio_size and hasattr(self.voice_handler, "synthesizer") and self.voice_handler.synthesizer:
            self.voice_handler.synthesizer.decrement_buffer_size(audio_size)
