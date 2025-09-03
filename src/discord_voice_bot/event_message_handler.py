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
            logger.debug(f"🔵 RECEIVED message from {message.author.name} (ID: {message.id}) in channel {message.channel.id}: '{message.content[:50]}'")
            logger.debug(f"🔵 Message details - Type: {message.type}, Author bot: {message.author.bot}, Content length: {len(message.content)}")

            # Process commands first (with optional rate limiting) - BEFORE TTS filtering
            logger.debug("🟡 STEP 1: Processing commands for message")
            if hasattr(self.bot, "voice_handler") and self.bot.voice_handler:  # type: ignore
                logger.debug("🟡 Using voice_handler.make_rate_limited_request for bot.process_commands")
                await self.bot.voice_handler.make_rate_limited_request(self.bot.process_commands, message)  # type: ignore
            else:
                logger.debug("🟡 Using bot.process_commands directly")
                await self.bot.process_commands(message)
            logger.debug("✅ STEP 1 COMPLETED: Command processing done")

            # Apply comprehensive message filtering
            logger.debug("🟠 STEP 2: Applying message filtering")
            should_process = await self._should_process_message(message)
            logger.debug(f"🟠 Message filtering result: {should_process}")
            if not should_process:
                logger.debug("🟠 Message filtered out - not processing for TTS")
                return
            logger.debug("✅ STEP 2 COMPLETED: Message passed filtering")

            # Apply additional message validation
            logger.debug("🟢 STEP 3: Applying message validation")
            processed_message = await self._validate_and_process_message(message)
            logger.debug(f"🟢 Validation result: {processed_message is not None}")
            if not processed_message:
                logger.debug(f"Message {message.id} from {message.author.name} was filtered out after validation")
                return
            logger.debug("✅ STEP 3 COMPLETED: Message passed validation")

            # Add to TTS queue with rate limiting
            logger.debug("🔴 STEP 4: Adding message to TTS queue")
            if hasattr(self.bot, "voice_handler") and self.bot.voice_handler:  # type: ignore
                logger.debug("🔴 Voice handler found, attempting to queue message")
                try:
                    await self.bot.voice_handler.add_to_queue(processed_message)  # type: ignore
                    current_count = self.bot.stats.get("messages_processed", 0)  # type: ignore
                    self.bot.stats["messages_processed"] = int(current_count if current_count is not None else 0) + 1  # type: ignore
                    logger.debug(f"✅ STEP 4 COMPLETED: Successfully queued TTS message from {message.author.display_name}")
                    logger.info(f"📢 TTS Message queued - Author: {message.author.display_name}, Content: '{message.content[:30]}...'")
                except Exception as e:
                    logger.error(f"❌ Failed to queue TTS message: {e}")
                    logger.error(f"❌ Processed message keys: {list(processed_message.keys())}")
            else:
                logger.warning("Voice handler not initialized, cannot queue TTS message")
                logger.warning(f"Available bot attributes: {[attr for attr in dir(self.bot) if 'handler' in attr.lower()]}")

        except Exception:
            logger.exception(f"❌ CRITICAL ERROR processing message {message.id} from {message.author.name}")

            # Try to update stats if possible
            try:
                current_errors = self.bot.stats.get("connection_errors", 0)  # type: ignore
                self.bot.stats["connection_errors"] = int(current_errors if current_errors is not None else 0) + 1  # type: ignore
                logger.debug("✅ Error stats updated successfully")
            except Exception as stats_error:
                logger.error(f"❌ Failed to update error stats: {stats_error}")

            # Continue processing other messages even if one fails
            logger.info("✅ Continuing with next message processing despite error")

    async def _should_process_message(self, message: discord.Message) -> bool:
        """Determine if a message should be processed following Discord's patterns."""
        try:
            logger.debug(f"🔍 FILTERING: Checking message from {message.author.name} (bot: {message.author.bot})")

            # Handle bot messages - allow self-messages if configured
            if message.author.bot:
                logger.debug(f"🔍 FILTERING: Message is from bot {message.author.name}")
                # Allow self-messages if enabled in configuration
                if self._config_manager.get_enable_self_message_processing():
                    logger.debug("🔍 FILTERING: Self-message processing enabled")
                    # Check if this is a message from the bot itself
                    if self.bot.user and message.author.id == self.bot.user.id:
                        logger.debug(f"🔍 FILTERING: Allowing self-message from {message.author.name}")
                        # Continue with other checks
                    else:
                        logger.debug(f"🔍 FILTERING: Skipping other bot message from {message.author.name}")
                        return False
                else:
                    logger.debug(f"🔍 FILTERING: Skipping bot message from {message.author.name} (self-message processing disabled)")
                    return False

            # Skip system messages
            if message.type != discord.MessageType.default:
                logger.debug(f"🔍 FILTERING: Skipping system message type {message.type}")
                return False

            # Skip empty messages
            if not message.content or not message.content.strip():
                logger.warning(f"🔍 FILTERING: Skipping empty message from {message.author.name} (ID: {message.id})")
                logger.warning(f"🔍 FILTERING: Empty message details - Content: '{message.content}', Length: {len(message.content)}")
                channel_name = getattr(message.channel, "name", "Unknown")
                logger.warning(f"🔍 FILTERING: Empty message timestamp: {message.created_at}, Channel: {channel_name}")
                return False

            # Skip messages that are too long (Discord's 2000 char limit)
            if len(message.content) > 2000:
                logger.debug(f"🔍 FILTERING: Skipping too long message ({len(message.content)} chars)")
                return False

            # Only process messages from the target voice channel's text chat
            if hasattr(message.channel, "id"):
                channel_name = getattr(message.channel, "name", "Unknown")
                logger.debug(f"🔍 FILTERING: Processing message from channel {message.channel.id} ({channel_name})")
                # For now, process messages from any channel that the bot can see
                # This allows flexibility for different server setups
                return True

            logger.debug("🔍 FILTERING: Message passed all filters")
            return True

        except Exception:
            logger.exception("🔍 FILTERING ERROR: Error in message filtering")
            return False

    async def _validate_and_process_message(self, message: discord.Message) -> dict[str, Any] | None:
        """Validate and process message with proper sanitization."""
        try:
            logger.debug("🔍 VALIDATION: Starting message validation")

            # Sanitize message content
            logger.debug("🔍 VALIDATION: Sanitizing message content")
            sanitized_content = self._sanitize_message_content(message.content)
            logger.debug(f"🔍 VALIDATION: Content sanitized from {len(message.content)} to {len(sanitized_content)} chars")

            # Use the existing message processor
            logger.debug("🔍 VALIDATION: Getting message processor")
            from .message_processor import get_message_processor

            message_processor = get_message_processor(self._config_manager)
            logger.debug("🔍 VALIDATION: Message processor obtained")

            # Pass bot user ID for self-message processing
            bot_user_id = self.bot.user.id if self.bot.user else None
            logger.debug(f"🔍 VALIDATION: Processing message with bot_user_id={bot_user_id}")

            processed_message = await message_processor.process_message(message, bot_user_id)
            logger.debug(f"🔍 VALIDATION: Message processor result: {processed_message is not None}")

            if processed_message:
                logger.debug("🔍 VALIDATION: Adding additional validation data")
                # Add additional validation and sanitization
                processed_message["original_content"] = message.content
                processed_message["sanitized_content"] = sanitized_content
                processed_message["validation_passed"] = True
                logger.debug("🔍 VALIDATION: Additional data added")

                # Apply rate limiting to message processing
                logger.debug("🔍 VALIDATION: Applying rate limiting")
                if hasattr(self.bot, "voice_handler") and self.bot.voice_handler:  # type: ignore
                    await self.bot.voice_handler.rate_limiter.wait_if_needed()  # type: ignore
                    logger.debug("🔍 VALIDATION: Rate limiting applied")
                else:
                    logger.debug("🔍 VALIDATION: No voice handler for rate limiting")

                logger.debug("🔍 VALIDATION: Message validation completed successfully")
            else:
                logger.debug(f"Message from '{message.author.name}' was valid but returned no processable content (e.g., URL only).")

            return processed_message

        except Exception:
            logger.exception("🔍 VALIDATION ERROR: Error in message validation")
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
                "“": '"',
                "”": '"',
                "‘": "'",
                "’": "'",
            }

            for old, new in replacements.items():
                content = content.replace(old, new)

            # Remove non-printable characters but keep basic unicode
            content = "".join(c for c in content if c.isprintable() or c in ["\n", "\t", " "])

            # Limit length to prevent abuse
            if len(content) > 500:  # Reasonable limit for TTS
                content = content[:497] + "..."

            return content.strip()

        except Exception:
            logger.exception("Error sanitizing message content")
            return content[:100] + "..." if len(content) > 100 else content
