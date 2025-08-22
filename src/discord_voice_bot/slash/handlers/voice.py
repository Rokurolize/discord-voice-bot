"""Voice slash command handler."""

from typing import Optional

import discord
from loguru import logger

from ...bot import DiscordVoiceTTSBot


async def handle(interaction: discord.Interaction, bot: DiscordVoiceTTSBot, speaker: Optional[str] = None) -> None:
    """Handle voice slash command."""
    try:
        from ...user_settings import user_settings

        user_id = str(interaction.user.id)

        # If no speaker specified, show current setting
        if speaker is None:
            current_settings = user_settings.get_user_settings(user_id)
            if current_settings:
                embed = discord.Embed(
                    title="🎭 Your Voice Settings",
                    color=discord.Color.blue(),
                    description=f"Current voice: **{current_settings['speaker_name']}** (ID: {current_settings['speaker_id']})",
                )
            else:
                embed = discord.Embed(
                    title="🎭 Your Voice Settings",
                    color=discord.Color.greyple(),
                    description="No custom voice set. Using default voice.",
                )
            embed.add_field(
                name="Commands",
                value="`/voice <name>` - Set voice\n`/voice reset` - Reset to default\n`/voices` - List available",
                inline=False,
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Handle reset
        if speaker.lower() == "reset":
            if user_settings.remove_user_speaker(user_id):
                await interaction.response.send_message("✅ Voice preference reset to default", ephemeral=True)
            else:
                await interaction.response.send_message("ℹ️ You don't have a custom voice set", ephemeral=True)
            return

        # Get available speakers
        from ...tts_engine import tts_engine

        speakers = await tts_engine.get_available_speakers()
        from ...config import config

        # Find matching speaker (case-insensitive)
        speaker_lower = speaker.lower()
        matched_speaker = None
        matched_id = None

        for name, speaker_id in speakers.items():
            if name.lower() == speaker_lower or str(speaker_id) == speaker:
                matched_speaker = name
                matched_id = speaker_id
                break

        if matched_speaker and matched_id is not None:
            # Pass current engine to ensure proper mapping
            if user_settings.set_user_speaker(user_id, matched_id, matched_speaker, config.tts_engine):
                await interaction.response.send_message(f"✅ Voice set to **{matched_speaker}** (ID: {matched_id}) on {config.tts_engine.upper()}", ephemeral=True)
                # Test the new voice
                test_text = f"{matched_speaker}の声です"
                if hasattr(bot, "voice_handler") and bot.voice_handler:
                    from ...message_processor import message_processor

                    chunks = message_processor.chunk_message(test_text)
                    processed_message = {
                        "text": test_text,
                        "user_id": interaction.user.id,
                        "username": interaction.user.display_name,
                        "chunks": chunks,
                        "group_id": f"slash_voice_test_{interaction.id}",
                    }
                    await bot.voice_handler.add_to_queue(processed_message)
            else:
                await interaction.response.send_message("❌ Failed to save voice preference", ephemeral=True)
        else:
            await interaction.response.send_message(f"❌ Voice '{speaker}' not found. Use `/voices` to see available options.", ephemeral=True)

    except Exception as e:
        logger.error(f"Error in voice slash command: {e}")
        await interaction.response.send_message("❌ Error setting voice preference", ephemeral=True)
