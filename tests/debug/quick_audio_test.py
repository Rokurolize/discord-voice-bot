#!/usr/bin/env python3
"""Quick audio test for Discord TTS bot."""

import asyncio

import discord

from src.config import config


async def send_test_message():
    """Send a simple test message to check audio."""
    intents = discord.Intents.default()
    intents.message_content = True
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        print(f"Test client ready: {client.user}")

        # Get target channel
        channel = client.get_channel(config.target_voice_channel_id)
        if channel:
            print(f"Found channel: {channel.name}")

            # Send simple test message
            await channel.send("こんにちは、音声テスト中です！")
            print("✅ Sent test message!")

            await asyncio.sleep(5)  # Wait for TTS processing
            await client.close()
        else:
            print("❌ Channel not found")
            await client.close()

    await client.start(config.discord_token)


if __name__ == "__main__":
    print("🧪 Sending quick audio test message...")
    asyncio.run(send_test_message())
