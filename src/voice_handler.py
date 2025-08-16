"""Voice connection handler for Discord Voice TTS Bot."""

import asyncio
from collections import deque
from typing import Any

import discord
from loguru import logger

from .config import config
from .tts_engine import tts_engine


class AudioQueueItem:
    """Represents an item in the audio playback queue."""

    def __init__(
        self,
        text: str,
        user_name: str = "",
        priority: int = 0,
        user_id: int | None = None,
        speaker_id: int | None = None,
        engine_name: str | None = None,
        message_group_id: str | None = None,
        chunk_index: int = 0,
        total_chunks: int = 1,
    ):
        """Initialize audio queue item.

        Args:
            text: Text content for TTS synthesis
            user_name: Name of the user who sent the message
            priority: Priority level (higher = played first)
            user_id: Discord user ID for speaker preference lookup
            speaker_id: Specific speaker ID to use for TTS
            engine_name: TTS engine to use ('voicevox' or 'aivis')
            message_group_id: ID to group chunks of the same message
            chunk_index: Index of this chunk in the message
            total_chunks: Total number of chunks in the message

        """
        self.text = text
        self.user_name = user_name
        self.priority = priority
        self.user_id = user_id
        self.speaker_id = speaker_id
        self.engine_name = engine_name
        self.message_group_id = message_group_id
        self.chunk_index = chunk_index
        self.total_chunks = total_chunks
        self.created_at = asyncio.get_event_loop().time()
        self.audio_source = None  # Pre-synthesized audio

    def __lt__(self, other: "AudioQueueItem") -> bool:
        """Compare for priority queue (higher priority first, then FIFO)."""
        if self.priority != other.priority:
            return self.priority > other.priority
        return self.created_at < other.created_at


class VoiceHandler:
    """Manages Discord voice connections and audio playback."""

    def __init__(self, bot_client: discord.Client) -> None:
        """Initialize voice handler.

        Args:
            bot_client: Discord bot client instance

        """
        self.bot = bot_client
        self.voice_client: discord.VoiceClient | None = None
        self.target_channel: discord.VoiceChannel | discord.StageChannel | None = None
        self.audio_queue: deque = deque(maxlen=config.message_queue_size * 3)  # Larger for chunks
        self.synthesis_queue: deque = deque()  # Queue for items awaiting synthesis
        self.is_playing = False
        self.is_connected = False
        self.reconnect_task: asyncio.Task | None = None
        self.playback_task: asyncio.Task | None = None
        self.synthesis_task: asyncio.Task | None = None
        self._should_stop = False
        self._current_message_group: str | None = None  # Track current message being played
        self._synthesis_cache: dict[str, Any] = {}  # Cache for pre-synthesized audio

        logger.info("Voice handler initialized")

    async def start(self) -> None:
        """Start the voice handler and begin playback processing."""
        self._should_stop = False

        # Start the playback task
        if not self.playback_task or self.playback_task.done():
            self.playback_task = asyncio.create_task(self._process_audio_queue())

        # Start the synthesis task for parallel processing
        if not self.synthesis_task or self.synthesis_task.done():
            self.synthesis_task = asyncio.create_task(self._process_synthesis_queue())

        logger.info("Voice handler started")

    async def stop(self) -> None:
        """Stop the voice handler and cleanup resources."""
        self._should_stop = True

        # Cancel tasks
        if self.reconnect_task and not self.reconnect_task.done():
            self.reconnect_task.cancel()

        if self.playback_task and not self.playback_task.done():
            self.playback_task.cancel()

        if self.synthesis_task and not self.synthesis_task.done():
            self.synthesis_task.cancel()

        # Clear synthesis cache
        for audio_source in self._synthesis_cache.values():
            tts_engine.cleanup_audio_source(audio_source)
        self._synthesis_cache.clear()

        # Disconnect from voice
        await self.disconnect()

        logger.info("Voice handler stopped")

    async def connect_to_channel(self, channel_id: int) -> bool:
        """Connect to voice channel.

        Args:
            channel_id: Discord voice channel ID

        Returns:
            True if connected successfully, False otherwise

        """
        try:
            # Get the target channel
            channel = self.bot.get_channel(channel_id)
            if not channel:
                logger.error(f"Voice channel {channel_id} not found")
                return False

            if not isinstance(channel, discord.VoiceChannel):
                logger.error(f"Channel {channel_id} is not a voice channel")
                return False

            self.target_channel = channel

            # Connect to voice channel
            if self.voice_client and self.voice_client.is_connected():
                if self.voice_client.channel.id == channel_id:
                    logger.info("Already connected to target voice channel")
                    self.is_connected = True
                    return True
                else:
                    # Move to different channel
                    await self.voice_client.move_to(channel)
                    logger.info(f"Moved to voice channel: {channel.name}")
            else:
                # New connection
                self.voice_client = await channel.connect(reconnect=True, timeout=10.0)
                logger.info(f"Connected to voice channel: {channel.name}")

            self.is_connected = True

            # Start TTS engine if not already started
            await tts_engine.start()

            return True

        except discord.ClientException as e:
            logger.error(f"Failed to connect to voice channel: {e!s}")
            return False

        except TimeoutError:
            logger.error("Voice connection timed out")
            return False

        except Exception as e:
            logger.error(f"Unexpected error connecting to voice: {type(e).__name__} - {e!s}")
            return False

    async def disconnect(self) -> None:
        """Disconnect from voice channel."""
        try:
            if self.voice_client:
                if self.voice_client.is_connected():
                    await self.voice_client.disconnect()
                    logger.info("Disconnected from voice channel")
                self.voice_client = None

            self.is_connected = False
            self.target_channel = None

        except Exception as e:
            logger.error(f"Error disconnecting from voice: {e!s}")

    async def ensure_connected(self) -> bool:
        """Ensure bot is connected to target voice channel.

        Returns:
            True if connected, False otherwise

        """
        if self.is_connected and self.voice_client and self.voice_client.is_connected():
            return True

        logger.info("Attempting to reconnect to voice channel")
        return await self.connect_to_channel(config.target_voice_channel_id)

    async def add_to_queue(
        self,
        text: str,
        user_name: str = "",
        priority: int = 0,
        user_id: int | None = None,
    ) -> bool:
        """Add text to audio playback queue.

        Args:
            text: Text to synthesize and play
            user_name: Name of user who sent the message
            priority: Priority level for queue ordering
            user_id: Discord user ID for speaker preference lookup

        Returns:
            True if added successfully, False otherwise

        """
        if not text or not text.strip():
            logger.debug("Skipping empty text for queue")
            return False

        # Look up user's speaker preference
        from .user_settings import user_settings

        speaker_id = None
        engine_name = None
        if user_id:
            user_settings_data = user_settings.get_user_settings(str(user_id))
            if user_settings_data:
                speaker_id = user_settings_data["speaker_id"]
                engine_name = user_settings_data["engine"]
                logger.debug(f"Using custom speaker {speaker_id} for user {user_id} (engine: {engine_name})")
            else:
                logger.debug(f"No custom settings for user {user_id}, using default")

        # Chunk long messages
        from .message_processor import message_processor

        chunks = message_processor.chunk_message(text.strip(), max_chunk_size=500)

        # Generate a unique message group ID for all chunks
        import uuid

        message_group_id = str(uuid.uuid4())

        # Add all chunks to synthesis queue
        for i, chunk in enumerate(chunks):
            queue_item = AudioQueueItem(
                chunk,
                user_name,
                priority,
                user_id,
                speaker_id,
                engine_name,
                message_group_id,
                i,
                len(chunks),
            )
            self.synthesis_queue.append(queue_item)

            if len(chunks) > 1:
                logger.debug(f"Added chunk {i+1}/{len(chunks)} to synthesis queue: '{chunk[:30]}...' from {user_name}")

        logger.debug(f"Added to synthesis queue (size: {len(self.synthesis_queue)}): {len(chunks)} chunk(s) from {user_name}")

        return True

    async def _process_audio_queue(self) -> None:
        """Process audio queue and play TTS messages."""
        logger.info("Started audio queue processing")

        while not self._should_stop:
            try:
                # Wait for queue items
                if not self.audio_queue:
                    await asyncio.sleep(0.1)
                    continue

                # Ensure we're connected
                if not await self.ensure_connected():
                    logger.warning("Not connected to voice channel, waiting...")
                    await asyncio.sleep(config.reconnect_delay)
                    continue

                # Get next item from queue
                queue_item = self.audio_queue.popleft()

                # Update current message group
                self._current_message_group = queue_item.message_group_id

                # Play the audio (now uses pre-synthesized audio)
                await self._play_tts_audio(queue_item)

                # Very small delay between chunks of same message, longer between different messages
                if self.audio_queue and self.audio_queue[0].message_group_id == queue_item.message_group_id:
                    await asyncio.sleep(0.1)  # Small gap between chunks
                else:
                    await asyncio.sleep(0.3)  # Slightly longer gap between different messages

            except asyncio.CancelledError:
                logger.info("Audio queue processing cancelled")
                break

            except Exception as e:
                logger.error(f"Error in audio queue processing: {type(e).__name__} - {e!s}")
                await asyncio.sleep(1)  # Wait before retrying

    async def _process_synthesis_queue(self) -> None:
        """Process synthesis queue and pre-synthesize audio."""
        logger.info("Started synthesis queue processing")

        while not self._should_stop:
            try:
                # Wait for items to synthesize
                if not self.synthesis_queue:
                    await asyncio.sleep(0.1)
                    continue

                # Check if we already have enough pre-synthesized audio
                if len(self.audio_queue) >= 3:
                    await asyncio.sleep(0.2)
                    continue

                # Get next item from synthesis queue
                item = self.synthesis_queue.popleft()

                # Skip if this message group was skipped
                if item.message_group_id != self._current_message_group and self._current_message_group:
                    # Check if any items from this group are already playing
                    playing_group_items = [q for q in self.audio_queue if q.message_group_id == item.message_group_id]
                    if not playing_group_items and item.chunk_index > 0:
                        # This is a later chunk of a skipped message
                        logger.debug(f"Skipping synthesis of chunk {item.chunk_index} from skipped message")
                        continue

                logger.info(
                    f"Synthesizing chunk {item.chunk_index + 1}/{item.total_chunks}: '{item.text[:30]}...' (Speaker: {item.speaker_id}, Engine: {item.engine_name or 'default'})"
                )

                # Synthesize the audio
                try:
                    audio_source = await tts_engine.create_audio_source(item.text, item.speaker_id, item.engine_name)
                    if audio_source:
                        item.audio_source = audio_source
                        # Add to playback queue
                        self.audio_queue.append(item)
                        logger.debug(f"Pre-synthesized and queued chunk {item.chunk_index + 1}/{item.total_chunks}")
                    else:
                        logger.error(f"Failed to synthesize chunk {item.chunk_index + 1}")
                except Exception as e:
                    logger.error(f"Error synthesizing audio: {e}")

            except asyncio.CancelledError:
                logger.info("Synthesis queue processing cancelled")
                break

            except Exception as e:
                logger.error(f"Error in synthesis queue processing: {type(e).__name__} - {e!s}")
                await asyncio.sleep(1)  # Wait before retrying

    async def _play_tts_audio(self, queue_item: AudioQueueItem) -> None:
        """Play TTS audio for queue item.

        Args:
            queue_item: Audio queue item to play

        """
        if not self.voice_client or not self.voice_client.is_connected():
            logger.warning("Cannot play audio: not connected to voice channel")
            return

        # Wait if already playing audio
        retry_count = 0
        max_retries = 300  # Max 30 seconds wait for long messages
        while self.voice_client.is_playing() and retry_count < max_retries:
            await asyncio.sleep(0.1)
            retry_count += 1

        if self.voice_client.is_playing():
            logger.warning(f"Still playing audio after {retry_count * 0.1:.1f} seconds, forcing stop")
            self.voice_client.stop()  # Force stop the current playback
            await asyncio.sleep(0.1)  # Brief pause after stopping

        try:
            self.is_playing = True

            # Use pre-synthesized audio if available
            audio_source = None
            if queue_item.audio_source:
                audio_source = queue_item.audio_source  # type: ignore[unreachable]
                logger.info(
                    f"Playing pre-synthesized chunk {queue_item.chunk_index + 1}/{queue_item.total_chunks} from {queue_item.user_name}"
                )
            else:
                # Fallback: synthesize on-demand (shouldn't happen normally)
                logger.warning(f"No pre-synthesized audio, synthesizing on-demand: '{queue_item.text[:30]}...'")
                audio_source = await tts_engine.create_audio_source(queue_item.text, queue_item.speaker_id)

            if not audio_source:
                logger.error("Failed to create audio source for TTS")
                return

            # Set Discord speaking state BEFORE playing audio
            try:
                # Type ignore for discord.py internal API
                await self.voice_client.ws.speak(True)  # type: ignore[arg-type]
                logger.debug("Set Discord speaking state to True")
            except Exception as e:
                logger.warning(f"Failed to set speaking state: {e}")

            # Create a future to track playback completion
            playback_done: asyncio.Future[None] = asyncio.Future()

            def after_playing(error: Exception | None) -> None:
                # Clear speaking state when done
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.run_coroutine_threadsafe(self._clear_speaking_state(), loop)
                except Exception as e:
                    logger.warning(f"Failed to clear speaking state: {e}")

                # Mark as not playing
                self.is_playing = False

                if error:
                    logger.error(f"Audio playback error: {error}")
                    if not playback_done.done():
                        playback_done.set_exception(Exception(f"Playback error: {error}"))
                else:
                    logger.debug("Audio playback completed successfully")
                    if not playback_done.done():
                        playback_done.set_result(None)

                # Cleanup audio source
                tts_engine.cleanup_audio_source(audio_source)

            # Start playing
            self.voice_client.play(audio_source, after=after_playing)

            # DON'T wait for playback to complete - return immediately
            # This allows the next audio to be prepared while this one plays
            logger.debug("Started audio playback, continuing to next item")

            # Just wait a tiny bit to ensure playback started
            await asyncio.sleep(0.05)

        except Exception as e:
            logger.error(f"Error playing TTS audio: {type(e).__name__} - {e!s}")
            self.is_playing = False

    async def _clear_speaking_state(self) -> None:
        """Clear Discord speaking state."""
        try:
            if self.voice_client and self.voice_client.ws:
                await self.voice_client.ws.speak(False)  # type: ignore[arg-type]  # Stop speaking indication
                logger.debug("Cleared Discord speaking state")
        except Exception as e:
            logger.warning(f"Failed to clear speaking state: {e}")

    async def skip_current(self) -> bool:
        """Skip currently playing audio and all chunks of the same message.

        Returns:
            True if skipped, False if nothing was playing

        """
        skipped = False

        # Stop current playback
        if self.voice_client and self.voice_client.is_playing():
            self.voice_client.stop()
            skipped = True
            logger.info("Stopped current audio playback")

        # Clear all chunks from the same message group
        if self._current_message_group:
            # Remove from audio queue
            initial_size = len(self.audio_queue)
            self.audio_queue = deque(
                [item for item in self.audio_queue if item.message_group_id != self._current_message_group],
                maxlen=self.audio_queue.maxlen,
            )
            removed_from_audio = initial_size - len(self.audio_queue)

            # Remove from synthesis queue
            initial_size = len(self.synthesis_queue)
            self.synthesis_queue = deque([item for item in self.synthesis_queue if item.message_group_id != self._current_message_group])
            removed_from_synthesis = initial_size - len(self.synthesis_queue)

            if removed_from_audio > 0 or removed_from_synthesis > 0:
                logger.info(f"Cleared {removed_from_audio} audio + {removed_from_synthesis} synthesis chunks from message group")
                skipped = True

            # Clear the current message group
            self._current_message_group = None

        if not skipped:
            logger.debug("No audio currently playing to skip")

        return skipped

    def clear_queue(self) -> int:
        """Clear all items from audio and synthesis queues.

        Returns:
            Number of items that were cleared

        """
        audio_count = len(self.audio_queue)
        synthesis_count = len(self.synthesis_queue)

        # Clear any pre-synthesized audio
        for item in self.audio_queue:
            if item.audio_source:
                tts_engine.cleanup_audio_source(item.audio_source)

        self.audio_queue.clear()
        self.synthesis_queue.clear()
        self._current_message_group = None

        total_count = audio_count + synthesis_count
        logger.info(f"Cleared {audio_count} audio + {synthesis_count} synthesis items (total: {total_count})")
        return total_count

    def get_queue_status(self) -> dict[str, Any]:
        """Get current queue status.

        Returns:
            Dictionary with queue status information

        """
        return {
            "audio_queue_size": len(self.audio_queue),
            "synthesis_queue_size": len(self.synthesis_queue),
            "total_queue_size": len(self.audio_queue) + len(self.synthesis_queue),
            "max_queue_size": config.message_queue_size,
            "is_playing": self.is_playing,
            "is_connected": self.is_connected,
            "voice_channel_id": self.target_channel.id if self.target_channel else None,
            "voice_channel_name": (self.target_channel.name if self.target_channel else None),
            "current_message_group": (self._current_message_group[:8] if self._current_message_group else None),
        }

    async def handle_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> None:
        """Handle voice state updates (for monitoring bot's own state).

        Args:
            member: Discord member whose voice state changed
            before: Voice state before the change
            after: Voice state after the change

        """
        # Only handle the bot's own voice state changes
        if not self.bot.user or member.id != self.bot.user.id:
            return

        # Check if bot was disconnected
        if before.channel and not after.channel:
            logger.warning("Bot was disconnected from voice channel")
            self.is_connected = False

            # Attempt to reconnect
            if not self._should_stop:
                if not self.reconnect_task or self.reconnect_task.done():
                    self.reconnect_task = asyncio.create_task(self._handle_disconnect())

        # Check if bot was moved to different channel
        elif before.channel and after.channel and before.channel.id != after.channel.id:
            if after.channel.id == config.target_voice_channel_id:
                logger.info("Bot was moved to target voice channel")
                self.target_channel = after.channel
                self.is_connected = True
            else:
                logger.warning(f"Bot was moved to non-target channel: {after.channel.name}")
                # Could implement auto-move back to target channel here

    async def _handle_disconnect(self) -> None:
        """Handle bot disconnection from voice channel."""
        logger.info("Handling voice disconnection, attempting reconnect...")

        # Wait a bit before reconnecting
        await asyncio.sleep(config.reconnect_delay)

        retry_count = 0
        max_retries = 5

        while retry_count < max_retries and not self._should_stop:
            if await self.connect_to_channel(config.target_voice_channel_id):
                logger.info("Successfully reconnected to voice channel")
                return

            retry_count += 1
            wait_time = config.reconnect_delay * (2**retry_count)  # Exponential backoff
            logger.warning(f"Reconnect attempt {retry_count} failed, waiting {wait_time}s...")
            await asyncio.sleep(wait_time)

        if retry_count >= max_retries:
            logger.error("Failed to reconnect after maximum retries")
            # Could implement notification to admin here


# Global voice handler instance (will be initialized with bot client)
voice_handler: VoiceHandler | None = None
