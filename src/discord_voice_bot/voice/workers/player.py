"""Player worker for voice operations."""

import asyncio
from typing import TYPE_CHECKING

import discord
from loguru import logger

if TYPE_CHECKING:
    from ..handler import VoiceHandler

from ..audio_utils import cleanup_file


class PlayerWorker:
    """Worker for processing audio playback requests."""

    def __init__(self, voice_handler: "VoiceHandler"):
        self.voice_handler = voice_handler

    async def run(self) -> None:
        """Run the playback worker loop."""
        while True:
            try:
                # Get highest priority item from queue
                audio_path, group_id, priority, chunk_index = await self.voice_handler.audio_queue.get()

                if not self.voice_handler.voice_client or not self.voice_handler.voice_client.is_connected():
                    cleanup_file(audio_path)
                    logger.debug(f"Skipping playback of {audio_path} (chunk: {chunk_index}) - not connected")
                    continue

                # Wait if already playing
                while self.voice_handler.voice_client.is_playing():
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

                    self.voice_handler.stats["messages_played"] += 1
                    logger.debug(f"Played audio: {audio_path} (priority: {priority})")

                except Exception as e:
                    logger.error(f"Playback error: {e}")
                    cleanup_file(audio_path)
                    self.voice_handler.stats["errors"] += 1

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Playback task error: {e}")

    def _playback_complete(self, error: Exception | None) -> None:
        """Handle playback completion."""
        self.voice_handler.is_playing = False
        self.voice_handler.current_group_id = None

        if error:
            logger.error(f"Playback error: {error}")
            self.voice_handler.stats["errors"] += 1
