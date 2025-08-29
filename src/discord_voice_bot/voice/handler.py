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
        return False

    def is_playing(self) -> bool:  # pragma: no cover - trivial
        return False

    def stop(self) -> None:  # pragma: no cover - trivial
        return None

    async def disconnect(self) -> None:  # pragma: no cover - trivial
        return None


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

    def __init__(self, bot_client: discord.Client, config: Config) -> None:
        """Initialize voice handler with manager components."""
        super().__init__()
        self.bot = bot_client
        self.config = config

        # Initialize manager components
        from ..config_manager import ConfigManagerImpl
        from ..tts_client import TTSClient

        self.connection_manager = VoiceConnectionManager(bot_client, ConfigManagerImpl(config))
        self.queue_manager = QueueManager()
        self.rate_limiter_manager = RateLimiterManager()
        self.stats_tracker = StatsTracker()
        self.task_manager = TaskManager()
        self.health_monitor = HealthMonitor(self.connection_manager, ConfigManagerImpl(config), TTSClient(config))

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
        """Set voice gateway in connection manager."""
        self.connection_manager.voice_gateway = value

    async def start(self, start_player: bool = True) -> None:
        """Start the voice handler tasks."""
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
        """Stop all worker tasks gracefully."""
        if self._synthesizer_worker:
            self._synthesizer_worker.stop()
        if self._player_worker:
            self._player_worker.stop()
        self.synthesizer = None
        logger.info("Sent stop signal to workers")

    def _get_voice_client(self) -> Any:
        vc = self.connection_manager.voice_client
        return vc if vc is not None else NullVoiceClient()

    def _set_voice_client(self, value: Any) -> None:
        self.connection_manager.voice_client = value

    voice_client = property(_get_voice_client, _set_voice_client)

    def is_connected(self) -> bool:
        """Check if the bot is connected to a voice channel."""
        return self.connection_manager.is_connected()

    async def connect_to_channel(self, channel_id: int) -> bool:
        """Connect to a voice channel using connection manager."""
        return await self.connection_manager.connect_to_channel(channel_id)

    async def handle_voice_server_update(self, payload: dict[str, Any]) -> None:
        """Handle VOICE_SERVER_UPDATE event with proper Discord API compliance."""
        await self.connection_manager.handle_voice_server_update(payload)

    async def handle_voice_state_update(self, payload: dict[str, Any]) -> None:
        """Handle VOICE_STATE_UPDATE event with proper Discord API compliance."""
        await self.connection_manager.handle_voice_state_update(payload)

    async def make_rate_limited_request(self, api_call: Any, *args: Any, **kwargs: Any) -> Any:
        """Make a rate-limited API request with circuit breaker pattern."""
        return await self.rate_limiter_manager.make_rate_limited_request(api_call, *args, **kwargs)

    async def add_to_queue(self, message_data: dict[str, Any]) -> None:
        """Add message to synthesis queue with deduplication."""
        await self.queue_manager.add_to_queue(message_data)

    async def skip_current(self, group_id: str | None = None) -> int:
        """Skip the current message group."""
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
        """Clear all queues."""
        total = await self.queue_manager.clear_all()

        if self.voice_client and self.voice_client.is_playing():
            self.voice_client.stop()

        logger.info(f"Cleared {total} items from queues")
        return total

    def get_status(self) -> dict[str, Any]:
        """Get current status information from all managers."""
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
        """Backward-compatible stats dict for legacy tests and integrations.

        Maps the new StatsTracker counters to the legacy keys expected by
        older tests (messages_processed, connection_errors,
        tts_messages_played).
        """
        s = self.stats_tracker.get_stats()
        return {
            "messages_processed": s.get("messages_played", 0) + s.get("messages_skipped", 0),
            "connection_errors": s.get("errors", 0),
            "tts_messages_played": s.get("messages_played", 0),
        }

    @stats.setter
    def stats(self, value: dict[str, Any]) -> None:
        """Allow legacy tests to assign a stats dict.

        The assignment updates the internal StatsTracker counters by mapping
        legacy keys to current ones. Unrecognized keys are ignored.
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
        """Clean up resources."""
        # Stop workers gracefully before cleanup
        self.stop_workers()

        await self.task_manager.cleanup()

        result = await self.clear_all()
        _ = result  # Handle unused result

        await self.connection_manager.cleanup_voice_client()

        logger.info("Voice handler cleaned up")

    async def cleanup_voice_client(self) -> None:
        """Aggressively clean up voice client state."""
        await self.connection_manager.cleanup_voice_client()
