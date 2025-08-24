"""Message processing and filtering for Discord Voice TTS Bot."""

import re
from collections import defaultdict, deque
from datetime import datetime, timedelta
from functools import lru_cache
from typing import Any

from loguru import logger

from .protocols import ConfigManager


class RateLimiter:
    """Rate limiter to prevent message spam."""

    def __init__(self, max_messages: int, period_seconds: int) -> None:
        """Initialize rate limiter.

        Args:
            max_messages: Maximum messages allowed in period
            period_seconds: Time period in seconds

        """
        super().__init__()
        self.max_messages = max_messages
        # Ensure period_seconds is a valid integer for timedelta
        # This handles test mocks while maintaining type safety
        try:
            self.period = timedelta(seconds=int(period_seconds))
        except (TypeError, ValueError):
            self.period = timedelta(seconds=60)
        self.message_times: dict[int, deque[datetime]] = defaultdict(lambda: deque[datetime]())  # user_id -> timestamps

    def is_allowed(self, user_id: int) -> bool:
        """Check if user is allowed to send message based on rate limit."""
        now = datetime.now()
        user_times = self.message_times[user_id]

        # Remove old timestamps outside the time window
        while user_times and now - user_times[0] > self.period:
            _ = user_times.popleft()

        # Check if under limit
        if len(user_times) < self.max_messages:
            user_times.append(now)
            return True

        return False

    def reset_user(self, user_id: int) -> None:
        """Reset rate limit for specific user."""
        self.message_times[user_id].clear()

    def get_remaining_time(self, user_id: int) -> int | None:
        """Get remaining time in seconds until user can send another message."""
        user_times = self.message_times[user_id]
        if not user_times or len(user_times) < self.max_messages:
            return None

        oldest_time = user_times[0]
        remaining = self.period - (datetime.now() - oldest_time)
        return max(0, int(remaining.total_seconds()))


class MessageProcessor:
    """Process and filter messages for TTS synthesis."""

    def __init__(self, config_manager: ConfigManager) -> None:
        """Initialize message processor."""
        super().__init__()
        self._config_manager = config_manager
        self.rate_limiter = RateLimiter(self._config_manager.get_rate_limit_messages(), self._config_manager.get_rate_limit_period())
        self.blocked_users: set[int] = set()
        self.ignored_prefixes = ["!", "/", ".", ">", "<"]  # Common bot/command prefixes

        # Emoji and mention patterns
        self.emoji_pattern = re.compile(r"<:[a-zA-Z0-9_]+:[0-9]+>")
        self.animated_emoji_pattern = re.compile(r"<a:[a-zA-Z0-9_]+:[0-9]+>")
        self.mention_pattern = re.compile(r"<@!?[0-9]+>")
        self.channel_mention_pattern = re.compile(r"<#[0-9]+>")
        self.role_mention_pattern = re.compile(r"<@&[0-9]+>")
        self.url_pattern = re.compile(r"https?://[^\s]+")

        # Japanese text patterns for better processing
        self.japanese_emoticon_pattern = re.compile(r"[（）()（）\(\)]")

        rate_limit_messages = self._config_manager.get_rate_limit_messages()
        # Handle mock objects in tests while maintaining type safety
        if isinstance(rate_limit_messages, int):  # type: ignore[reportUnnecessaryIsInstance]
            if rate_limit_messages > 0 and rate_limit_messages < 1000:
                rate_limit_period = self._config_manager.get_rate_limit_period()
                logger.info(f"Message processor initialized with rate limiting: {rate_limit_messages} messages per {rate_limit_period}s")
        else:
            logger.info("Message processor initialized without rate limiting")

    async def should_process_message(self, message: Any, bot_user_id: int | None = None) -> bool:
        """Determine if message should be processed for TTS.

        Args:
            message: Discord message object
            bot_user_id: Optional bot user ID for self-message processing

        Returns:
            True if message should be processed, False otherwise

        """
        # Check if message is in target voice channel
        if message.channel.id != self._config_manager.get_target_voice_channel_id():
            return False

        # Handle bot messages - allow self-messages if configured
        if message.author.bot:
            # Allow self-messages if enabled in configuration and bot_user_id is provided
            if self._config_manager.get_enable_self_message_processing() and bot_user_id is not None:
                # Check if this is a message from the bot itself
                if message.author.id == bot_user_id:
                    logger.debug(f"Allowing self-message from {message.author.name}")
                    # Continue with other checks
                else:
                    logger.debug(f"Skipping other bot message from {message.author.name}")
                    return False
            else:
                logger.debug(f"Skipping bot message from {message.author.name}")
                return False

        # Skip system messages
        if message.type.name != "default":
            logger.debug(f"Skipping system message type: {message.type.name}")
            return False

        # Skip empty messages
        if not message.content.strip():
            logger.debug("Skipping empty message")
            return False

        # Skip blocked users
        if message.author.id in self.blocked_users:
            logger.debug(f"Skipping message from blocked user: {message.author.name}")
            return False

        # Skip messages that start with ignored prefixes (commands, etc.)
        content = message.content.strip()
        if any(content.startswith(prefix) for prefix in self.ignored_prefixes):
            logger.debug(f"Skipping command/prefix message: {content[:20]}...")
            return False

        # Check rate limiting (skip if set to 0 or very high)
        rate_limit_messages = self._config_manager.get_rate_limit_messages()
        if rate_limit_messages > 0 and rate_limit_messages < 1000:
            if not self.rate_limiter.is_allowed(message.author.id):
                remaining = self.rate_limiter.get_remaining_time(message.author.id)
                logger.info(f"Rate limited user {message.author.name}, remaining cooldown: {remaining}s")
                return False

        logger.debug(f"Message approved for processing: {content[:50]}...")
        return True

    def process_message_content(self, content: str, author_name: str = "") -> str:
        """Process message content for TTS synthesis.

        Args:
            content: Raw message content
            author_name: Author name for context

        Returns:
            Processed content suitable for TTS

        """
        # Remove URLs and replace with description
        content = self.url_pattern.sub("link", content)

        # Replace Discord-specific mentions and emojis
        content = self._process_discord_markup(content)

        # Clean up whitespace and special characters
        content = self._clean_text_for_tts(content)

        # Don't add author context - it's unnecessary for TTS
        # The voice itself identifies the speaker

        # For very long messages, we'll chunk them later in the voice handler
        # No truncation here anymore - let the voice handler handle chunking
        max_length = self._config_manager.get_max_message_length()
        if isinstance(max_length, int) and len(content) > max_length:  # type: ignore[reportUnnecessaryIsInstance]
            logger.info(f"Long message ({len(content)} chars) will be chunked for playback")

        # Final validation
        content = content.strip()
        if not content:
            content = "message"  # Fallback for empty processed content

        logger.debug(f"Processed content: '{content}'")
        return content

    def _process_discord_markup(self, content: str) -> str:
        """Process Discord-specific markup (mentions, emojis, etc.)."""
        # Replace user mentions with "someone"
        content = self.mention_pattern.sub("someone", content)

        # Replace channel mentions with "channel"
        content = self.channel_mention_pattern.sub("channel", content)

        # Replace role mentions with "role"
        content = self.role_mention_pattern.sub("role", content)

        # Replace custom emojis with "emoji"
        content = self.emoji_pattern.sub("emoji", content)
        content = self.animated_emoji_pattern.sub("emoji", content)

        return content

    def _clean_text_for_tts(self, content: str) -> str:
        """Clean text for better TTS pronunciation."""
        # Replace multiple spaces with single space
        content = re.sub(r"\s+", " ", content)

        # Remove or replace problematic characters for Japanese TTS
        replacements = {
            "**": "",  # Bold markdown
            "__": "",  # Underline markdown
            "~~": "",  # Strikethrough markdown
            "||": "",  # Spoiler markdown
            "`": "",  # Code markdown
            "*": "",  # Italic markdown
            "_": "",  # Underscore
            "\\": "",  # Escape characters
            "\n": ".",  # Newlines become sentence breaks
            "\r": "",  # Remove carriage returns
            "\t": " ",  # Tabs become spaces
        }

        for old, new in replacements.items():
            content = content.replace(old, new)

        # Replace common English abbreviations/emoticons
        emoticon_replacements = {
            ":)": "smile",
            ":D": "big smile",
            ":(": "sad",
            ":P": "tongue out",
            "xD": "laughing hard",
            "lol": "laugh out loud",
            "LOL": "laugh out loud",
            "www": "laughing",
            "WWW": "laughing",
        }

        for emoticon, replacement in emoticon_replacements.items():
            content = content.replace(emoticon, replacement)

        # Clean up excessive punctuation
        content = re.sub(r"[！!]{2,}", "！", content)
        content = re.sub(r"[？?]{2,}", "？", content)
        content = re.sub(r"[。.]{2,}", "。", content)

        return content.strip()

    def add_blocked_user(self, user_id: int) -> None:
        """Add user to blocked list."""
        self.blocked_users.add(user_id)
        logger.info(f"Added user {user_id} to blocked list")

    def remove_blocked_user(self, user_id: int) -> None:
        """Remove user from blocked list."""
        self.blocked_users.discard(user_id)
        logger.info(f"Removed user {user_id} from blocked list")

    def reset_rate_limit(self, user_id: int) -> None:
        """Reset rate limit for specific user."""
        self.rate_limiter.reset_user(user_id)
        logger.info(f"Reset rate limit for user {user_id}")

    def get_stats(self) -> dict[str, int]:
        """Get processing statistics."""
        return {
            "blocked_users": len(self.blocked_users),
            "rate_limited_users": len(self.rate_limiter.message_times),
            "max_messages_per_period": self.rate_limiter.max_messages,
            "rate_limit_period_seconds": int(self.rate_limiter.period.total_seconds()),
        }

    def chunk_message(self, text: str, max_chunk_size: int = 500) -> list[str]:
        """Split long message into chunks at sentence boundaries.

        Args:
            text: Text to chunk
            max_chunk_size: Maximum size of each chunk

        Returns:
            List of text chunks

        """
        if len(text) <= max_chunk_size:
            return [text]

        chunks: list[str] = []

        # Try to split at sentence boundaries
        current_chunk = ""
        sentences = re.split(r"([.!?\n])", text)

        for i in range(0, len(sentences), 2):
            sentence = sentences[i]
            if i + 1 < len(sentences):
                sentence += sentences[i + 1]  # Add the separator back

            if len(current_chunk) + len(sentence) <= max_chunk_size:
                current_chunk += sentence
            else:
                # Save current chunk if not empty
                if current_chunk:
                    chunks.append(current_chunk.strip())

                # Start new chunk with current sentence
                if len(sentence) <= max_chunk_size:
                    current_chunk = sentence
                else:
                    # Force split very long sentence
                    while len(sentence) > max_chunk_size:
                        chunks.append(sentence[:max_chunk_size])
                        sentence = sentence[max_chunk_size:]
                    current_chunk = sentence

        # Add remaining chunk
        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    async def create_tts_message(self, message: Any, bot_user_id: int | None = None) -> str | None:
        """Create TTS message from Discord message.

        Args:
            message: Discord message object
            bot_user_id: Optional bot user ID for self-message processing

        Returns:
            Processed message content for TTS, or None if shouldn't be processed

        """
        if not await self.should_process_message(message, bot_user_id):
            return None

        processed_content = self.process_message_content(message.content, message.author.display_name)

        if not processed_content or processed_content.isspace():
            logger.debug("Processed content is empty, skipping")
            return None

        logger.info(f"Created TTS message from {message.author.display_name}: '{processed_content[:50]}...'")
        return processed_content

    async def process_message(self, message: Any, bot_user_id: int | None = None) -> dict[str, Any] | None:
        """Process Discord message for TTS with chunking support.

        Args:
            message: Discord message object
            bot_user_id: Optional bot user ID for self-message processing

        Returns:
            Dictionary with processed message data, or None if shouldn't be processed

        """
        logger.debug(f"📝 PROCESSOR: process_message called for {message.author.display_name}: '{message.content[:50]}'")
        logger.debug(f"📝 PROCESSOR: Message ID: {message.id}, Channel ID: {message.channel.id}")

        tts_text = await self.create_tts_message(message, bot_user_id)
        if not tts_text:
            logger.debug("📝 PROCESSOR: create_tts_message returned None - message filtered out")
            return None

        logger.debug(f"📝 PROCESSOR: TTS text created: '{tts_text[:50]}...'")

        # Chunk the message
        chunks = self.chunk_message(tts_text)
        logger.debug(f"📝 PROCESSOR: Message chunked into {len(chunks)} pieces")
        for i, chunk in enumerate(chunks):
            logger.debug(f"📝 PROCESSOR: Chunk {i + 1}: '{chunk[:30]}...'")

        result = {
            "text": tts_text,
            "user_id": message.author.id,
            "username": message.author.display_name,
            "chunks": chunks,
            "group_id": f"msg_{message.id}",
        }

        logger.debug(f"📝 PROCESSOR: Returning processed message with keys: {list(result.keys())}")
        logger.info(f"📝 PROCESSOR: Successfully processed message from {message.author.display_name} into {len(chunks)} chunks")
        return result


@lru_cache(maxsize=1)
def get_message_processor(config_manager: ConfigManager) -> MessageProcessor:
    """Return a process-wide singleton MessageProcessor without globals."""
    return MessageProcessor(config_manager)


# For backward compatibility, provide message_processor instance
class _MessageProcessorProxy:
    """Proxy to delay message processor creation until first access."""

    def __getattr__(self, name: str) -> Any:
        return getattr(get_message_processor(), name)


message_processor = _MessageProcessorProxy()
