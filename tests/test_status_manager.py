"""Tests for StatusManager component - TDD Approach (Red-Green-Refactor)."""

import unittest
from typing import override
from unittest.mock import MagicMock, patch

import pytest

from discord_voice_bot.status_manager import BotStats, StatusManager, SystemHealth, VoiceStatus

from .base_test import BaseTestCase


class TestBotStats(BaseTestCase):
    """Test cases for BotStats data class."""

    def runTest(self) -> None:
        """Default test method for unittest compatibility."""

    def test_bot_stats_initialization(self) -> None:
        """Test BotStats initializes with correct default values."""
        stats = BotStats()

        self.assertEqual(stats.messages_processed, 0)
        self.assertEqual(stats.tts_messages_played, 0)
        self.assertEqual(stats.connection_errors, 0)
        self.assertIsNone(stats.uptime_start)
        self.assertEqual(stats.command_usage, {})
        self.assertEqual(stats.voice_connections, 0)
        self.assertEqual(stats.voice_disconnections, 0)
        self.assertEqual(stats.failed_tts_requests, 0)
        self.assertEqual(stats.average_response_time, 0.0)
        self.assertEqual(stats.peak_concurrent_users, 0)
        self.assertEqual(stats.total_guilds, 0)


class TestVoiceStatus(BaseTestCase):
    """Test cases for VoiceStatus data class."""

    def runTest(self) -> None:
        """Default test method for unittest compatibility."""

    def test_voice_status_initialization(self) -> None:
        """Test VoiceStatus initializes with correct default values."""
        voice_status = VoiceStatus()

        self.assertFalse(voice_status.connected)
        self.assertIsNone(voice_status.channel_name)
        self.assertIsNone(voice_status.channel_id)
        self.assertFalse(voice_status.is_playing)
        self.assertEqual(voice_status.queue_size, 0)
        self.assertIsNone(voice_status.current_group)
        self.assertIsNone(voice_status.connection_time)
        self.assertIsNone(voice_status.last_activity)


class TestSystemHealth(BaseTestCase):
    """Test cases for SystemHealth data class."""

    def runTest(self) -> None:
        """Default test method for unittest compatibility."""

    def test_system_health_initialization(self) -> None:
        """Test SystemHealth initializes with correct default values."""
        health = SystemHealth()

        self.assertTrue(health.tts_engine_healthy)
        self.assertTrue(health.voice_system_healthy)
        self.assertEqual(health.memory_usage, 0.0)
        self.assertEqual(health.cpu_usage, 0.0)
        self.assertIsNone(health.last_health_check)
        self.assertEqual(health.health_check_failures, 0)


class TestStatusManager(BaseTestCase):
    """Test cases for StatusManager - Main component."""

    def __init__(self, methodName: str = "runTest") -> None:
        """Initialize test case."""
        super().__init__(methodName)
        self.status_manager: StatusManager

    def runTest(self) -> None:
        """Default test method for unittest compatibility."""
        # This method is needed when no specific test method is provided

    @override
    def setUp(self) -> None:
        """Set up test fixtures."""
        super().setUp()
        self.status_manager = StatusManager()

    def test_initialization(self) -> None:
        """Test StatusManager initializes correctly."""
        assert isinstance(self.status_manager.stats, BotStats)
        assert isinstance(self.status_manager.voice_status, VoiceStatus)
        assert isinstance(self.status_manager.health, SystemHealth)
        assert self.status_manager.stats.uptime_start is not None
        assert self.status_manager.get_command_timings() == {}
        assert self.status_manager.get_response_times() == []
        assert self.status_manager.get_status_update_callbacks() == []

    def test_record_message_processed(self) -> None:
        """Test recording a processed message."""
        initial_count = self.status_manager.stats.messages_processed

        self.status_manager.record_message_processed()

        assert self.status_manager.stats.messages_processed == initial_count + 1

    def test_record_tts_played(self) -> None:
        """Test recording a TTS message played."""
        initial_count = self.status_manager.stats.tts_messages_played

        self.status_manager.record_tts_played()

        assert self.status_manager.stats.tts_messages_played == initial_count + 1

    def test_record_connection_error(self) -> None:
        """Test recording a connection error."""
        initial_count = self.status_manager.stats.connection_errors

        self.status_manager.record_connection_error()

        assert self.status_manager.stats.connection_errors == initial_count + 1

    def test_record_command_usage(self) -> None:
        """Test recording command usage."""
        command_name = "test_command"

        self.status_manager.record_command_usage(command_name)

        assert self.status_manager.stats.command_usage[command_name] == 1
        command_timings = self.status_manager.get_command_timings()
        assert command_name in command_timings
        assert len(command_timings[command_name]) == 1

    def test_record_voice_connection(self) -> None:
        """Test recording voice connection."""
        initial_connections = self.status_manager.stats.voice_connections

        self.status_manager.record_voice_connection()

        assert self.status_manager.stats.voice_connections == initial_connections + 1
        assert self.status_manager.voice_status.connected
        assert self.status_manager.voice_status.connection_time is not None
        assert self.status_manager.voice_status.last_activity is not None

    def test_record_voice_disconnection(self) -> None:
        """Test recording voice disconnection."""
        # First connect
        self.status_manager.record_voice_connection()
        initial_disconnections = self.status_manager.stats.voice_disconnections

        # Then disconnect
        self.status_manager.record_voice_disconnection()

        assert self.status_manager.stats.voice_disconnections == initial_disconnections + 1
        assert not self.status_manager.voice_status.connected
        assert self.status_manager.voice_status.connection_time is None

    def test_record_tts_failure(self) -> None:
        """Test recording TTS failure."""
        initial_failures = self.status_manager.stats.failed_tts_requests

        self.status_manager.record_tts_failure()

        assert self.status_manager.stats.failed_tts_requests == initial_failures + 1

    def test_record_response_time(self) -> None:
        """Test recording response time."""
        response_time = 0.5

        self.status_manager.record_response_time(response_time)

        response_times = self.status_manager.get_response_times()
        self.assertEqual(len(response_times), 1)
        self.assertEqual(response_times[0], response_time)
        self.assertAlmostEqual(self.status_manager.stats.average_response_time, response_time)

    def test_record_multiple_response_times(self) -> None:
        """Test recording multiple response times and average calculation."""
        response_times = [0.1, 0.2, 0.3]
        expected_average = sum(response_times) / len(response_times)

        for rt in response_times:
            self.status_manager.record_response_time(rt)

        response_times = self.status_manager.get_response_times()
        self.assertEqual(len(response_times), 3)
        self.assertAlmostEqual(self.status_manager.stats.average_response_time, expected_average)

    def test_response_time_limit(self) -> None:
        """Test that response times are limited to 100 entries."""
        # Add 101 response times
        for _ in range(101):
            self.status_manager.record_response_time(0.1)

        response_times = self.status_manager.get_response_times()
        self.assertEqual(len(response_times), 100)

    def test_update_voice_status_connected(self) -> None:
        """Test updating voice status connected state."""
        self.status_manager.update_voice_status(connected=True, channel_name="Test Channel")

        self.assertTrue(self.status_manager.voice_status.connected)
        self.assertEqual(self.status_manager.voice_status.channel_name, "Test Channel")
        self.assertIsNotNone(self.status_manager.voice_status.connection_time)

    def test_update_voice_status_playing(self) -> None:
        """Test updating voice status playing state."""
        self.status_manager.update_voice_status(is_playing=True, queue_size=5)

        self.assertTrue(self.status_manager.voice_status.is_playing)
        self.assertEqual(self.status_manager.voice_status.queue_size, 5)
        self.assertIsNotNone(self.status_manager.voice_status.last_activity)

    def test_update_system_health(self) -> None:
        """Test updating system health."""
        self.status_manager.update_system_health(tts_engine_healthy=False, voice_system_healthy=True, memory_usage=75.5, cpu_usage=45.2)

        self.assertFalse(self.status_manager.health.tts_engine_healthy)
        self.assertTrue(self.status_manager.health.voice_system_healthy)
        self.assertEqual(self.status_manager.health.memory_usage, 75.5)
        self.assertEqual(self.status_manager.health.cpu_usage, 45.2)
        self.assertIsNotNone(self.status_manager.health.last_health_check)
        self.assertEqual(self.status_manager.health.health_check_failures, 1)

    def test_update_guild_count(self) -> None:
        """Test updating guild count."""
        self.status_manager.update_guild_count(10)

        self.assertEqual(self.status_manager.stats.total_guilds, 10)
        self.assertEqual(self.status_manager.stats.peak_concurrent_users, 100)  # 10 * 10

    def test_update_guild_count_peak_update(self) -> None:
        """Test that peak concurrent users only increases."""
        self.status_manager.update_guild_count(5)  # Peak: 50
        self.status_manager.update_guild_count(3)  # Peak should remain 50

        self.assertEqual(self.status_manager.stats.peak_concurrent_users, 50)

    def test_get_overall_health_healthy(self) -> None:
        """Test getting overall health when system is healthy."""
        health = self.status_manager.get_overall_health()

        self.assertTrue(health)

    def test_get_overall_health_unhealthy(self) -> None:
        """Test getting overall health when system is unhealthy."""
        self.status_manager.update_system_health(tts_engine_healthy=False)

        health = self.status_manager.get_overall_health()

        self.assertFalse(health)

    def test_get_overall_health_with_connection_errors(self) -> None:
        """Test getting overall health with many connection errors."""
        for _ in range(15):  # More than 10 errors
            self.status_manager.record_connection_error()

        health = self.status_manager.get_overall_health()

        self.assertFalse(health)

    def test_get_uptime_seconds(self) -> None:
        """Test getting uptime in seconds."""
        uptime = self.status_manager.get_uptime_seconds()

        self.assertGreaterEqual(uptime, 0.0)

    def test_get_uptime_formatted(self) -> None:
        """Test getting formatted uptime string."""
        uptime_str = self.status_manager.get_uptime_formatted()

        # Should be in format HH:MM:SS
        self.assertRegex(uptime_str, r"^\d{2}:\d{2}:\d{2}$")

    def test_get_statistics(self) -> None:
        """Test getting comprehensive statistics."""
        # Set up some test data
        self.status_manager.record_message_processed()
        self.status_manager.record_command_usage("test")
        self.status_manager.update_voice_status(connected=True, channel_name="Test")

        stats = self.status_manager.get_statistics()

        # Check that all expected keys are present
        expected_keys = [
            "messages_processed",
            "tts_messages_played",
            "connection_errors",
            "uptime_seconds",
            "uptime_formatted",
            "command_usage",
            "voice_connections",
            "voice_disconnections",
            "failed_tts_requests",
            "average_response_time",
            "peak_concurrent_users",
            "total_guilds",
            "voice_status",
            "system_health",
        ]

        for key in expected_keys:
            self.assertIn(key, stats)

        # Check specific values
        self.assertEqual(stats["messages_processed"], 1)
        self.assertEqual(stats["command_usage"]["test"], 1)
        self.assertTrue(stats["voice_status"]["connected"])

    def test_get_status_summary(self) -> None:
        """Test getting status summary string."""
        summary = self.status_manager.get_status_summary()

        self.assertIn("Uptime:", summary)
        self.assertIn("Processed:", summary)
        self.assertIn("Played:", summary)
        self.assertIn("Errors:", summary)
        self.assertIn("Voice:", summary)

    def test_reset_statistics(self) -> None:
        """Test resetting all statistics."""
        # Add some data
        self.status_manager.record_message_processed()
        self.status_manager.record_command_usage("test")
        self.status_manager.record_response_time(0.5)

        # Reset
        self.status_manager.reset_statistics()

        # Check reset
        self.assertEqual(self.status_manager.stats.messages_processed, 0)
        self.assertEqual(self.status_manager.stats.command_usage, {})
        self.assertEqual(self.status_manager.get_command_timings(), {})
        self.assertEqual(self.status_manager.get_response_times(), [])
        self.assertIsNotNone(self.status_manager.stats.uptime_start)  # Should be reset

    def test_status_callbacks(self) -> None:
        """Test status update callbacks."""
        callback_called = False

        def test_callback() -> None:
            nonlocal callback_called
            callback_called = True

        # Add callback
        self.status_manager.add_status_callback(test_callback)

        # Notify callbacks
        self.status_manager.notify_status_callbacks_for_testing()

        self.assertTrue(callback_called)

    def test_remove_status_callback(self) -> None:
        """Test removing status update callback."""
        callback_called = False

        def test_callback() -> None:
            nonlocal callback_called
            callback_called = True

        # Add and remove callback
        self.status_manager.add_status_callback(test_callback)
        self.status_manager.remove_status_callback(test_callback)

        # Notify callbacks
        self.status_manager.notify_status_callbacks_for_testing()

        self.assertFalse(callback_called)

    @patch("asyncio.iscoroutinefunction", return_value=True)
    @patch("asyncio.create_task")
    @pytest.mark.asyncio
    async def test_async_status_callback(self, mock_create_task: MagicMock, mock_iscoroutine: MagicMock) -> None:
        """Test async status update callbacks."""
        from unittest.mock import AsyncMock

        # Create a mock task that behaves like a real task
        mock_task = AsyncMock()
        mock_create_task.return_value = mock_task

        async def async_callback() -> None:
            pass  # Simple callback that doesn't need to await anything

        # Add async callback
        self.status_manager.add_status_callback(async_callback)

        # Notify callbacks
        self.status_manager.notify_status_callbacks_for_testing()

        # Verify create_task was called once
        assert mock_create_task.call_count == 1
        # Verify the called function is async
        mock_iscoroutine.assert_called_once_with(async_callback)

    def test_callback_error_handling(self) -> None:
        """Test that callback errors are handled gracefully."""

        def error_callback() -> None:
            raise Exception("Test error")

        # Add error callback
        self.status_manager.add_status_callback(error_callback)

        # Should not raise exception
        try:
            self.status_manager.notify_status_callbacks_for_testing()
        except Exception:
            self.fail("Callback error should be handled gracefully")


if __name__ == "__main__":
    _ = unittest.main()
