"""Unit tests for message_processor module."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

from src.message_processor import MessageProcessor


@pytest.fixture
def processor():
    """Create a MessageProcessor instance for testing."""
    return MessageProcessor()


@pytest.fixture
def mock_message():
    """Create a mock Discord message."""
    msg = MagicMock()
    msg.author = MagicMock()
    msg.author.id = 123456789
    msg.author.name = "TestUser"
    msg.author.bot = False
    msg.content = "Test message"
    msg.channel = MagicMock()
    msg.channel.id = 987654321
    return msg


class TestMessageFiltering:
    """Test message filtering logic."""

    def test_filter_bot_message(self, processor, mock_message):
        """Bot messages should be filtered out."""
        mock_message.author.bot = True
        assert processor.should_filter_message(mock_message) is True

    def test_filter_command_message(self, processor, mock_message):
        """Command messages starting with ! should be filtered."""
        mock_message.content = "!tts test"
        assert processor.should_filter_message(mock_message) is True

    def test_filter_empty_message(self, processor, mock_message):
        """Empty messages should be filtered."""
        mock_message.content = ""
        assert processor.should_filter_message(mock_message) is True

    def test_filter_whitespace_message(self, processor, mock_message):
        """Whitespace-only messages should be filtered."""
        mock_message.content = "   \n\t  "
        assert processor.should_filter_message(mock_message) is True

    def test_normal_message_not_filtered(self, processor, mock_message):
        """Normal messages should not be filtered."""
        mock_message.content = "Hello world"
        assert processor.should_filter_message(mock_message) is False


class TestRateLimiting:
    """Test rate limiting functionality."""

    def test_rate_limit_not_exceeded(self, processor, mock_message):
        """Messages within rate limit should not be limited."""
        for _ in range(5):
            assert processor.is_rate_limited(mock_message.author.id) is False
            processor._update_rate_limit(mock_message.author.id)

    def test_rate_limit_exceeded(self, processor, mock_message):
        """Messages exceeding rate limit should be limited."""
        # Send max messages
        for _ in range(processor.rate_limit_messages):
            processor._update_rate_limit(mock_message.author.id)

        # Next message should be rate limited
        assert processor.is_rate_limited(mock_message.author.id) is True

    def test_rate_limit_reset_after_window(self, processor, mock_message):
        """Rate limit should reset after time window."""
        user_id = mock_message.author.id

        # Fill up rate limit
        for _ in range(processor.rate_limit_messages):
            processor._update_rate_limit(user_id)

        # Should be rate limited
        assert processor.is_rate_limited(user_id) is True

        # Simulate time passing
        processor.user_message_times[user_id] = [
            datetime.now() - timedelta(seconds=processor.rate_limit_window + 1) for _ in processor.user_message_times[user_id]
        ]

        # Should no longer be rate limited
        assert processor.is_rate_limited(user_id) is False


class TestTextProcessing:
    """Test text processing and conversion."""

    def test_convert_emoji_to_text(self, processor):
        """Emojis should be converted to text descriptions."""
        text = "Hello 😀 world 👍"
        result = processor.convert_emoji_to_text(text)
        assert "笑顔" in result
        assert "いいね" in result

    def test_convert_url_to_text(self, processor):
        """URLs should be converted to 'URL省略'."""
        text = "Check this https://example.com out"
        result = processor.convert_url_to_text(text)
        assert result == "Check this URL省略 out"

    def test_convert_mention_to_text(self, processor):
        """Discord mentions should be converted to readable text."""
        text = "Hey <@123456789> check this"
        result = processor.convert_mention_to_text(text)
        assert result == "Hey メンション check this"

    def test_convert_channel_to_text(self, processor):
        """Channel mentions should be converted to readable text."""
        text = "Go to <#987654321> channel"
        result = processor.convert_channel_to_text(text)
        assert result == "Go to チャンネル channel"

    def test_normalize_text_full_pipeline(self, processor):
        """Test full text normalization pipeline."""
        text = "Hello @user 😀 check https://example.com in <#channel>!"
        result = processor.normalize_text(text)
        # Should process all conversions
        assert "URL省略" in result
        assert "笑顔" in result
        assert "チャンネル" in result


class TestMessageChunking:
    """Test message chunking for long messages."""

    def test_short_message_not_chunked(self, processor):
        """Short messages should not be chunked."""
        text = "This is a short message."
        chunks = processor.chunk_message(text)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_long_message_chunked_at_sentence(self, processor):
        """Long messages should be chunked at sentence boundaries."""
        # Create a long message with clear sentence boundaries
        text = "これは文です。" * 50  # 350 chars (7 chars * 50)
        chunks = processor.chunk_message(text, max_length=100)

        # Should be split into chunks
        assert len(chunks) > 1

        # Each chunk should end at a sentence boundary
        for chunk in chunks[:-1]:  # All but last chunk
            assert chunk.endswith("。")

        # No chunk should exceed max length
        for chunk in chunks:
            assert len(chunk) <= 100

    def test_chunk_message_preserves_content(self, processor):
        """Chunking should preserve all content."""
        text = "文章1。文章2。文章3。文章4。文章5。"
        chunks = processor.chunk_message(text, max_length=15)

        # Rejoin chunks should equal original
        rejoined = "".join(chunks)
        assert rejoined == text

    def test_chunk_message_with_no_sentence_boundary(self, processor):
        """Message with no sentence boundary should be force-split."""
        text = "a" * 600  # No sentence boundaries
        chunks = processor.chunk_message(text, max_length=500)

        assert len(chunks) == 2
        assert len(chunks[0]) == 500
        assert len(chunks[1]) == 100


class TestAsyncProcessing:
    """Test async message processing."""

    @pytest.mark.asyncio
    async def test_process_message_success(self, processor, mock_message):
        """Successful message processing should return processed text."""
        mock_message.content = "Hello world"
        result = await processor.process_message(mock_message)

        assert result is not None
        assert "user_id" in result
        assert "username" in result
        assert "text" in result
        assert "chunks" in result
        assert result["text"] == "Hello world"

    @pytest.mark.asyncio
    async def test_process_message_filtered(self, processor, mock_message):
        """Filtered messages should return None."""
        mock_message.author.bot = True
        result = await processor.process_message(mock_message)
        assert result is None

    @pytest.mark.asyncio
    async def test_process_message_rate_limited(self, processor, mock_message):
        """Rate limited messages should return None."""
        # Fill up rate limit
        for _ in range(processor.rate_limit_messages):
            processor._update_rate_limit(mock_message.author.id)

        result = await processor.process_message(mock_message)
        assert result is None

    @pytest.mark.asyncio
    async def test_process_message_with_chunking(self, processor, mock_message):
        """Long messages should be properly chunked."""
        mock_message.content = "これは長い文章です。" * 100
        result = await processor.process_message(mock_message)

        assert result is not None
        assert len(result["chunks"]) > 1
        assert all(chunk for chunk in result["chunks"])  # No empty chunks
