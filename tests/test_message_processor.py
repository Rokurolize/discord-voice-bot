"""Unit tests for message_processor module."""

from unittest.mock import MagicMock

import pytest

from discord_voice_bot.config import config
from discord_voice_bot.message_processor import MessageProcessor


@pytest.fixture
def processor() -> MessageProcessor:
    """Create a MessageProcessor instance for testing."""
    from unittest.mock import MagicMock

    from discord_voice_bot.protocols import ConfigManager

    mock_config: MagicMock = MagicMock(spec=ConfigManager)
    mock_config.get_target_voice_channel_id.return_value = 123456789
    mock_config.get_rate_limit_messages.return_value = 100
    mock_config.get_rate_limit_period.return_value = 60
    mock_config.get_enable_self_message_processing.return_value = False
    return MessageProcessor(mock_config)


@pytest.fixture
def mock_message() -> MagicMock:
    """Create a mock Discord message."""
    msg = MagicMock()
    msg.author = MagicMock()
    msg.author.id = 123456789
    msg.author.name = "TestUser"
    msg.author.display_name = "TestUser"
    msg.author.bot = False
    msg.content = "Test message"
    msg.channel = MagicMock()
    msg.guild = MagicMock()  # Treat as a server message
    msg.channel.id = config.target_voice_channel_id  # Use actual config
    msg.id = 987654321
    msg.type = MagicMock()
    msg.type.name = "default"
    return msg


class TestMessageFiltering:
    """Test message filtering logic."""

    @pytest.mark.asyncio
    async def test_filter_bot_message(self, processor: MessageProcessor, mock_message: MagicMock) -> None:
        """Bot messages should be filtered out."""
        mock_message.author.bot = True
        result = await processor.should_process_message(mock_message)
        assert result is False

    @pytest.mark.asyncio
    async def test_filter_command_message(self, processor: MessageProcessor, mock_message: MagicMock) -> None:
        """Command messages starting with ! should be filtered."""
        mock_message.content = "!tts test"
        result = await processor.should_process_message(mock_message)
        assert result is False

    @pytest.mark.asyncio
    async def test_filter_empty_message(self, processor: MessageProcessor, mock_message: MagicMock) -> None:
        """Empty messages should be filtered."""
        mock_message.content = ""
        result = await processor.should_process_message(mock_message)
        assert result is False

    @pytest.mark.asyncio
    async def test_filter_whitespace_message(self, processor: MessageProcessor, mock_message: MagicMock) -> None:
        """Whitespace-only messages should be filtered."""
        mock_message.content = "   \n\t  "
        result = await processor.should_process_message(mock_message)
        assert result is False

    @pytest.mark.asyncio
    async def test_normal_message_not_filtered(self, processor: MessageProcessor, mock_message: MagicMock) -> None:
        """Normal messages should not be filtered."""
        mock_message.content = "Hello world"
        result = await processor.should_process_message(mock_message)
        assert result is True

    @pytest.mark.asyncio
    async def test_messages_from_any_channel_are_allowed(self, processor: MessageProcessor, mock_message: MagicMock) -> None:
        """Messages from any server text channel should be allowed."""
        mock_message.channel.id = 999999999
        result = await processor.should_process_message(mock_message)
        assert result is True

    @pytest.mark.asyncio
    async def test_system_message_filtered(self, processor: MessageProcessor, mock_message: MagicMock) -> None:
        """System messages should be filtered."""
        mock_message.type.name = "pins_add"
        result = await processor.should_process_message(mock_message)
        assert result is False


class TestTextProcessing:
    """Test text processing and conversion."""

    def test_process_message_content(self, processor: MessageProcessor) -> None:
        """Test basic message content processing."""
        result = processor.process_message_content("Hello world!", "TestUser")
        assert "Hello" in result
        assert "world" in result

    def test_emoji_handling(self, processor: MessageProcessor) -> None:
        """Test emoji processing."""
        # Emojis are typically converted or kept
        result = processor.process_message_content("Hello :)", "TestUser")
        assert result  # Should not be empty

    def test_url_handling(self, processor: MessageProcessor) -> None:
        """URLs should be processed."""
        result = processor.process_message_content("Check https://example.com", "TestUser")
        # URLs are converted to "link" in the actual implementation
        assert "link" in result or "https://" in result


class TestMessageChunking:
    """Test message chunking for long messages."""

    def test_short_message_not_chunked(self, processor: MessageProcessor) -> None:
        """Short messages should not be chunked."""
        text = "This is a short message."
        chunks = processor.chunk_message(text)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_long_message_chunked(self, processor: MessageProcessor) -> None:
        """Long messages should be chunked."""
        # Create a message longer than default max length
        text = "This is a long sentence. " * 100  # Very long
        chunks = processor.chunk_message(text)
        assert len(chunks) > 1
        # Verify no data loss - reconstruct original with spaces between chunks
        reconstructed = " ".join(chunks)
        # The chunked version should be similar in length and contain the same content
        assert len(reconstructed) > 100  # Should be substantial
        assert "This is a long sentence" in reconstructed  # Should contain original content

    def test_chunk_at_sentence_boundary(self, processor: MessageProcessor) -> None:
        """Chunks should split at sentence boundaries when possible."""
        text = "Sentence 1. Sentence 2. Sentence 3. " * 50
        chunks = processor.chunk_message(text)
        # Check that chunks end with sentence markers where possible
        for chunk in chunks[:-1]:  # All but last
            # Should end with a sentence marker if possible
            if len(chunk) < 500:  # If not at max length
                assert chunk[-1] in ".!?\n" or len(chunk) == 500


class TestAsyncProcessing:
    """Test async message processing."""

    @pytest.mark.asyncio
    async def test_process_message_success(self, processor: MessageProcessor, mock_message: MagicMock) -> None:
        """Successful message processing should return processed data."""
        mock_message.content = "Hello world"
        result = await processor.process_message(mock_message)

        assert result is not None
        assert "user_id" in result
        assert "username" in result
        assert "text" in result
        assert "chunks" in result
        assert result["user_id"] == mock_message.author.id

    @pytest.mark.asyncio
    async def test_process_message_filtered(self, processor: MessageProcessor, mock_message: MagicMock) -> None:
        """Filtered messages should return None."""
        mock_message.author.bot = True
        result = await processor.process_message(mock_message)
        assert result is None

    @pytest.mark.asyncio
    async def test_process_message_with_chunking(self, processor: MessageProcessor, mock_message: MagicMock) -> None:
        """Long messages should be properly chunked."""
        mock_message.content = "This is a long sentence. " * 100
        result = await processor.process_message(mock_message)

        assert result is not None
        assert len(result["chunks"]) > 1
        assert all(chunk for chunk in result["chunks"])  # No empty chunks

    @pytest.mark.asyncio
    async def test_create_tts_message(self, processor: MessageProcessor, mock_message: MagicMock) -> None:
        """Test create_tts_message method."""
        mock_message.content = "Test message"
        result = await processor.create_tts_message(mock_message)
        assert result is not None
        assert isinstance(result, str)
