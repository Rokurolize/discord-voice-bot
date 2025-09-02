"""Reconnect slash command handler."""

import asyncio

import discord
from loguru import logger

from ...bot import DiscordVoiceTTSBot


async def handle(interaction: discord.Interaction, bot: DiscordVoiceTTSBot) -> None:
    """
    Handle the /reconnect slash command: attempt a guided reconnect of the bot's voice client to the configured target voice channel and report status to the user.

    Performs guards (must be used in a guild, voice handler must be initialized, and a target voice channel must be configured), defers the interaction response (ephemeral), then attempts to connect to the configured channel with a 10 second timeout. On success edits the original response with a success embed that includes channel info and queue stats. On timeout or failure it edits the original response with an error embed and actionable troubleshooting/next-steps information. Best-effort cleanup of any partial voice client is attempted after a timeout.

    Side effects:
    - Sends/edits ephemeral interaction responses (original response / follow-ups).
    - Calls bot.voice_handler.connect_to_channel, bot.voice_handler.cleanup_voice_client, and bot.voice_handler.get_status.
    - Logs events and errors.

    Errors:
    - asyncio.CancelledError is propagated.
    - Other exceptions are caught, logged, and result in an ephemeral error message to the invoking user.
    """
    logger.debug(
        "Handling /reconnect command (request_id={}) from user id={} name={} guild_id={}",
        interaction.id,
        interaction.user.id,
        interaction.user.display_name,
        interaction.guild.id if interaction.guild else None,
    )
    try:
        # Guard against use in DMs
        if not interaction.guild:
            _ = await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
            return

        # Guard against uninitialized voice handler
        if not hasattr(bot, "voice_handler") or not bot.voice_handler:
            embed = discord.Embed(title="🔄 Voice Reconnection", color=discord.Color.red(), description="❌ Voice handler not initialized")
            _ = await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Guard against no target channel configured
        if not bot.config.target_voice_channel_id:
            embed = discord.Embed(title="🔄 Voice Reconnection", color=discord.Color.red(), description="❌ No target voice channel is configured for this bot.")
            _ = await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        _ = await interaction.response.defer(ephemeral=True)
        embed = discord.Embed(title="🔄 Voice Reconnection", color=discord.Color.orange(), description="Attempting to reconnect to voice channel...")
        _ = await interaction.edit_original_response(embed=embed)

        try:
            # Attempt reconnection
            logger.info(
                "🔄 MANUAL RECONNECTION - request_id={} user='{}' user_id={} guild_id={}",
                interaction.id,
                interaction.user,
                interaction.user.id,
                (interaction.guild_id or "DM"),
            )
            timed_out = False
            try:
                # Use asyncio.timeout for consistent cancellation semantics
                async with asyncio.timeout(10):
                    success = await bot.voice_handler.connect_to_channel(bot.config.target_voice_channel_id)
            except TimeoutError:
                success = False
                timed_out = True
                # Best-effort cleanup of any partial voice client
                try:
                    await bot.voice_handler.cleanup_voice_client()
                except Exception:
                    logger.opt(exception=True).warning("Cleanup after reconnect timeout failed")
                embed = discord.Embed(
                    title="🔄 Voice Reconnection",
                    color=discord.Color.red(),
                    description="❌ Reconnection timed out after 10s.",
                )

            # Get new status
            new_status = bot.voice_handler.get_status()

            if success and new_status["connected"]:
                embed = discord.Embed(title="🔄 Voice Reconnection", color=discord.Color.green(), description="✅ Successfully reconnected to voice channel!")

                _ = embed.add_field(name="📍 Channel Info", value=f"Name: {new_status['voice_channel_name']}\nID: {new_status['voice_channel_id']}", inline=True)

                _ = embed.add_field(name="📊 Queue Status", value=f"Ready: {new_status['audio_queue_size']} chunks\nSynthesizing: {new_status['synthesis_queue_size']} chunks", inline=True)

                logger.info("✅ MANUAL RECONNECTION SUCCESSFUL - connected_to={}", new_status["voice_channel_name"])
            else:
                # Preserve timeout-specific embed; otherwise show generic failure
                if not timed_out:
                    embed = discord.Embed(title="🔄 Voice Reconnection", color=discord.Color.red(), description="❌ Reconnection failed")

                _ = embed.add_field(
                    name="🔍 Troubleshooting",
                    value="Check the bot logs for detailed error information.\nCommon issues:\n• Bot lacks 'Connect' permission\n• Channel is full\n• Network connectivity issues",
                    inline=False,
                )

                _ = embed.add_field(name="🔧 Next Steps", value="Use `/voicecheck` for detailed diagnostics\nContact bot administrator if issues persist", inline=False)

                logger.error("❌ MANUAL RECONNECTION FAILED - Check logs for detailed error information")

        except asyncio.CancelledError:
            raise
        except Exception:
            embed = discord.Embed(
                title="🔄 Voice Reconnection",
                color=discord.Color.red(),
                description="❌ Error during reconnection. Please try again later.",
            )
            logger.exception(
                "💥 CRITICAL ERROR during manual reconnection (request_id={}, user_id={}, guild_id={})",
                interaction.id,
                interaction.user.id,
                (interaction.guild_id or "DM"),
            )

        _ = await interaction.edit_original_response(embed=embed)

    except asyncio.CancelledError:
        raise
    except Exception:
        logger.exception(
            "Error in reconnect slash command (request_id={}, user_id={}, guild_id={})",
            getattr(interaction, "id", None),
            getattr(getattr(interaction, "user", None), "id", None),
            (interaction.guild_id or "DM"),
        )
        try:
            if interaction.response.is_done():
                _ = await interaction.followup.send("❌ Error during reconnection", ephemeral=True)
            else:
                _ = await interaction.response.send_message("❌ Error during reconnection", ephemeral=True)
        except Exception as followup_err:
            logger.opt(exception=followup_err).debug("Suppressed secondary error while responding to interaction")
