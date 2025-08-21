"""Voice connection handler for Discord Voice TTS Bot."""

import asyncio
import os
import time
from functools import partial
from typing import Any

import discord
from loguru import logger

from .tts_engine import tts_engine
from .user_settings import user_settings


class SimpleRateLimiter:
    """Simple rate limiter that respects Discord's global limit."""

    def __init__(self) -> None:
        self.last_request_time = 0.0

    async def wait_if_needed(self) -> None:
        """Wait to respect Discord's 50 requests per second global limit."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time

        # Discord allows 50 requests per second globally
        min_interval = 1.0 / 50.0

        if time_since_last < min_interval:
            wait_time = min_interval - time_since_last
            await asyncio.sleep(wait_time)

        self.last_request_time = time.time()


class CircuitBreaker:
    """Circuit breaker pattern for API failure handling."""

    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 60.0) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = 0.0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN


    async def can_make_request(self) -> bool:
        """Check if a request can be made."""
        current_time = time.time()

        if self.state == "CLOSED":
            return True
        elif self.state == "OPEN":
            if current_time - self.last_failure_time >= self.recovery_timeout:
                self.state = "HALF_OPEN"
                logger.info("Circuit breaker transitioning to HALF_OPEN state")
                return True
            return False
        else:  # HALF_OPEN
            return True

    async def record_success(self) -> None:
        """Record a successful request."""
        if self.state == "HALF_OPEN":
            self.state = "CLOSED"
            self.failure_count = 0
            logger.info("Circuit breaker transitioning to CLOSED state")

    async def record_failure(self) -> None:
        """Record a failed request."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            logger.error(f"Circuit breaker transitioning to OPEN state after {self.failure_count} failures")

    def get_state(self) -> dict[str, Any]:
        """Get current circuit breaker state."""
        return {"state": self.state, "failure_count": self.failure_count, "last_failure_time": self.last_failure_time}


class VoiceGatewayManager:
    """Manages voice gateway connections following Discord's official steps."""

    def __init__(self, voice_client: discord.VoiceClient):
        self.voice_client = voice_client
        self._session_id: str | None = None
        self._token: str | None = None
        self._endpoint: str | None = None
        self._guild_id: int | None = None
        self._connected = False

    async def handle_voice_server_update(self, payload: dict[str, Any]) -> None:
        """Handle VOICE_SERVER_UPDATE event following Discord's official steps."""
        try:
            self._token = payload.get("token")
            self._guild_id = payload.get("guild_id")
            self._endpoint = payload.get("endpoint")

            # Remove protocol if present and add voice gateway version
            if self._endpoint and "://" in self._endpoint:
                self._endpoint = self._endpoint.split("://")[1]

            logger.info(f"📡 Voice server update received - Guild: {self._guild_id}, Endpoint: {self._endpoint}")

            # The voice client handles the connection internally, but we ensure proper setup
            await self._ensure_proper_voice_setup()

        except Exception as e:
            logger.error(f"❌ Error handling voice server update: {e}")

    async def handle_voice_state_update(self, payload: dict[str, Any]) -> None:
        """Handle VOICE_STATE_UPDATE event."""
        try:
            self._session_id = payload.get("session_id")
            logger.info(f"🎤 Voice state update - Session ID: {self._session_id}")

            # Voice client handles the connection, but we track state for compliance
            if self._session_id and self.voice_client.is_connected():
                self._connected = True
                logger.info("✅ Voice gateway connection established with proper session")

        except Exception as e:
            logger.error(f"❌ Error handling voice state update: {e}")

    async def _ensure_proper_voice_setup(self) -> None:
        """Ensure voice connection follows Discord's official patterns."""
        try:
            # Discord.py handles most of the voice gateway internally
            # We focus on ensuring proper state and logging compliance

            # Verify connection state
            if self.voice_client.is_connected():
                logger.info("✅ Voice client connected with Discord API compliance")
                self._connected = True

                # Log connection details for transparency
                if hasattr(self.voice_client, "channel") and self.voice_client.channel:
                    logger.debug(f"🎵 Connected to voice channel: {self.voice_client.channel.name}")
                    logger.debug(f"🔊 Voice client SSRC: {getattr(self.voice_client, 'ssrc', 'Unknown')}")
            else:
                logger.warning("⚠️ Voice client not yet connected, waiting for handshake completion")

        except Exception as e:
            logger.error(f"❌ Error in voice setup validation: {e}")

    def get_connection_info(self) -> dict[str, Any]:
        """Get voice connection information for debugging."""
        return {
            "connected": self._connected,
            "session_id": self._session_id,
            "guild_id": self._guild_id,
            "has_token": self._token is not None,
            "endpoint": self._endpoint,
            "client_connected": self.voice_client.is_connected() if self.voice_client else False,
        }

    def is_connected(self) -> bool:
        """Check if voice gateway connection is established."""
        return self._connected and self.voice_client.is_connected()


class VoiceHandler:
    """Manages Discord voice connections and audio playback."""

    def __init__(self, bot_client: discord.Client) -> None:
        """Initialize voice handler."""
        self.bot = bot_client
        self.voice_client: discord.VoiceClient | None = None
        self.voice_gateway: VoiceGatewayManager | None = None
        self.target_channel: discord.VoiceChannel | discord.StageChannel | None = None
        self.synthesis_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self.audio_queue: asyncio.Queue[tuple[str, str, int, int]] = asyncio.Queue()
        self.is_playing = False
        self.current_group_id: str | None = None
        self.tasks: list[asyncio.Task[None]] = []
        self.stats = {"messages_played": 0, "messages_skipped": 0, "errors": 0}
        self._connection_state = "DISCONNECTED"
        self._last_connection_attempt = 0.0
        self._reconnection_cooldown = 5  # seconds
        self._recent_messages: list[int] = []

        # Simple rate limiter for Discord API compliance
        self.rate_limiter = SimpleRateLimiter()

    async def start(self) -> None:
        """Start the voice handler tasks."""
        # Diagnostics: ensure opus is loaded; if not, voice playback will fail
        try:
            import discord.opus as opus  # type: ignore

            if not opus.is_loaded():
                # Let discord.py attempt to locate the system opus library
                try:
                    opus.load_opus("opus")
                except Exception:
                    pass
            if not opus.is_loaded():
                logger.warning("Opus library is not loaded. Audio playback may fail. Install system libopus or ensure discord.py[voice] is correctly installed.")
        except Exception:
            # Best-effort only
            pass

        self.tasks = [
            asyncio.create_task(self._synthesis_task()),
            asyncio.create_task(self._playback_task()),
        ]
        logger.info("Voice handler started")

    def is_connected(self) -> bool:
        """Check if the bot is connected to a voice channel."""
        try:
            return self.voice_client is not None and self.voice_client.is_connected()
        except Exception:
            # If there's an error checking connection status, assume disconnected
            return False

    async def connect_to_channel(self, channel_id: int) -> bool:
        """Connect to a voice channel with comprehensive logging and error handling."""
        try:
            # Check reconnection cooldown
            now = asyncio.get_event_loop().time()
            time_since_last_attempt = now - self._last_connection_attempt
            if time_since_last_attempt < self._reconnection_cooldown:
                wait_time = self._reconnection_cooldown - time_since_last_attempt
                logger.debug(f"Connection attempt too soon, waiting {wait_time:.1f}s")
                await asyncio.sleep(wait_time)

            self._last_connection_attempt = now
            logger.info(f"🔄 ATTEMPTING VOICE CONNECTION - Channel ID: {channel_id}")
            logger.debug(f"Bot user: {self.bot.user}, Bot ID: {self.bot.user.id if self.bot.user else 'None'}")

            # Basic connection attempt
            logger.debug("🔗 ATTEMPTING VOICE CONNECTION")

            # Get channel information
            channel = self.bot.get_channel(channel_id)
            if not channel:
                logger.error(f"❌ CHANNEL NOT FOUND - Channel {channel_id} does not exist or is not accessible")
                logger.debug(f"Available channels: {[c.name for c in self.bot.guilds[0].channels] if self.bot.guilds else 'No guilds'}")
                return False

            if not isinstance(channel, (discord.VoiceChannel, discord.StageChannel)):
                channel_name = getattr(channel, "name", f"ID:{channel_id}")
                logger.error(f"❌ INVALID CHANNEL TYPE - Channel {channel_id} ({channel_name}) is not a voice channel")
                logger.debug(f"Channel type: {type(channel).__name__}, Expected: VoiceChannel or StageChannel")
                return False

            logger.info(f"📍 TARGET CHANNEL INFO - Name: {channel.name}, Type: {type(channel).__name__}, Guild: {channel.guild.name}")

            # Check current connection status
            if self.is_connected():
                current_channel_id = getattr(self.voice_client.channel, "id", None) if self.voice_client else None
                logger.debug(f"Current connection status: Connected to {self.voice_client.channel.name if self.voice_client else 'None'} (ID: {current_channel_id})")

                if current_channel_id == channel_id:
                    logger.info(f"✅ ALREADY CONNECTED - Already connected to target channel {channel.name}")
                    return True
                else:
                    if self.voice_client and self.voice_client.channel:
                        logger.info(f"🔄 MOVING CHANNELS - From {self.voice_client.channel.name} to {channel.name}")
                    else:
                        logger.info(f"🔄 MOVING CHANNELS - To {channel.name}")
                    try:
                        if self.voice_client:
                            await self.voice_client.move_to(channel)
                            logger.info(f"✅ SUCCESSFULLY MOVED - Now connected to voice channel: {channel.name}")
                            return True
                    except Exception as move_error:
                        logger.error(f"❌ MOVE FAILED - Error moving to channel {channel.name}: {move_error}")
                        # Disconnect and retry with fresh connection
                        if self.voice_client:
                            await self.voice_client.disconnect()
                            self.voice_client = None

            # Fresh connection attempt
            logger.info(f"🔗 ESTABLISHING NEW CONNECTION - Connecting to {channel.name}...")
            logger.debug(f"Channel permissions check: Bot can_connect={channel.permissions_for(channel.guild.me).connect if channel.guild.me else 'Unknown'}")

            try:
                self.voice_client = await channel.connect()
                logger.info(f"✅ CONNECTION SUCCESSFUL - Connected to voice channel: {channel.name}")

                # Initialize voice gateway manager for proper Discord API compliance
                self.voice_gateway = VoiceGatewayManager(self.voice_client)
                logger.info("🎯 Voice Gateway Manager initialized for Discord API compliance")

                # Verify the connection is stable by checking status immediately after connection
                await asyncio.sleep(0.5)  # Brief pause to let Discord process the connection
                is_still_connected = self.is_connected()
                logger.debug(f"Voice client details: {self.voice_client}, Connected: {is_still_connected}")

                if not is_still_connected:
                    logger.warning(f"⚠️ CONNECTION UNSTABLE - Discord immediately disconnected after connecting to {channel.name}")
                    logger.warning("This usually indicates a permissions issue or channel limit reached")
                    return False

                # Handle stage channel specifics
                if isinstance(channel, discord.StageChannel):
                    await asyncio.sleep(1)
                    if channel.guild.me and channel.guild.me.voice and channel.guild.me.voice.suppress:
                        logger.info("🎤 STAGE CHANNEL - Bot is suppressed, requesting to speak")
                        try:
                            await channel.guild.me.edit(suppress=False)
                            logger.info("🎤 STAGE CHANNEL - Successfully requested to speak")
                        except Exception as stage_error:
                            logger.warning(f"⚠️ STAGE CHANNEL - Failed to request speaking: {stage_error}")

                return True

            except discord.ClientException as client_error:
                logger.error(f"❌ CLIENT ERROR - Discord client error: {client_error}")
                logger.debug(f"Client error type: {type(client_error).__name__}")
                return False

            except discord.Forbidden as forbidden_error:
                logger.error(f"❌ FORBIDDEN - Permission denied connecting to {channel.name}: {forbidden_error}")
                logger.debug("Check bot permissions for the target voice channel")
                return False

            except discord.NotFound as not_found_error:
                logger.error(f"❌ NOT FOUND - Voice channel not found: {not_found_error}")
                return False

            except discord.HTTPException as http_error:
                logger.error(f"❌ HTTP ERROR - HTTP error during connection: {http_error}")
                logger.debug(f"HTTP status: {http_error.status}, Code: {http_error.code}")
                return False

            except Exception as connection_error:
                logger.error(f"❌ CONNECTION ERROR - Unexpected error connecting to {channel.name}: {connection_error}")
                logger.debug(f"Error type: {type(connection_error).__name__}")
                raise

        except Exception as e:
            logger.error(f"❌ CRITICAL CONNECTION FAILURE - Failed to connect to voice channel {channel_id}: {e}")
            logger.debug(f"Exception type: {type(e).__name__}, Full traceback:", exc_info=True)

            # Cleanup on failure - be more aggressive with cleanup
            await self.cleanup_voice_client()

            return False

    async def handle_voice_server_update(self, payload: dict[str, Any]) -> None:
        """Handle VOICE_SERVER_UPDATE event with proper Discord API compliance."""
        if self.voice_gateway:
            await self.voice_gateway.handle_voice_server_update(payload)
        else:
            logger.warning("⚠️ Voice gateway manager not initialized, cannot handle voice server update")

    async def handle_voice_state_update(self, payload: dict[str, Any]) -> None:
        """Handle VOICE_STATE_UPDATE event with proper Discord API compliance."""
        if self.voice_gateway:
            await self.voice_gateway.handle_voice_state_update(payload)
        else:
            logger.warning("⚠️ Voice gateway manager not initialized, cannot handle voice state update")

    async def make_rate_limited_request(self, api_call: Any, *args: Any, **kwargs: Any) -> Any:
        """Make a simple rate-limited API request respecting Discord's limits."""
        await self.rate_limiter.wait_if_needed()

        try:
            result = await api_call(*args, **kwargs)
            return result
        except discord.HTTPException as e:
            if e.status == 429:  # Rate limited by Discord
                # Handle both real responses and mock objects in tests
                retry_after = "1"  # Default value
                if e.response:
                    try:
                        # Try to get headers from response
                        headers = getattr(e.response, "headers", {})
                        if hasattr(headers, "get"):
                            retry_after = headers.get("Retry-After", "1")
                    except (AttributeError, TypeError):
                        # Fallback for mock objects or malformed responses
                        retry_after = "1"

                logger.warning(f"Discord rate limit hit, retrying after {retry_after}s")
                await asyncio.sleep(float(retry_after))
                # Retry once after rate limit
                return await api_call(*args, **kwargs)
            else:
                raise

    async def add_to_queue(self, message_data: dict[str, Any]) -> None:
        """Add message to synthesis queue with deduplication."""
        if not message_data.get("chunks"):
            return

        # Check for message deduplication
        message_hash = hash(message_data.get("original_content", ""))
        if hasattr(self, "_recent_messages"):
            if message_hash in self._recent_messages:
                logger.debug("Duplicate message detected, skipping")
                return
            # Keep only last 100 message hashes
            if len(self._recent_messages) > 100:
                self._recent_messages.pop(0)
            self._recent_messages.append(message_hash)
        else:
            self._recent_messages = [message_hash]

        # Check queue size limits
        if self.synthesis_queue.qsize() >= 100:  # Max 100 items in synthesis queue
            logger.warning("Synthesis queue full, dropping message")
            return

        for i, chunk in enumerate(message_data["chunks"]):
            item = {
                "text": chunk,
                "user_id": message_data.get("user_id"),
                "username": message_data.get("username", "Unknown"),
                "group_id": message_data.get("group_id", f"msg_{id(message_data)}"),
                "chunk_index": i,
                "total_chunks": len(message_data["chunks"]),
                "message_hash": message_hash,
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
                if len(item) > 0:
                    self._cleanup_audio_file(item[0])
            except asyncio.QueueEmpty:
                break

        if self.voice_client and self.voice_client.is_playing():
            self.voice_client.stop()

        logger.info(f"Cleared {total} items from queues")
        return total

    async def _synthesis_task(self) -> None:
        """Process synthesis queue and create audio files with enhanced buffer management."""
        audio_buffer_size = 0
        max_buffer_size = 50 * 1024 * 1024  # 50MB limit

        while True:
            try:
                item = await self.synthesis_queue.get()

                # Check buffer size before processing
                if audio_buffer_size >= max_buffer_size:
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
                    if not self._validate_audio_format(audio_data):
                        logger.error(f"Invalid audio format for: {item['text'][:50]}...")
                        continue

                    # Check audio size
                    audio_size = len(audio_data)
                    if audio_size > 10 * 1024 * 1024:  # 10MB per audio file
                        logger.warning(f"Audio file too large ({audio_size} bytes), skipping")
                        continue

                    # Save to temporary file with proper cleanup tracking
                    import tempfile

                    with tempfile.NamedTemporaryFile(mode="wb", suffix=".wav", delete=False) as f:
                        f.write(audio_data)
                        audio_path = f.name

                    # Track buffer size
                    audio_buffer_size += audio_size

                    # Add to priority queue
                    priority = self._calculate_message_priority(item)
                    await self.audio_queue.put((audio_path, item["group_id"], priority, audio_size))
                    logger.debug(f"Synthesized chunk {item['chunk_index'] + 1}/{item['total_chunks']} (size: {audio_size} bytes)")

                else:
                    logger.error(f"Failed to synthesize: {item['text'][:50]}...")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Synthesis error: {e}")
                self.stats["errors"] += 1

    async def _playback_task(self) -> None:
        """Process audio queue and play audio files with priority handling."""
        while True:
            try:
                # Get highest priority item from queue
                queue_item = await self._get_highest_priority_item()

                if not queue_item:
                    await asyncio.sleep(0.1)
                    continue

                audio_path, group_id, priority, audio_size = queue_item

                if not self.voice_client or not self.voice_client.is_connected():
                    self._cleanup_audio_file(audio_path)
                    logger.debug(f"Skipping playback of {audio_path} (size: {audio_size} bytes) - not connected")
                    continue

                # Wait if already playing
                while self.voice_client.is_playing():
                    await asyncio.sleep(0.1)

                # Play audio with enhanced error handling
                self.current_group_id = group_id
                self.is_playing = True

                try:
                    audio_source = discord.FFmpegPCMAudio(audio_path)
                    self.voice_client.play(audio_source, after=partial(self._playback_complete, audio_path=audio_path))

                    # Wait for playback to complete with timeout
                    waited = 0
                    while self.voice_client.is_playing() and waited < 300:  # 5 minute timeout
                        await asyncio.sleep(0.1)
                        waited += 1

                    if waited >= 300:
                        logger.warning(f"Audio playback timeout for {audio_path}")
                        self.voice_client.stop()

                    self.stats["messages_played"] += 1
                    logger.debug(f"Played audio: {audio_path} (priority: {priority})")

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

    def _validate_audio_format(self, audio_data: bytes) -> bool:
        """Validate audio data format and basic properties."""
        try:
            if len(audio_data) < 44:  # WAV header is at least 44 bytes
                return False

            # Check WAV header
            if audio_data[:4] != b"RIFF" or audio_data[8:12] != b"WAVE":
                return False

            # Extract basic format info
            channels = int.from_bytes(audio_data[22:24], byteorder="little")
            sample_rate = int.from_bytes(audio_data[24:28], byteorder="little")
            bits_per_sample = int.from_bytes(audio_data[34:36], byteorder="little")

            # Validate reasonable audio parameters
            if channels not in [1, 2]:
                return False
            if sample_rate not in [8000, 16000, 22050, 44100, 48000]:
                return False
            if bits_per_sample not in [8, 16, 24, 32]:
                return False

            return True

        except Exception as e:
            logger.error(f"Audio format validation error: {e}")
            return False

    def _calculate_message_priority(self, item: dict[str, Any]) -> int:
        """Calculate priority for message processing."""
        priority = 5  # Default priority

        # Higher priority for shorter messages (quicker processing)
        if len(item.get("text", "")) < 50:
            priority -= 1

        # Higher priority for commands
        if item.get("text", "").startswith("!"):
            priority -= 2

        # Lower priority for very long messages
        if len(item.get("text", "")) > 200:
            priority += 2

        return max(1, min(10, priority))  # Clamp between 1-10

    async def _get_highest_priority_item(self) -> tuple[str, str, int, int] | None:
        """Get the highest priority item from the audio queue."""
        if self.audio_queue.empty():
            return None

        # Convert queue to list to find highest priority item
        items: list[tuple[str, str, int, int]] = []
        while not self.audio_queue.empty():
            try:
                item = self.audio_queue.get_nowait()  # type: ignore[assignment]
                items.append(item)  # type: ignore[arg-type]
            except asyncio.QueueEmpty:
                break

        if not items:
            return None

        # Find highest priority item (lower number = higher priority)
        items.sort(key=lambda x: x[2])  # type: ignore[arg-type] # Sort by priority (index 2)
        highest_priority_item = items[0]

        # Put back all items except the highest priority one
        for item in items[1:]:
            await self.audio_queue.put(item)  # type: ignore[arg-type]

        return highest_priority_item

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
        synthesis_items: list[dict[str, Any]] = []
        while not self.synthesis_queue.empty():
            try:
                item = self.synthesis_queue.get_nowait()
                if item.get("group_id") != group_id:
                    synthesis_items.append(item)
                else:
                    cleared += 1
            except asyncio.QueueEmpty:
                break

        for item in synthesis_items:
            await self.synthesis_queue.put(item)

        # Clear audio queue
        items: list[tuple[str, str, int, int]] = []
        while not self.audio_queue.empty():
            try:
                item = self.audio_queue.get_nowait()  # type: ignore[assignment]
                if item[1] != group_id:  # type: ignore[index]
                    items.append(item)  # type: ignore[arg-type]
                else:
                    self._cleanup_audio_file(item[0])  # type: ignore[index]
                    cleared += 1
            except asyncio.QueueEmpty:
                break

        for item in items:  # type: ignore[assignment]
            await self.audio_queue.put(item)  # type: ignore[arg-type]

        return cleared

    def get_status(self) -> dict[str, Any]:
        """Get current status information."""
        connected = bool(self.voice_client and self.voice_client.is_connected())
        channel_name = None
        channel_id = None

        try:
            if self.voice_client and getattr(self.voice_client, "channel", None):
                channel_name = self.voice_client.channel.name  # type: ignore[attr-defined]
                channel_id = self.voice_client.channel.id  # type: ignore[attr-defined]
            elif self.target_channel:
                channel_name = self.target_channel.name
                channel_id = self.target_channel.id
        except Exception as e:
            logger.debug(f"Error getting channel info: {e}")

        return {
            "connected": connected,
            "voice_connected": connected,  # compatibility for UI/status uses
            "voice_channel_name": channel_name,
            "voice_channel_id": channel_id,
            "playing": self.is_playing,
            "synthesis_queue_size": self.synthesis_queue.qsize(),
            "audio_queue_size": self.audio_queue.qsize(),
            "total_queue_size": self.synthesis_queue.qsize() + self.audio_queue.qsize(),
            "current_group": self.current_group_id,
            "messages_played": self.stats["messages_played"],
            "messages_skipped": self.stats["messages_skipped"],
            "errors": self.stats["errors"],
            "connection_state": self._connection_state,
            "is_playing": self.is_playing,
            "max_queue_size": 50,  # Add max queue size for UI
        }

    async def health_check(self) -> dict[str, Any]:
        """Perform comprehensive voice connection health check."""
        logger.debug("🔍 Performing voice connection health check...")

        health_status: dict[str, Any] = {
            "healthy": False,
            "issues": [],
            "recommendations": [],
            "voice_client_exists": self.voice_client is not None,
            "voice_client_connected": False,
            "channel_accessible": False,
            "can_synthesize": False,
            "audio_playback_ready": False,
        }

        # Check voice client
        if not self.voice_client:
            health_status["issues"].append("Voice client not initialized")
            health_status["recommendations"].append("Call connect_to_channel() to establish connection")
        else:
            # Check connection status
            try:
                is_connected = self.voice_client.is_connected()
                health_status["voice_client_connected"] = is_connected

                if not is_connected:
                    health_status["issues"].append("Voice client not connected")
                    health_status["recommendations"].append("Check voice channel permissions and network connectivity")
                else:
                    logger.debug("✅ Voice client is connected")

                    # Check channel accessibility
                    if hasattr(self.voice_client, "channel") and self.voice_client.channel:
                        channel = self.voice_client.channel
                        health_status["channel_accessible"] = True
                        logger.debug(f"✅ Connected to channel: {channel.name} (ID: {channel.id})")

                        # Check if we can actually play audio
                        if not self.voice_client.is_playing():
                            health_status["audio_playback_ready"] = True
                            logger.debug("✅ Audio playback is ready")
                        else:
                            health_status["issues"].append("Audio is currently playing")
                            logger.debug("ℹ️ Audio is currently playing")
                    else:
                        health_status["issues"].append("Voice client has no associated channel")
                        health_status["recommendations"].append("Voice client may be in disconnected state")

            except Exception as e:
                health_status["issues"].append(f"Error checking voice client: {e}")
                logger.debug(f"⚠️ Voice client check error: {e}")

        # Check TTS synthesis capability
        try:
            from .tts_engine import tts_engine

            if await tts_engine.health_check():
                health_status["can_synthesize"] = True
                logger.debug("✅ TTS engine is healthy")
            else:
                health_status["issues"].append("TTS engine health check failed")
                health_status["recommendations"].append("Check TTS API availability and configuration")
        except Exception as e:
            health_status["issues"].append(f"TTS engine check failed: {e}")
            logger.debug(f"⚠️ TTS engine check error: {e}")

        # Overall health assessment
        critical_issues = [issue for issue in health_status["issues"] if any(keyword in issue.lower() for keyword in ["not initialized", "not connected", "failed", "error"])]

        if not critical_issues:
            health_status["healthy"] = True
            logger.debug("🎉 Voice system health check PASSED")
        else:
            logger.debug(f"💥 Voice system health check FAILED: {len(critical_issues)} critical issues")
            for issue in critical_issues:
                logger.debug(f"   - {issue}")

        return health_status

    async def cleanup(self) -> None:
        """Clean up resources."""
        for task in self.tasks:
            task.cancel()

        await self.clear_all()

        if self.voice_client and self.voice_client.is_connected():
            await self.voice_client.disconnect()
        self._connection_state = "DISCONNECTED"

        logger.info("Voice handler cleaned up")

    async def cleanup_voice_client(self) -> None:
        """Aggressively clean up voice client state."""
        if not self.voice_client:
            return

        logger.debug("🧹 Cleaning up voice client...")

        try:
            # Try to disconnect gracefully first
            if hasattr(self.voice_client, "is_connected") and self.voice_client.is_connected():
                await self.voice_client.disconnect()
                logger.debug("✅ Voice client disconnected gracefully")
            else:
                logger.debug("ℹ️ Voice client was already disconnected")
        except Exception as e:
            logger.warning(f"⚠️ Error during graceful disconnect: {e}")

        try:
            # Force cleanup by setting to None
            self.voice_client = None
            logger.debug("✅ Voice client reference cleared")
        except Exception as e:
            logger.error(f"💥 Error clearing voice client reference: {e}")

        # Update connection state
        self._connection_state = "DISCONNECTED"
