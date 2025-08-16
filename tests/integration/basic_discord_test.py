#!/usr/bin/env python3
"""Basic Discord connection test without voice."""

import asyncio

import discord

from src.config import config


async def test_basic_connection():
    """Test basic Discord bot connection."""
    print("🤖 Testing basic Discord connection...")

    try:
        # Create simple client
        intents = discord.Intents.default()
        client = discord.Client(intents=intents)

        @client.event
        async def on_ready():
            print(f"✅ Connected as: {client.user}")
            print(f"📡 User ID: {client.user.id}")
            print(f"🌐 Guilds: {len(client.guilds)}")

            # Try to get the target channel (without connecting to voice)
            channel = client.get_channel(config.target_voice_channel_id)
            if channel:
                print(f"🎯 Found target channel: {channel.name} (Type: {type(channel).__name__})")
                print(f"📍 Guild: {channel.guild.name}")
                print(f'👥 Members in voice: {len(channel.members) if hasattr(channel, "members") else "N/A"}')
            else:
                print(f"❌ Could not find channel with ID: {config.target_voice_channel_id}")

            print("✅ Basic Discord connection test completed")
            await client.close()

        # Set timeout for connection
        async def timeout_handler():
            await asyncio.sleep(10)
            print("⏱️  Connection timeout")
            await client.close()

        # Start both connection and timeout handler
        await asyncio.gather(
            client.start(config.discord_token),
            timeout_handler(),
            return_exceptions=True,
        )

    except Exception as e:
        print(f"❌ Connection failed: {type(e).__name__}: {e!s}")


if __name__ == "__main__":
    print("🧪 Basic Discord Connection Test")
    asyncio.run(test_basic_connection())
