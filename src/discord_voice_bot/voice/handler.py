"""Voice handler facade for Discord Voice TTS Bot."""

import asyncio
from typing import Any

import discord
from loguru import logger

from .gateway import VoiceGatewayManager
from .health import health_check
from .queues import PriorityAudioQueue, SynthesisQueue
from .ratelimit import CircuitBreaker, SimpleRateLimiter
from .status import build_status
from .workers.player import PlayerWorker
from .workers.synthesizer import SynthesizerWorker


class VoiceHandler:
    """Manages Discord voice connections and audio playback."""

    def __init__(self, bot_client: discord.Client) -> None:
        """Initialize voice handler."""
        self.bot = bot_client
        self.voice_client: discord.VoiceClient | None = None
        self.voice_gateway: VoiceGatewayManager | None = None
        self.target_channel: discord.VoiceChannel | discord.StageChannel | None = None
        self.synthesis_queue = SynthesisQueue(maxsize=100)
        self.audio_queue = PriorityAudioQueue()
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
        # Circuit breaker for API failure handling
        self.circuit_breaker = CircuitBreaker()

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
            asyncio.create_task(SynthesizerWorker(self).run()),
            asyncio.create_task(PlayerWorker(self).run()),
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
        """Make a rate-limited API request with circuit breaker pattern."""
        # Check circuit breaker state first
        if not await self.circuit_breaker.can_make_request():
            logger.error("Circuit breaker is OPEN, skipping request")
            raise discord.HTTPException(None, "Circuit breaker is open")

        await self.rate_limiter.wait_if_needed()

        try:
            result = await api_call(*args, **kwargs)
            # Record success in circuit breaker
            await self.circuit_breaker.record_success()
            return result
        except discord.HTTPException as e:
            # Record failure in circuit breaker for non-rate-limit errors
            if e.status != 429:
                await self.circuit_breaker.record_failure()

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

        skipped = await self.audio_queue.clear_group(self.current_group_id)

        if self.voice_client and self.voice_client.is_playing():
            self.voice_client.stop()

        self.stats["messages_skipped"] += 1
        logger.info(f"Skipped {skipped} chunks from group {self.current_group_id}")
        return skipped

    async def clear_all(self) -> int:
        """Clear all queues."""
        total = self.synthesis_queue.qsize() + self.audio_queue.qsize()

        await self.synthesis_queue.clear()
        await self.audio_queue.clear()

        if self.voice_client and self.voice_client.is_playing():
            self.voice_client.stop()

        logger.info(f"Cleared {total} items from queues")
        return total

    def get_status(self) -> dict[str, Any]:
        """Get current status information."""
        return build_status(self)

    async def health_check(self) -> dict[str, Any]:
        """Perform comprehensive voice connection health check."""
        return await health_check(self)

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
