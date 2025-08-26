"""Reconnect slash command handler."""

import discord
from loguru import logger

from ...bot import DiscordVoiceTTSBot


async def handle(interaction: discord.Interaction, bot: DiscordVoiceTTSBot) -> None:
    """Handle reconnect slash command."""
    logger.debug(f"Handling /reconnect command from user '{interaction.user}' (id={interaction.user.id})")
    try:
        if not hasattr(bot, "voice_handler") or not bot.voice_handler:
            embed = discord.Embed(title="🔄 Voice Reconnection", color=discord.Color.red(), description="❌ Voice handler not initialized")
            _ = await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        embed = discord.Embed(title="🔄 Voice Reconnection", color=discord.Color.orange(), description="Attempting to reconnect to voice channel...")

        _ = await interaction.response.send_message(embed=embed, ephemeral=True)

        try:
            # Attempt reconnection
            logger.info(f"🔄 MANUAL RECONNECTION - User {interaction.user} (id={interaction.user.id}) requested voice reconnection")
            from ...config import get_config

            success = await bot.voice_handler.connect_to_channel(get_config().target_voice_channel_id)

            # Get new status
            new_status = bot.voice_handler.get_status()

            if success and new_status["connected"]:
                embed = discord.Embed(title="🔄 Voice Reconnection", color=discord.Color.green(), description="✅ Successfully reconnected to voice channel!")

                _ = embed.add_field(name="📍 Channel Info", value=f"Name: {new_status['voice_channel_name']}\nID: {new_status['voice_channel_id']}", inline=True)

                _ = embed.add_field(name="📊 Queue Status", value=f"Ready: {new_status['audio_queue_size']} chunks\nSynthesizing: {new_status['synthesis_queue_size']} chunks", inline=True)

                logger.info(f"✅ MANUAL RECONNECTION SUCCESSFUL - Connected to {new_status['voice_channel_name']}")
            else:
                embed = discord.Embed(title="🔄 Voice Reconnection", color=discord.Color.red(), description="❌ Reconnection failed")

                _ = embed.add_field(
                    name="🔍 Troubleshooting",
                    value="Check the bot logs for detailed error information.\nCommon issues:\n• Bot lacks 'Connect' permission\n• Channel is full\n• Network connectivity issues",
                    inline=False,
                )

                _ = embed.add_field(name="🔧 Next Steps", value="Use `/voicecheck` for detailed diagnostics\nContact bot administrator if issues persist", inline=False)

                logger.error("❌ MANUAL RECONNECTION FAILED - Check logs for detailed error information")

        except Exception:
            embed = discord.Embed(
                title="🔄 Voice Reconnection",
                color=discord.Color.red(),
                description="❌ Error during reconnection. Please try again later."
            )
            logger.exception("💥 CRITICAL ERROR during manual reconnection")

        _ = await interaction.edit_original_response(embed=embed)

    except Exception:
        logger.exception("Error in reconnect slash command")
        try:
            if interaction.response.is_done():
                _ = await interaction.followup.send("❌ Error during reconnection", ephemeral=True)
            else:
                _ = await interaction.response.send_message("❌ Error during reconnection", ephemeral=True)
        except Exception as followup_err:
            logger.debug(f"Suppressed secondary error while responding to interaction: {followup_err!s}")
