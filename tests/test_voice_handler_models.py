"""Tests for VoiceHandler models and data structures."""

import pytest

from tests.test_voice_handler_fixtures import AudioItem


class TestAudioItem:
    """Test AudioItem dataclass."""

    def test_audio_item_creation(self) -> None:
        """Test creating an AudioItem with required fields."""
        from datetime import datetime

        created_item = AudioItem(
            text="Hello World",
            user_id=123456789,
            username="test_user",
            group_id="group_1",
            priority=1,
            chunk_index=0,
            audio_size=1024,
        )

        assert created_item.text == "Hello World"
        assert created_item.user_id == 123456789
        assert created_item.username == "test_user"
        assert created_item.group_id == "group_1"
        assert created_item.priority == 1
        assert created_item.chunk_index == 0
        assert created_item.audio_size == 1024

    def test_audio_item_optional_fields(self) -> None:
        """Test that optional fields are properly initialized."""
        item = AudioItem(
            text="test",
            user_id=1,
            username="user",
            group_id="group",
            priority=0,
            chunk_index=0,
            audio_size=0
        )

        assert item.created_at is None
        assert item.processed_at is None

    def test_audio_item_equality(self) -> None:
        """Test AudioItem equality."""

        item1 = AudioItem(
            text="test",
            user_id=1,
            username="user",
            group_id="group",
            priority=0,
            chunk_index=0,
            audio_size=100
        )

        item2 = AudioItem(
            text="test",
            user_id=1,
            username="user",
            group_id="group",
            priority=0,
            chunk_index=0,
            audio_size=100
        )

        # AudioItem instances should be equal if all fields match
        assert item1 == item2

    def test_audio_item_hashable(self) -> None:
        """Test that AudioItem can be used in sets and as dict keys."""
        item = AudioItem(
            text="test",
            user_id=1,
            username="user",
            group_id="group",
            priority=0,
            chunk_index=0,
            audio_size=0
        )

        # Should be hashable for use in queues and sets
        qset = {item}
        assert len(qset) == 1

        # Should be usable as dict key
        d = {item: "value"}
        assert d[item] == "value"