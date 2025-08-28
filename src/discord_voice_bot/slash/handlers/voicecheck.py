"""Voicecheck slash command handler."""

import discord
from loguru import logger

from ...bot import DiscordVoiceTTSBot


async def handle(interaction: discord.Interaction, bot: DiscordVoiceTTSBot) -> None:
    """Handle voicecheck slash command."""
    logger.debug("Handling /voicecheck command from user id={} name={}", interaction.user.id, interaction.user.display_name)
    try:
        if not hasattr(bot, "voice_handler") or not bot.voice_handler:
            embed = discord.Embed(title="🔍 Voice Health Check", color=discord.Color.red(), description="❌ Voice handler not initialized")
            _ = await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Perform health check
        embed = discord.Embed(title="🔍 Voice Health Check", color=discord.Color.blue(), description="Performing comprehensive voice connection diagnostics...")

        # Send initial message
        _ = await interaction.response.send_message(embed=embed, ephemeral=True)

        try:
            # Get basic status
            status = bot.voice_handler.get_status()
            health_status = await bot.voice_handler.health_check()

            # Update embed with results
            embed = discord.Embed(
                title="🔍 Voice Health Check Results",
                color=(discord.Color.green() if health_status["healthy"] else discord.Color.red()),
                description=f"Overall Status: {'✅ HEALTHY' if health_status['healthy'] else '❌ ISSUES FOUND'}",
            )

            # Connection status
            _ = embed.add_field(
                name="🔗 Connection Status",
                value=(
                    f"Voice Client: {'✅' if health_status['voice_client_exists'] else '❌'}\n"
                    f"Connected: {'✅' if health_status['voice_client_connected'] else '❌'}\n"
                    f"Channel: {status.get('voice_channel_name', 'None') or 'None'}"
                ),
                inline=True,
            )

            # Audio system status
            _ = embed.add_field(
                name="🎵 Audio System",
                value=(
                    f"Playback Ready: {'✅' if health_status['audio_playback_ready'] else '❌'}\n"
                    f"Synthesis: {'✅' if health_status['can_synthesize'] else '❌'}\n"
                    f"Queue Size: {status.get('total_queue_size', 0)}"
                ),
                inline=True,
            )

            # Issues and recommendations
            if health_status["issues"]:
                issues_text = "\n".join(f"• {issue}" for issue in health_status["issues"])
                _ = embed.add_field(name="⚠️ Issues Found", value=issues_text, inline=False)

            if health_status["recommendations"]:
                recommendations_text = "\n".join(f"💡 {rec}" for rec in health_status["recommendations"])
                _ = embed.add_field(name="🔧 Recommendations", value=recommendations_text, inline=False)

            # If not healthy, offer to attempt reconnection
            if not health_status["healthy"]:
                _ = embed.add_field(name="🔄 Quick Actions", value="Use `/reconnect` to attempt reconnection", inline=False)

        except Exception as e:
            embed = discord.Embed(title="🔍 Voice Health Check", color=discord.Color.red(), description=f"❌ Error during health check: {e}")

        # Edit the original response with results
        _ = await interaction.edit_original_response(embed=embed)

    except Exception:
        logger.exception("Error in voicecheck slash command")
        _ = await interaction.response.send_message("❌ Error during health check", ephemeral=True)
