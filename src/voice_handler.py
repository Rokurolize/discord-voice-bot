"""Voice connection handler for Discord Voice TTS Bot."""

import asyncio
import os
from functools import partial
from typing import Any

import discord
from loguru import logger

from .tts_engine import tts_engine
from .user_settings import user_settings


class VoiceHandler:
    """Manages Discord voice connections and audio playback."""

    def __init__(self, bot_client: discord.Client) -> None:
        """Initialize voice handler."""
        self.bot = bot_client
        self.voice_client: discord.VoiceClient | None = None
        self.target_channel: discord.VoiceChannel | discord.StageChannel | None = None
        self.synthesis_queue: asyncio.Queue = asyncio.Queue()
        self.audio_queue: asyncio.Queue = asyncio.Queue()
        self.is_playing = False
        self.current_group_id: str | None = None
        self.tasks: list[asyncio.Task] = []
        self.stats = {"messages_played": 0, "messages_skipped": 0, "errors": 0}

    async def start(self) -> None:
        """Start the voice handler tasks."""
        self.tasks = [
            asyncio.create_task(self._synthesis_task()),
            asyncio.create_task(self._playback_task()),
        ]
        logger.info("Voice handler started")

    async def connect_to_channel(self, channel_id: int) -> bool:
        """Connect to a voice channel."""
        try:
            channel = self.bot.get_channel(channel_id)
            if not isinstance(channel, (discord.VoiceChannel, discord.StageChannel)):
                logger.error(f"Channel {channel_id} is not a voice channel")
                return False

            self.target_channel = channel

            if self.voice_client and self.voice_client.is_connected():
                await self.voice_client.disconnect()

            self.voice_client = await channel.connect()
            logger.info(f"Connected to voice channel: {channel.name}")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to voice channel: {e}")
            return False

    async def add_to_queue(self, message_data: dict[str, Any]) -> None:
        """Add message to synthesis queue."""
        if not message_data.get("chunks"):
            return

        for i, chunk in enumerate(message_data["chunks"]):
            item = {
                "text": chunk,
                "user_id": message_data.get("user_id"),
                "username": message_data.get("username", "Unknown"),
                "group_id": message_data.get("group_id", f"msg_{id(message_data)}"),
                "chunk_index": i,
                "total_chunks": len(message_data["chunks"]),
            }
            await self.synthesis_queue.put(item)

    async def skip_current(self) -> int:
        """Skip the current message group."""
        if not self.current_group_id:
            return 0

        skipped = await self._clear_group_from_queues(self.current_group_id)

        if self.voice_client and self.voice_client.is_playing():
            self.voice_client.stop()

        self.stats["messages_skipped"] += 1
        logger.info(f"Skipped {skipped} chunks from group {self.current_group_id}")
        return skipped

    async def clear_all(self) -> int:
        """Clear all queues."""
        total = self.synthesis_queue.qsize() + self.audio_queue.qsize()

        while not self.synthesis_queue.empty():
            try:
                self.synthesis_queue.get_nowait()
            except asyncio.QueueEmpty:
                break

        while not self.audio_queue.empty():
            try:
                item = self.audio_queue.get_nowait()
                if len(item) > 0 and isinstance(item[0], str):
                    self._cleanup_audio_file(item[0])
            except asyncio.QueueEmpty:
                break

        if self.voice_client and self.voice_client.is_playing():
            self.voice_client.stop()

        logger.info(f"Cleared {total} items from queues")
        return total

    async def _synthesis_task(self) -> None:
        """Process synthesis queue and create audio files."""
        while True:
            try:
                item = await self.synthesis_queue.get()

                # Get user settings
                speaker_id = None
                engine_name = None
                if item.get("user_id"):
                    settings = user_settings.get_user_settings(str(item["user_id"]))
                    if settings:
                        speaker_id = settings.get("speaker_id")
                        engine_name = settings.get("engine")

                # Synthesize audio
                audio_data = await tts_engine.synthesize_audio(item["text"], speaker_id=speaker_id, engine_name=engine_name)

                if audio_data:
                    # Save to temporary file
                    import tempfile

                    with tempfile.NamedTemporaryFile(mode="wb", suffix=".wav", delete=False) as f:
                        f.write(audio_data)
                        audio_path = f.name
                    await self.audio_queue.put((audio_path, item["group_id"]))
                    logger.debug(f"Synthesized chunk {item['chunk_index']+1}/{item['total_chunks']}")
                else:
                    logger.error(f"Failed to synthesize: {item['text'][:50]}...")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Synthesis error: {e}")
                self.stats["errors"] += 1

    async def _playback_task(self) -> None:
        """Process audio queue and play audio files."""
        while True:
            try:
                audio_path, group_id = await self.audio_queue.get()

                if not self.voice_client or not self.voice_client.is_connected():
                    self._cleanup_audio_file(audio_path)
                    continue

                # Wait if already playing
                while self.voice_client.is_playing():
                    await asyncio.sleep(0.1)

                # Play audio
                self.current_group_id = group_id
                self.is_playing = True

                try:
                    audio_source = discord.FFmpegPCMAudio(audio_path)
                    self.voice_client.play(audio_source, after=partial(self._playback_complete, audio_path=audio_path))

                    # Wait for playback to complete
                    while self.voice_client.is_playing():
                        await asyncio.sleep(0.1)

                    self.stats["messages_played"] += 1

                except Exception as e:
                    logger.error(f"Playback error: {e}")
                    self._cleanup_audio_file(audio_path)
                    self.stats["errors"] += 1

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Playback task error: {e}")

    def _playback_complete(self, error: Exception | None, audio_path: str) -> None:
        """Handle playback completion."""
        self.is_playing = False
        self.current_group_id = None
        self._cleanup_audio_file(audio_path)

        if error:
            logger.error(f"Playback error: {error}")
            self.stats["errors"] += 1

    def _cleanup_audio_file(self, audio_path: str) -> None:
        """Clean up temporary audio file."""
        try:
            if audio_path and os.path.exists(audio_path):
                os.remove(audio_path)
        except Exception as e:
            logger.warning(f"Failed to cleanup audio file: {e}")

    async def _clear_group_from_queues(self, group_id: str) -> int:
        """Clear all items with specified group_id from queues."""
        cleared = 0

        # Clear synthesis queue
        items = []
        while not self.synthesis_queue.empty():
            try:
                item = self.synthesis_queue.get_nowait()
                if item.get("group_id") != group_id:
                    items.append(item)
                else:
                    cleared += 1
            except asyncio.QueueEmpty:
                break

        for item in items:
            await self.synthesis_queue.put(item)

        # Clear audio queue
        items = []
        while not self.audio_queue.empty():
            try:
                item = self.audio_queue.get_nowait()
                if item[1] != group_id:
                    items.append(item)
                else:
                    self._cleanup_audio_file(item[0])
                    cleared += 1
            except asyncio.QueueEmpty:
                break

        for item in items:
            await self.audio_queue.put(item)

        return cleared

    def get_status(self) -> dict[str, Any]:
        """Get current status information."""
        return {
            "connected": self.voice_client and self.voice_client.is_connected(),
            "playing": self.is_playing,
            "synthesis_queue_size": self.synthesis_queue.qsize(),
            "audio_queue_size": self.audio_queue.qsize(),
            "current_group": self.current_group_id,
            "messages_played": self.stats["messages_played"],
            "messages_skipped": self.stats["messages_skipped"],
            "errors": self.stats["errors"],
        }

    async def cleanup(self) -> None:
        """Clean up resources."""
        for task in self.tasks:
            task.cancel()

        await self.clear_all()

        if self.voice_client and self.voice_client.is_connected():
            await self.voice_client.disconnect()

        logger.info("Voice handler cleaned up")
