#!/usr/bin/env python3
"""Test script to send messages to Discord voice channel for TTS testing."""

import asyncio

import discord

from src.config import config


async def send_test_messages():
    """Send test messages to the Discord voice channel."""
    # Create client with same intents as bot
    intents = config.get_intents()
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        print(f"✅ Test client logged in as {client.user}")

        # Get target channel
        channel = client.get_channel(config.target_voice_channel_id)
        if not channel:
            print(f"❌ Channel {config.target_voice_channel_id} not found")
            await client.close()
            return

        print(f"✅ Found channel: {channel.name}")

        # Test messages to send
        test_messages = [
            "こんにちは、ずんだもんなのだ！",
            "Hello, this is a test message!",
            "日本語とEnglish混合テストです",
            "長いメッセージのテストです。これは200文字制限をテストするための長い文章です。ずんだもんボットが正しく処理できるかチェックしています。",
            "絵文字テスト😊🎉✨",
            "URLテスト https://example.com",
            "メンション<@123456789>テスト",
            "短い",
            "!tts status",
        ]

        print(f"📤 Sending {len(test_messages)} test messages...")

        for i, message in enumerate(test_messages, 1):
            try:
                await channel.send(f"[Test {i}] {message}")
                print(f"✅ Sent message {i}: {message[:50]}...")
                await asyncio.sleep(3)  # Wait between messages
            except Exception as e:
                print(f"❌ Failed to send message {i}: {e}")

        print("✅ All test messages sent!")
        await asyncio.sleep(2)
        await client.close()

    try:
        await client.start(config.discord_token)
    except Exception as e:
        print(f"❌ Failed to start test client: {e}")


if __name__ == "__main__":
    print("🧪 Starting TTS functionality test...")
    asyncio.run(send_test_messages())
