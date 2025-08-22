"""Test TTS slash command handler."""

import discord
from loguru import logger

from ...bot import DiscordVoiceTTSBot


async def handle(interaction: discord.Interaction, bot: DiscordVoiceTTSBot, text: str) -> None:
    """Handle test slash command."""
    try:
        if not hasattr(bot, "voice_handler") or not bot.voice_handler:
            await interaction.response.send_message("❌ Voice handler not available", ephemeral=True)
            return

        status = bot.voice_handler.get_status()
        if not status["connected"]:
            await interaction.response.send_message("❌ Not connected to voice channel", ephemeral=True)
            return

        # Process and queue the test message
        from ...message_processor import message_processor

        processed_text = message_processor.process_message_content(text, interaction.user.display_name)
        chunks = message_processor.chunk_message(processed_text)

        processed_message = {
            "text": processed_text,
            "user_id": interaction.user.id,
            "username": interaction.user.display_name,
            "chunks": chunks,
            "group_id": f"slash_test_{interaction.id}",
        }

        await bot.voice_handler.add_to_queue(processed_message)
        await interaction.response.send_message(f"🎤 Test TTS queued: `{processed_text[:50]}...`")

        # Update stats
        if hasattr(bot, "status_manager") and bot.status_manager:
            await bot.status_manager.record_command_usage("slash_test")
            bot.status_manager.record_tts_played()

    except Exception as e:
        logger.error(f"Error in test slash command: {e}")
        await interaction.response.send_message("❌ Error testing TTS", ephemeral=True)
