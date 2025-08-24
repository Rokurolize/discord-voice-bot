"""Message handling for event handler."""

from typing import TYPE_CHECKING, Any

import discord
from discord.ext import commands
from loguru import logger

if TYPE_CHECKING:
    from .protocols import ConfigManager

# Type alias for Discord bot to avoid circular imports - use commands.Bot at runtime
DiscordBot = commands.Bot


class MessageHandler:
    """Handles Discord message events and processing."""

    def __init__(self, bot: DiscordBot, config_manager: "ConfigManager"):
        """Initialize message handler."""
        super().__init__()
        self.bot = bot
        self._config_manager = config_manager

    async def handle_message(self, message: discord.Message) -> None:
        """Handle message events with proper filtering and validation."""
        try:
            # Log all messages for debugging (rate limited)
            logger.debug(f"Received message from {message.author.name} (ID: {message.id}) in channel {message.channel.id}: {message.content[:50]}")

            # Process commands first (with rate limiting) - BEFORE TTS filtering
            logger.debug(f"Processing commands for message: {message.content}")
            if hasattr(self.bot, "command_handler") and self.bot.command_handler:  # type: ignore
                await self.bot.command_handler.process_command(message)  # type: ignore
            elif hasattr(self.bot, "voice_handler") and self.bot.voice_handler:  # type: ignore
                await self.bot.voice_handler.make_rate_limited_request(self.bot.process_commands, message)  # type: ignore
            else:
                await self.bot.process_commands(message)

            # Apply comprehensive message filtering
            if not await self._should_process_message(message):
                return

            # Apply additional message validation
            processed_message = await self._validate_and_process_message(message)
            if not processed_message:
                logger.debug(f"Message {message.id} from {message.author.name} was filtered out after validation")
                return

            # Add to TTS queue with rate limiting
            if hasattr(self.bot, "voice_handler") and self.bot.voice_handler:  # type: ignore
                await self.bot.voice_handler.add_to_queue(processed_message)  # type: ignore
                current_count = self.bot.stats.get("messages_processed", 0)  # type: ignore
                self.bot.stats["messages_processed"] = int(current_count if current_count is not None else 0) + 1  # type: ignore
                logger.debug(f"Queued TTS message from {message.author.display_name}")
            else:
                logger.warning("Voice handler not initialized, cannot queue TTS message")

        except Exception as e:
            logger.error(f"Error processing message {message.id}: {e!s}")
            current_errors = self.bot.stats.get("connection_errors", 0)  # type: ignore
            self.bot.stats["connection_errors"] = int(current_errors if current_errors is not None else 0) + 1  # type: ignore

    async def _should_process_message(self, message: discord.Message) -> bool:
        """Determine if a message should be processed following Discord's patterns."""
        try:
            # Handle bot messages - allow self-messages if configured
            if message.author.bot:
                # Allow self-messages if enabled in configuration
                if self._config_manager.get_enable_self_message_processing():
                    # Check if this is a message from the bot itself
                    if self.bot.user and message.author.id == self.bot.user.id:
                        logger.debug(f"Allowing self-message from {message.author.name}")
                        # Continue with other checks
                    else:
                        logger.debug(f"Skipping other bot message from {message.author.name}")
                        return False
                else:
                    logger.debug(f"Skipping bot message from {message.author.name}")
                    return False

            # Skip system messages
            if message.type != discord.MessageType.default:
                return False

            # Skip empty messages
            if not message.content or not message.content.strip():
                return False

            # Skip messages that are too long (Discord's 2000 char limit)
            if len(message.content) > 2000:
                return False

            # Only process messages from the target voice channel's text chat
            if hasattr(message.channel, "id"):
                # For now, process messages from any channel that the bot can see
                # This allows flexibility for different server setups
                return True

            return True

        except Exception as e:
            logger.error(f"Error in message filtering: {e!s}")
            return False

    async def _validate_and_process_message(self, message: discord.Message) -> dict[str, Any] | None:
        """Validate and process message with proper sanitization."""
        try:
            # Sanitize message content
            sanitized_content = self._sanitize_message_content(message.content)

            # Use the existing message processor
            from .message_processor import get_message_processor

            message_processor = get_message_processor(self._config_manager)
            # Pass bot user ID for self-message processing
            bot_user_id = self.bot.user.id if self.bot.user else None
            processed_message = await message_processor.process_message(message, bot_user_id)

            if processed_message:
                # Add additional validation and sanitization
                processed_message["original_content"] = message.content
                processed_message["sanitized_content"] = sanitized_content
                processed_message["validation_passed"] = True

                # Apply rate limiting to message processing
                if hasattr(self.bot, "voice_handler") and self.bot.voice_handler:  # type: ignore
                    await self.bot.voice_handler.rate_limiter.wait_if_needed()  # type: ignore

            return processed_message

        except Exception as e:
            logger.error(f"Error in message validation: {e!s}")
            return None

    def _sanitize_message_content(self, content: str) -> str:
        """Sanitize message content for TTS processing."""
        try:
            # Remove excessive whitespace
            content = " ".join(content.split())

            # Remove or replace problematic characters
            replacements = {
                "\r\n": " ",
                "\r": " ",
                "\n": " ",
                "\t": " ",
                "…": "...",
                "—": "-",
                "–": "-",
                '"': '"',  # Keep quotes but ensure they're proper
                """: "'",
                """: "'",
            }

            for old, new in replacements.items():
                content = content.replace(old, new)

            # Remove non-printable characters but keep basic unicode
            content = "".join(c for c in content if c.isprintable() or c in ["\n", "\t", " "])

            # Limit length to prevent abuse
            if len(content) > 500:  # Reasonable limit for TTS
                content = content[:497] + "..."

            return content.strip()

        except Exception as e:
            logger.error(f"Error sanitizing message content: {e!s}")
            return content[:100] + "..." if len(content) > 100 else content
