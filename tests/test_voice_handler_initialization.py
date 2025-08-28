"""Tests for VoiceHandler initialization."""


class TestVoiceHandlerInitialization:
    """Test VoiceHandler initialization."""

    def test_old_voice_handler_initialization(self, voice_handler_old) -> None:
        """Test that old VoiceHandler initializes with required components."""
        assert voice_handler_old is not None

        # Check that required components are initialized
        assert hasattr(voice_handler_old, "rate_limiter")
        assert hasattr(voice_handler_old, "voice_client")
        assert hasattr(voice_handler_old, "stats")

        # Test that stats dictionary is initialized
        assert isinstance(voice_handler_old.stats, dict)
        assert voice_handler_old.stats.get("connection_errors", 0) == 0

    def test_new_voice_handler_initialization(self, voice_handler_new) -> None:
        """Test that new VoiceHandler initializes with required components."""
        assert voice_handler_new is not None

        # Check that manager components are properly initialized
        assert hasattr(voice_handler_new, "connection_manager")
        assert hasattr(voice_handler_new, "queue_manager")
        assert hasattr(voice_handler_new, "rate_limiter_manager")
        assert hasattr(voice_handler_new, "stats_tracker")
        assert hasattr(voice_handler_new, "task_manager")
        assert hasattr(voice_handler_new, "health_monitor")

        # Verify queue attributes are properly set
        assert hasattr(voice_handler_new, "synthesis_queue")
        assert hasattr(voice_handler_new, "audio_queue")

    def test_voice_handler_component_managers(self, voice_handler_new) -> None:
        """Test that new VoiceHandler has all required manager components."""
        # Check that all manager instances are created
        assert voice_handler_new.connection_manager is not None
        assert voice_handler_new.queue_manager is not None
        assert voice_handler_new.rate_limiter_manager is not None
        assert voice_handler_new.stats_tracker is not None
        assert voice_handler_new.task_manager is not None
        assert voice_handler_new.health_monitor is not None

    def test_voice_handler_stats_initialization(self, voice_handler_new) -> None:
        """Test that VoiceHandler stats are properly initialized."""
        # Test that the stats object exists and is accessible
        assert voice_handler_new.stats is not None
        assert isinstance(voice_handler_new.stats, dict)

        # Test basic stats structure
        assert "messages_processed" in voice_handler_new.stats
        assert "connection_errors" in voice_handler_new.stats
        assert "tts_messages_played" in voice_handler_new.stats

    def test_voice_handler_cleanup_method_exists(self, voice_handler_new) -> None:
        """Test that VoiceHandler has cleanup method."""
        assert hasattr(voice_handler_new, "cleanup")
        assert callable(voice_handler_new.cleanup)

    def test_rate_limiter_initialization(self, voice_handler_new) -> None:
        """Test that rate limiter is properly initialized."""
        assert hasattr(voice_handler_new, "rate_limiter")
        assert voice_handler_new.rate_limiter is not None

    def test_connection_state_initialization(self, voice_handler_new) -> None:
        """Test that connection state is properly initialized."""
        assert hasattr(voice_handler_new, "connection_state")
        assert voice_handler_new.connection_state is not None
