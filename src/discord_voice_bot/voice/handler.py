# pyright: reportImplicitOverride=false
"""Voice handler facade for Discord Voice TTS Bot."""

import asyncio
from typing import TYPE_CHECKING, Any, Protocol

import discord
from loguru import logger

from ..config import Config

if TYPE_CHECKING:
    from .gateway import VoiceGatewayManager

# Import new manager classes
from .connection_manager import VoiceConnectionManager
from .health_monitor import HealthMonitor
from .queue_manager import QueueManager
from .rate_limiter_manager import RateLimiterManager
from .stats_tracker import StatsTracker
from .task_manager import TaskManager

# Import worker classes for type hints and instance management
from .workers.player import PlayerWorker
from .workers.synthesizer import SynthesizerWorker


class NullVoiceClient:
    """Minimal stub voice client for tests and uninitialized state."""

    channel = None

    def is_connected(self) -> bool:  # pragma: no cover - trivial
        """
        Return whether a voice client is connected.
        
        For the null stub client this always returns False.

        Returns:
            bool: False, indicating no active voice connection.

        """
        return False

    def is_playing(self) -> bool:  # pragma: no cover - trivial
        """
        Return whether audio is currently playing.
        
        This stub implementation always reports False (no audio is playing).
        
        Returns:
            bool: Always False.

        """
        return False

    def stop(self) -> None:  # pragma: no cover - trivial
        """
        No-op stop method for the null voice client.
        
        This method intentionally does nothing and exists to provide a compatible interface with real voice clients
        when no voice connection is present (e.g., testing or uninitialized state).
        """
        return

    async def disconnect(self) -> None:  # pragma: no cover - trivial
        """
        No-op asynchronous disconnect for the null/stub voice client.
        
        Implements the async disconnect signature of a real voice client but performs no action and returns immediately.
        """
        return


class VoiceHandlerInterface(Protocol):
    """Interface for voice handler to avoid circular imports."""

    synthesis_queue: Any
    audio_queue: Any
    config: Config
    # voice client property contract
    voice_client: Any
    target_channel: Any
    current_group_id: str | None
    is_playing: bool
    stats: Any
    connection_state: str
    synthesizer: "SynthesizerWorker | None"

    async def start(self) -> None:
        """Start the voice handler tasks."""
        ...

    def is_connected(self) -> bool:
        """Check if the bot is connected to a voice channel."""
        ...

    async def connect_to_channel(self, channel_id: int) -> bool:
        """Connect to a voice channel."""
        ...

    async def handle_voice_server_update(self, payload: dict[str, Any]) -> None:
        """Handle VOICE_SERVER_UPDATE event."""
        ...

    async def handle_voice_state_update(self, payload: dict[str, Any]) -> None:
        """Handle VOICE_STATE_UPDATE event."""
        ...

    async def make_rate_limited_request(self, api_call: Any, *args: Any, **kwargs: Any) -> Any:
        """Make a rate-limited API request."""
        ...

    async def add_to_queue(self, message_data: dict[str, Any]) -> None:
        """Add message to synthesis queue."""
        ...

    async def skip_current(self) -> int:
        """Skip the current message group."""
        ...

    async def clear_all(self) -> int:
        """Clear all queues."""
        ...

    def get_status(self) -> dict[str, Any]:
        """Get current status information."""
        ...

    async def health_check(self) -> dict[str, Any]:
        """Perform voice connection health check."""
        ...

    async def cleanup(self) -> None:
        """Clean up resources."""
        ...

    async def cleanup_voice_client(self) -> None:
        """Clean up voice client state."""
        ...


class VoiceHandler(VoiceHandlerInterface):
    """Manages Discord voice connections and audio playback using facade pattern."""

    def __init__(self, bot_client: discord.Client, config: Config, tts_client: Any | None = None) -> None:
        """
        Create a VoiceHandler and wire up its manager components, health monitor, and backward-compatible attributes.
        
        Initializes the connection, queue, rate-limiter, stats, and task managers; constructs a HealthMonitor (injecting a TTS client if none is provided); and sets legacy-compatible properties (is_playing, target_channel, connection_state, synthesis_queue, audio_queue, current_group_id, stats, rate_limiter, circuit_breaker, tasks) so existing callers/tests continue to work. Also prepares internal worker slots (_synthesizer_worker, _player_worker) for later lifecycle management.
        
        Parameters:
            bot_client: Discord client used for gateway interactions.
            config: Effective configuration for voice behavior.
            tts_client: Optional TTS client instance used by the HealthMonitor (primarily for testing or custom TTS implementations). If omitted, a default TTSClient is created from the provided config.

        """
        super().__init__()
        self.bot = bot_client
        self.config = config

        # Initialize manager components
        from ..config_manager import ConfigManagerImpl

        self.connection_manager = VoiceConnectionManager(bot_client, ConfigManagerImpl(config))
        self.queue_manager = QueueManager()
        self.rate_limiter_manager = RateLimiterManager()
        self.stats_tracker = StatsTracker()
        self.task_manager = TaskManager()
        if tts_client is None:
            from ..tts_client import TTSClient as _TTSClient

            tts_client = _TTSClient(config)
        self.health_monitor = HealthMonitor(self.connection_manager, ConfigManagerImpl(config), tts_client)

        # Maintain backward compatibility properties
        self.is_playing = False

        # Delegate properties to managers for backward compatibility
        # Access voice_client through dynamic property to avoid stale copies
        self.target_channel = self.connection_manager.target_channel
        self.connection_state = self.connection_manager.connection_state
        self.synthesis_queue = self.queue_manager.synthesis_queue
        self.audio_queue = self.queue_manager.audio_queue
        self.current_group_id = self.queue_manager.current_group_id
        # Dict-like stats for backward compatibility in tests
        self.stats = {
            "messages_processed": 0,
            "connection_errors": 0,
            "tts_messages_played": 0,
        }

        # Backward compatibility for rate limiter
        self.rate_limiter = self.rate_limiter_manager.rate_limiter
        self.circuit_breaker = self.rate_limiter_manager.circuit_breaker

        # Backward compatibility for connection attempt tracking - use properties for proper encapsulation
        self._last_connection_attempt = self.connection_manager.last_connection_attempt
        self._reconnection_cooldown = self.connection_manager.reconnection_cooldown

        # Backward compatibility for task management
        self.tasks = self.task_manager.tasks

        # Worker instances for graceful shutdown
        self._synthesizer_worker: SynthesizerWorker | None = None
        self._player_worker: PlayerWorker | None = None

    synthesizer: SynthesizerWorker | None = None

    @property
    def voice_gateway(self):
        """Get voice gateway from connection manager."""
        return self.connection_manager.voice_gateway

    @voice_gateway.setter
    def voice_gateway(self, value: "VoiceGatewayManager | None") -> None:
        """
        Set the voice gateway manager used by the connection manager.
        
        If `value` is None, clear the current gateway reference.
        """
        self.connection_manager.voice_gateway = value

    async def start(self, start_player: bool = True) -> None:
        """
        Start the voice handler: perform a best-effort Opus availability check and start background worker tasks.
        
        This coroutine checks for the Opus library (tries to load it if missing) as a diagnostic step — failures are logged and do not prevent startup. After the Opus check completes, it creates and starts the synthesizer worker and, if requested, the player worker.
        
        Parameters:
            start_player: If True (default), start the player worker in addition to the synthesizer worker.

        """
        # Diagnostics: ensure opus is loaded; if not, voice playback will fail
        try:
            logger.debug("🔊 Checking Opus library availability...")
            import discord.opus as opus

            if not opus.is_loaded():
                logger.debug("🔊 Opus library not loaded, attempting to load 'opus'...")
                try:
                    opus.load_opus("opus")
                    logger.debug("✅ Opus library loaded successfully via 'opus'")
                except Exception as e:
                    logger.debug(f"❌ Failed to load Opus via 'opus': {e}")
            else:
                logger.debug("✅ Opus library already loaded")

            if not opus.is_loaded():
                logger.warning("Opus library is not loaded. Audio playback may fail. Install system libopus or ensure discord.py[voice] is correctly installed.")
            else:
                logger.debug("✅ Opus library is available for audio playback")
        except Exception as e:
            logger.debug(f"❌ Error checking Opus library: {e}")
            # Best-effort only

        # Start worker tasks
        await self._start_workers(start_player)
        # Workers are created externally to avoid import cycles
        # The tasks list will be populated by external components

    async def _start_workers(self, start_player: bool = True) -> None:
        """Start the worker tasks for processing queues."""
        try:
            # Create workers
            synthesizer_worker = SynthesizerWorker(self, self.config)

            # Store worker instances for graceful shutdown
            self._synthesizer_worker = synthesizer_worker
            self.synthesizer = synthesizer_worker

            # Start synthesizer worker task
            synthesizer_task = asyncio.create_task(synthesizer_worker.run())
            self.add_worker_task(synthesizer_task)

            # Start player worker only if requested
            if start_player:
                player_worker = PlayerWorker(self)
                self._player_worker = player_worker
                player_task = asyncio.create_task(player_worker.run())
                self.add_worker_task(player_task)

            logger.info("✅ Worker tasks started successfully")

        except Exception as e:
            logger.error(f"❌ Failed to start worker tasks: {e}")
            raise

    def add_worker_task(self, task: asyncio.Task[None]) -> None:
        """Add a worker task to be managed by the handler."""
        self.task_manager.add_task(task)

    def stop_workers(self) -> None:
        """
        Signal synthesizer and player workers to stop and clear the external synthesizer reference.
        
        If present, calls each worker's stop() method (best-effort) and sets self.synthesizer to None.
        This does not wait for the worker tasks to finish; task cleanup is handled separately by the task manager.
        """
        if self._synthesizer_worker:
            self._synthesizer_worker.stop()
        if self._player_worker:
            self._player_worker.stop()
        self.synthesizer = None
        logger.info("Sent stop signal to workers")

    def _get_voice_client(self) -> Any:
        """
        Return the current voice client from the connection manager, or a NullVoiceClient when none is set.
        
        Returns:
            Any: The active voice client instance from the connection manager, or a NullVoiceClient() stub if no client is present.

        """
        vc = self.connection_manager.voice_client
        return vc if vc is not None else NullVoiceClient()

    def _set_voice_client(self, value: Any) -> None:
        """
        Set the active voice client on the underlying connection manager.
        """
        self.connection_manager.voice_client = value

    voice_client = property(_get_voice_client, _set_voice_client)

    def is_connected(self) -> bool:
        """Check if the bot is connected to a voice channel."""
        return self.connection_manager.is_connected()

    async def connect_to_channel(self, channel_id: int) -> bool:
        """
        Connect to a Discord voice channel by ID.
        
        Attempts to establish a voice connection for the given Discord channel ID and returns whether the connection succeeded.
        
        Parameters:
            channel_id: Discord channel (snowflake) ID to connect to.
        
        Returns:
            bool: True if the connection was established, False otherwise.

        """
        return await self.connection_manager.connect_to_channel(channel_id)

    async def handle_voice_server_update(self, payload: dict[str, Any]) -> None:
        """
        Handle a Discord VOICE_SERVER_UPDATE event.
        
        Delegates the raw VOICE_SERVER_UPDATE payload (the event data received from Discord) to the VoiceConnectionManager to update voice gateway connection details.
        """
        await self.connection_manager.handle_voice_server_update(payload)

    async def handle_voice_state_update(self, payload: dict[str, Any]) -> None:
        """
        Handle a Discord VOICE_STATE_UPDATE gateway event by delegating it to the VoiceConnectionManager.
        
        Parameters:
            payload: Raw VOICE_STATE_UPDATE gateway event payload as received from Discord.

        """
        await self.connection_manager.handle_voice_state_update(payload)

    async def make_rate_limited_request(self, api_call: Any, *args: Any, **kwargs: Any) -> Any:
        """
        Make a rate-limited API request using the configured rate limiter and circuit breaker.
        
        Parameters
            api_call (Callable): The callable to invoke under rate limiting/circuit-breaking. May be a coroutine function or regular callable.
            *args: Positional arguments forwarded to `api_call`.
            **kwargs: Keyword arguments forwarded to `api_call`.
        
        Returns
            Any: The result returned by `api_call`.

        """
        return await self.rate_limiter_manager.make_rate_limited_request(api_call, *args, **kwargs)

    async def add_to_queue(self, message_data: dict[str, Any]) -> None:
        """
        Enqueue a synthesis task for TTS playback, with duplicate detection.
        
        The provided `message_data` dictionary represents a synthesis task (content and any required metadata)
        and will be enqueued for processing. The queue manager performs deduplication so identical or
        already-scheduled tasks will not be added multiple times.
        
        Parameters
            message_data (dict[str, Any]): Payload describing the message to synthesize (text, voice, group id, etc.).
        
        Returns
            None

        """
        await self.queue_manager.add_to_queue(message_data)

    async def skip_current(self, group_id: str | None = None) -> int:
        """
        Skip the currently playing message group and clear its pending chunks.
        
        If a group_id is provided, updates the handler's current_group_id (and the QueueManager's current_group_id) before skipping.
        Skips items from both the audio playback queue and the synthesis queue for the active group, stops the voice client if it's playing, and increments the internal "messages skipped" counter.
        
        Parameters
            group_id (str | None): Optional group identifier to target for skipping; if omitted, the handler's current_group_id is used.
        
        Returns
            int: Total number of chunks removed/skipped across audio and synthesis queues. Returns 0 if there is no current group to skip.

        """
        # Allow caller to specify target group id for compatibility
        if group_id is not None:
            self.current_group_id = group_id
            # Keep QueueManager in sync before performing skip logic
            self.queue_manager.current_group_id = group_id

        if not self.current_group_id:
            return 0

        # Skip from audio queue
        audio_skipped = await self.queue_manager.skip_current()

        # Also skip from synthesis queue
        synthesis_skipped = await self.queue_manager.clear_group_from_synthesis_queue(self.current_group_id)

        total_skipped = audio_skipped + synthesis_skipped

        if self.voice_client and self.voice_client.is_playing():
            self.voice_client.stop()

        self.stats_tracker.increment_messages_skipped()
        logger.info(f"Skipped {total_skipped} chunks from group {self.current_group_id}")
        return total_skipped

    async def clear_all(self) -> int:
        """
        Clear all pending synthesis and audio items and stop playback if active.
        
        Calls the queue manager to remove all items from both synthesis and audio queues. If a voice client is present and currently playing, it will be stopped.
        
        Returns:
            int: Total number of items removed from the queues.

        """
        total = await self.queue_manager.clear_all()

        if self.voice_client and self.voice_client.is_playing():
            self.voice_client.stop()

        logger.info(f"Cleared {total} items from queues")
        return total

    def get_status(self) -> dict[str, Any]:
        """
        Return a snapshot of the handler's current state aggregated from the connection, queue, and stats managers.
        
        Returns:
            dict[str, Any]: Status map containing:
                - connected (bool): whether a voice connection exists.
                - voice_connected (bool): same as `connected` (backwards-compatible).
                - voice_channel_name (str | None): human-readable channel name or None if not connected.
                - voice_channel_id (int | None): channel id or None if not connected.
                - playing (bool): whether audio is currently being played.
                - synthesis_queue_size (int): number of pending synthesis tasks.
                - audio_queue_size (int): number of pending audio chunks.
                - total_queue_size (int): sum of synthesis and audio queue sizes.
                - current_group (str | None): identifier for the currently active group, if any.
                - messages_played (int): total messages successfully played.
                - messages_skipped (int): total messages skipped.
                - errors (int): total errors recorded.
                - connection_state (str): low-level connection state string from the connection manager.
                - is_playing (bool): same as `playing` (backwards-compatible).
                - max_queue_size (int): configured maximum queue size (fixed value: 50).

        """
        connection_info = self.connection_manager.get_connection_info()
        queue_sizes = self.queue_manager.get_queue_sizes()
        stats = self.stats_tracker.get_stats()

        return {
            "connected": connection_info["connected"],
            "voice_connected": connection_info["connected"],
            "voice_channel_name": connection_info["channel_name"],
            "voice_channel_id": connection_info["channel_id"],
            "playing": self.is_playing,
            "synthesis_queue_size": queue_sizes["synthesis_queue_size"],
            "audio_queue_size": queue_sizes["audio_queue_size"],
            "total_queue_size": queue_sizes["total_queue_size"],
            "current_group": self.current_group_id,
            "messages_played": stats["messages_played"],
            "messages_skipped": stats["messages_skipped"],
            "errors": stats["errors"],
            "connection_state": connection_info["connection_state"],
            "is_playing": self.is_playing,
            "max_queue_size": 50,
        }

    @property
    def stats(self) -> dict[str, Any]:
        """
        Return a legacy-compatible stats dictionary mapping internal StatsTracker counters to legacy keys.
        
        Returns a dict with:
        - "messages_processed": sum of messages played and skipped.
        - "connection_errors": number of recorded errors.
        - "tts_messages_played": number of messages successfully synthesized/played.
        """
        s = self.stats_tracker.get_stats()
        return {
            "messages_processed": s.get("messages_played", 0) + s.get("messages_skipped", 0),
            "connection_errors": s.get("errors", 0),
            "tts_messages_played": s.get("messages_played", 0),
        }

    @stats.setter
    def stats(self, value: dict[str, Any]) -> None:
        """
        Set stats using a legacy-style dictionary by mapping legacy keys into the internal StatsTracker.
        
        Resets the internal stats counters, then reads legacy keys from `value` and updates the tracker:
        - `messages_played` or fallback `tts_messages_played` → internal `messages_played`
        - `messages_skipped` → internal `messages_skipped`
        - `errors` or fallback `connection_errors` → internal `errors`
        
        Unrecognized or non-integer values are ignored.
        """
        # Reset and map known keys into the tracker
        self.stats_tracker.reset_stats()
        # Prefer direct keys if present
        played = value.get("messages_played")
        skipped = value.get("messages_skipped")
        errors = value.get("errors")
        # Map legacy keys
        if played is None:
            played = value.get("tts_messages_played")
        if errors is None:
            errors = value.get("connection_errors")

        if isinstance(played, int):
            self.stats_tracker.stats["messages_played"] = played
        if isinstance(skipped, int):
            self.stats_tracker.stats["messages_skipped"] = skipped
        if isinstance(errors, int):
            self.stats_tracker.stats["errors"] = errors

    async def health_check(self) -> dict[str, Any]:
        """Perform comprehensive voice connection health check."""
        return await self.health_monitor.perform_health_check()

    async def cleanup(self) -> None:
        """
        Shut down workers and release voice-related resources.
        
        Performs an orderly, best-effort cleanup: signals synthesizer/player workers to stop, waits for task manager cleanup, clears both synthesis and audio queues, and instructs the connection manager to clean up the active voice client. This is an async operation that completes once all cleanup steps have finished.
        """
        # Stop workers gracefully before cleanup
        self.stop_workers()

        await self.task_manager.cleanup()

        result = await self.clear_all()
        _ = result  # Handle unused result

        await self.connection_manager.cleanup_voice_client()

        logger.info("Voice handler cleaned up")

    async def cleanup_voice_client(self) -> None:
        """
        Aggressively clean up the underlying voice client, stopping playback, disconnecting, and releasing associated resources.
        """
        await self.connection_manager.cleanup_voice_client()
