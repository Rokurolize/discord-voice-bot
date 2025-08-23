"""Status management and statistics tracking for Discord Voice TTS Bot."""

import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import discord
from loguru import logger


@dataclass
class BotStats:
    """Bot statistics container."""

    messages_processed: int = 0
    tts_messages_played: int = 0
    connection_errors: int = 0
    uptime_start: float | None = None
    command_usage: dict[str, int] = field(default_factory=dict)  # type: ignore[misc]
    voice_connections: int = 0
    voice_disconnections: int = 0
    failed_tts_requests: int = 0
    average_response_time: float = 0.0
    peak_concurrent_users: int = 0
    total_guilds: int = 0


@dataclass
class VoiceStatus:
    """Voice connection status."""

    connected: bool = False
    channel_name: str | None = None
    channel_id: int | None = None
    is_playing: bool = False
    queue_size: int = 0
    current_group: str | None = None
    connection_time: float | None = None
    last_activity: float | None = None


@dataclass
class SystemHealth:
    """System health metrics."""

    tts_engine_healthy: bool = True
    voice_system_healthy: bool = True
    memory_usage: float = 0.0
    cpu_usage: float = 0.0
    last_health_check: float | None = None
    health_check_failures: int = 0


class StatusManager:
    """Manages bot statistics and status tracking."""

    def __init__(self) -> None:
        """Initialize status manager."""
        super().__init__()
        self.stats = BotStats()
        self.voice_status = VoiceStatus()
        self.health = SystemHealth()
        self._command_timings: dict[str, list[float]] = {}
        self._response_times: list[float] = []
        self._status_update_callbacks: list[Callable[[], Any]] = []

        # Set initial uptime
        self.stats.uptime_start = time.time()

        logger.info("Status manager initialized")

    def record_message_processed(self) -> None:
        """Record a message being processed."""
        self.stats.messages_processed += 1

    def record_tts_played(self) -> None:
        """Record a TTS message being played."""
        self.stats.tts_messages_played += 1

    def record_connection_error(self) -> None:
        """Record a connection error."""
        self.stats.connection_errors += 1

    def record_command_usage(self, command_name: str) -> None:
        """Record command usage.

        Args:
            command_name: Name of the command used

        """
        self.stats.command_usage[command_name] = self.stats.command_usage.get(command_name, 0) + 1

        # Track timing for performance monitoring
        if command_name not in self._command_timings:
            self._command_timings[command_name] = []
        self._command_timings[command_name].append(time.time())

        logger.debug(f"Recorded command usage: {command_name}")

    def record_voice_connection(self) -> None:
        """Record a voice connection."""
        self.stats.voice_connections += 1
        self.voice_status.connected = True
        self.voice_status.connection_time = time.time()
        self.voice_status.last_activity = time.time()

    def record_voice_disconnection(self) -> None:
        """Record a voice disconnection."""
        self.stats.voice_disconnections += 1
        self.voice_status.connected = False
        self.voice_status.connection_time = None

    def record_tts_failure(self) -> None:
        """Record a TTS request failure."""
        self.stats.failed_tts_requests += 1

    def record_response_time(self, response_time: float) -> None:
        """Record response time for performance monitoring.

        Args:
            response_time: Response time in seconds

        """
        self._response_times.append(response_time)

        # Keep only last 100 response times
        if len(self._response_times) > 100:
            _ = self._response_times.pop(0)

        # Update average response time
        if self._response_times:
            self.stats.average_response_time = sum(self._response_times) / len(self._response_times)

    def update_voice_status(
        self,
        connected: bool | None = None,
        channel_name: str | None = None,
        channel_id: int | None = None,
        is_playing: bool | None = None,
        queue_size: int | None = None,
        current_group: str | None = None,
    ) -> None:
        """Update voice connection status.

        Args:
            connected: Voice connection status
            channel_name: Voice channel name
            channel_id: Voice channel ID
            is_playing: Whether audio is playing
            queue_size: Size of audio queue
            current_group: Current message group being played

        """
        if connected is not None:
            self.voice_status.connected = connected
            if connected:
                self.voice_status.connection_time = time.time()

        if channel_name is not None:
            self.voice_status.channel_name = channel_name

        if channel_id is not None:
            self.voice_status.channel_id = channel_id

        if is_playing is not None:
            self.voice_status.is_playing = is_playing
            if is_playing:
                self.voice_status.last_activity = time.time()

        if queue_size is not None:
            self.voice_status.queue_size = queue_size

        if current_group is not None:
            self.voice_status.current_group = current_group

    def update_system_health(
        self,
        tts_engine_healthy: bool | None = None,
        voice_system_healthy: bool | None = None,
        memory_usage: float | None = None,
        cpu_usage: float | None = None,
    ) -> None:
        """Update system health metrics.

        Args:
            tts_engine_healthy: TTS engine health status
            voice_system_healthy: Voice system health status
            memory_usage: Memory usage percentage
            cpu_usage: CPU usage percentage

        """
        if tts_engine_healthy is not None:
            self.health.tts_engine_healthy = tts_engine_healthy

        if voice_system_healthy is not None:
            self.health.voice_system_healthy = voice_system_healthy

        if memory_usage is not None:
            self.health.memory_usage = memory_usage

        if cpu_usage is not None:
            self.health.cpu_usage = cpu_usage

        self.health.last_health_check = time.time()

        # Count health check failures
        if not (tts_engine_healthy and voice_system_healthy):
            self.health.health_check_failures += 1

    def update_guild_count(self, count: int) -> None:
        """Update total guild count.

        Args:
            count: Number of guilds the bot is in

        """
        self.stats.total_guilds = count

        # Update peak concurrent users (rough estimate)
        estimated_users = count * 10  # Assume 10 users per guild on average
        if estimated_users > self.stats.peak_concurrent_users:
            self.stats.peak_concurrent_users = estimated_users

    async def update_presence(self, bot: discord.Client) -> None:
        """Update bot presence with current status.

        Args:
            bot: Discord bot client

        """
        try:
            # Create presence based on current status
            activity_type = discord.ActivityType.listening
            activity_text = "声チャットのメッセージ 📢"

            # Modify activity based on status
            if not self.voice_status.connected:
                activity_text = "Disconnected - Use !tts reconnect"
                activity_type = discord.ActivityType.playing
            elif self.voice_status.is_playing:
                activity_text = f"Playing TTS ({self.voice_status.queue_size} queued)"
            elif self.voice_status.queue_size > 0:
                activity_text = f"{self.voice_status.queue_size} messages queued"

            activity = discord.Activity(type=activity_type, name=activity_text)
            await bot.change_presence(status=discord.Status.online if self.get_overall_health() else discord.Status.idle, activity=activity)

        except Exception as e:
            logger.error(f"Error updating bot presence: {e}")

    def get_overall_health(self) -> bool:
        """Get overall system health status.

        Returns:
            True if system is healthy, False otherwise

        """
        return (
            self.health.tts_engine_healthy and self.health.voice_system_healthy and self.stats.connection_errors < 10  # Allow some connection errors
        )

    def get_uptime_seconds(self) -> float:
        """Get bot uptime in seconds.

        Returns:
            Uptime in seconds

        """
        if self.stats.uptime_start is None:
            return 0.0
        return time.time() - self.stats.uptime_start

    def get_uptime_formatted(self) -> str:
        """Get formatted uptime string.

        Returns:
            Formatted uptime string (HH:MM:SS)

        """
        uptime = int(self.get_uptime_seconds())
        hours, remainder = divmod(uptime, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def get_statistics(self) -> dict[str, Any]:
        """Get comprehensive bot statistics.

        Returns:
            Dictionary with all statistics

        """
        return {
            "messages_processed": self.stats.messages_processed,
            "tts_messages_played": self.stats.tts_messages_played,
            "connection_errors": self.stats.connection_errors,
            "uptime_seconds": self.get_uptime_seconds(),
            "uptime_formatted": self.get_uptime_formatted(),
            "command_usage": dict(self.stats.command_usage),
            "voice_connections": self.stats.voice_connections,
            "voice_disconnections": self.stats.voice_disconnections,
            "failed_tts_requests": self.stats.failed_tts_requests,
            "average_response_time": round(self.stats.average_response_time * 1000, 2),  # Convert to ms
            "peak_concurrent_users": self.stats.peak_concurrent_users,
            "total_guilds": self.stats.total_guilds,
            "voice_status": {
                "connected": self.voice_status.connected,
                "channel_name": self.voice_status.channel_name,
                "channel_id": self.voice_status.channel_id,
                "is_playing": self.voice_status.is_playing,
                "queue_size": self.voice_status.queue_size,
                "current_group": self.voice_status.current_group,
            },
            "system_health": {
                "tts_engine_healthy": self.health.tts_engine_healthy,
                "voice_system_healthy": self.health.voice_system_healthy,
                "memory_usage": round(self.health.memory_usage, 1),
                "cpu_usage": round(self.health.cpu_usage, 1),
                "health_check_failures": self.health.health_check_failures,
                "overall_healthy": self.get_overall_health(),
            },
        }

    def get_status_summary(self) -> str:
        """Get a brief status summary.

        Returns:
            Status summary string

        """
        uptime = self.get_uptime_formatted()
        health_status = "✅ Healthy" if self.get_overall_health() else "⚠️ Issues Detected"

        summary = f"Uptime: {uptime} | Processed: {self.stats.messages_processed} | "
        summary += f"Played: {self.stats.tts_messages_played} | Errors: {self.stats.connection_errors} | "
        summary += f"Voice: {'✅' if self.voice_status.connected else '❌'} | {health_status}"

        return summary

    def reset_statistics(self) -> None:
        """Reset all statistics (useful for debugging)."""
        self.stats = BotStats()
        self._command_timings.clear()
        self._response_times.clear()
        self.stats.uptime_start = time.time()
        logger.info("Reset all statistics")

    def add_status_callback(self, callback: Callable[[], Any]) -> None:
        """Add a callback for status updates.

        Args:
            callback: Function to call when status updates

        """
        self._status_update_callbacks.append(callback)

    def remove_status_callback(self, callback: Callable[[], Any]) -> None:
        """Remove a status update callback.

        Args:
            callback: Callback function to remove

        """
        if callback in self._status_update_callbacks:
            self._status_update_callbacks.remove(callback)

    def _notify_status_callbacks(self) -> None:
        """Notify all status update callbacks."""
        for callback in self._status_update_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    _ = asyncio.create_task(callback())
                else:
                    callback()
            except Exception as e:
                logger.error(f"Error in status callback: {e}")

    # Test access methods
    def get_command_timings(self) -> dict[str, list[float]]:
        """Get command timings for testing.

        Returns:
            Dictionary of command timings

        """
        return self._command_timings.copy()

    def get_response_times(self) -> list[float]:
        """Get response times for testing.

        Returns:
            List of response times

        """
        return self._response_times.copy()

    def get_status_update_callbacks(self) -> list[Callable[[], Any]]:
        """Get status update callbacks for testing.

        Returns:
            List of status update callbacks

        """
        return self._status_update_callbacks.copy()

    def notify_status_callbacks_for_testing(self) -> None:
        """Notify all status update callbacks for testing purposes.

        This is a public method to allow tests to trigger callback notifications
        without accessing private methods.
        """
        self._notify_status_callbacks()
