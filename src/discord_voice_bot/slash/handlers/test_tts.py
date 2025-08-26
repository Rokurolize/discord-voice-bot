"""Test TTS slash command handler."""

import discord
from loguru import logger

from ...bot import DiscordVoiceTTSBot


async def handle(interaction: discord.Interaction, bot: DiscordVoiceTTSBot, text: str) -> None:
    """Handle test slash command."""
    logger.debug(f"Handling /test_tts command from user '{interaction.user.name}'. Text: '{text}'")
    try:
        if not hasattr(bot, "voice_handler") or not bot.voice_handler:
            _ = await interaction.response.send_message("❌ Voice handler not available", ephemeral=True)
            return

        status = bot.voice_handler.get_status()
        if not status["connected"]:
            _ = await interaction.response.send_message("❌ Not connected to voice channel", ephemeral=True)
            return

        # Process and queue the test message
        from ...message_processor import get_message_processor

        message_processor = get_message_processor(bot.config_manager)
        processed_text = message_processor.process_message_content(text, interaction.user.display_name)
        chunks = message_processor.chunk_message(processed_text)

        processed_message = {
            "text": processed_text,
            "user_id": interaction.user.id,
            "username": interaction.user.display_name,
            "chunks": chunks,
            "group_id": f"slash_test_{interaction.id}",
        }

        if bot.voice_handler:
            await bot.voice_handler.add_to_queue(processed_message)
        else:
            _ = await interaction.response.send_message("❌ Voice handler not available", ephemeral=True)
            return
        _ = await interaction.response.send_message(f"🎤 Test TTS queued: `{processed_text[:50]}...`")

        # Update stats
        if hasattr(bot, "status_manager") and bot.status_manager:
            # record_command_usage might not be async, so handle both cases
            record_usage_method = getattr(bot.status_manager, "record_command_usage", None)
            if record_usage_method:
                try:
                    result = await record_usage_method("slash_test")
                    _ = result  # Handle unused result
                except TypeError:
                    result = record_usage_method("slash_test")
                    _ = result  # Handle unused result
            result = bot.status_manager.record_tts_played()
            _ = result  # Handle unused result

    except Exception as e:
        logger.error(f"Error in test slash command: {e}")
        _ = await interaction.response.send_message("❌ Error testing TTS", ephemeral=True)
