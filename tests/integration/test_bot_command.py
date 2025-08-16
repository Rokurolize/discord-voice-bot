#!/usr/bin/env python3
"""Test bot commands to verify it's responding."""

import asyncio

import discord

from src.config import config


async def send_bot_command():
    """Send a bot command to test if it's responding."""
    intents = discord.Intents.default()
    intents.message_content = True
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        print(f"Command test client ready: {client.user}")

        # Get target channel
        channel = client.get_channel(config.target_voice_channel_id)
        if channel:
            print(f"Found channel: {channel.name}")

            # Send bot status command
            await channel.send("!tts status")
            print("✅ Sent !tts status command")
            await asyncio.sleep(2)

            # Send test command
            await channel.send("!tts test 修正テスト中です")
            print("✅ Sent !tts test command")
            await asyncio.sleep(5)

            await client.close()
        else:
            print("❌ Channel not found")
            await client.close()

    await client.start(config.discord_token)


if __name__ == "__main__":
    print("🧪 Sending bot commands to test responsiveness...")
    asyncio.run(send_bot_command())
