#!/usr/bin/env python3
"""Test script to verify bot message processing from target Discord channel."""

import asyncio

import discord
from src.discord_voice_bot.config_manager import ConfigManagerImpl


async def test_message_processing():
    """Test bot message processing capabilities."""
    try:
        # Initialize configuration
        config_manager = ConfigManagerImpl()
        token = config_manager.get_discord_token()
        target_guild_id = config_manager.get_target_guild_id()
        target_channel_id = config_manager.get_target_voice_channel_id()

        print("🧪 Bot Message Processing Test")
        print(f"   Target Guild ID: {target_guild_id}")
        print(f"   Target Channel ID: {target_channel_id}")
        print()

        # Create Discord client with required intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.voice_states = True

        client = discord.Client(intents=intents)
        messages_processed = []

        @client.event
        async def on_ready():
            print(f"✅ Bot connected as: {client.user}")
            print(f"   Bot is in {len(client.guilds)} servers")
            print()

            # Find target guild and channel
            target_guild = client.get_guild(target_guild_id)
            if not target_guild:
                print(f"❌ Target guild {target_guild_id} not found!")
                await client.close()
                return

            target_channel = client.get_channel(target_channel_id)
            if not target_channel:
                print(f"❌ Target channel {target_channel_id} not found!")
                await client.close()
                return

            print(f"✅ Found target channel: {target_channel.name}")
            print()

            # Send a test message to the target channel
            try:
                test_message = await target_channel.send("🎤 テストメッセージ - ずんだもんが読み上げてね")
                print(f"✅ Successfully sent test message to {target_channel.name}")
                print(f"   Message ID: {test_message.id}")
                print(f"   Message content: {test_message.content}")
                print()

                # Wait a bit for the bot to potentially process the message
                print("⏳ Waiting 5 seconds for message processing...")
                await asyncio.sleep(5)

                # Clean up the test message
                try:
                    await test_message.delete()
                    print("🧹 Test message cleaned up")
                except Exception as e:
                    print(f"⚠️ Could not delete test message: {e}")

            except Exception as e:
                print(f"❌ Failed to send test message: {e}")
                print(f"   Error details: {type(e).__name__}: {e}")

            print()
            print("🎉 Message processing test completed!")
            await client.close()

        @client.event
        async def on_message(message):
            """Handle incoming messages."""
            # Don't process our own messages to avoid loops
            if message.author == client.user:
                return

            # Only process messages from the target channel
            if message.channel.id == target_channel_id:
                messages_processed.append({"content": message.content, "author": str(message.author), "channel": str(message.channel), "timestamp": message.created_at})

                print("📨 Message received from target channel:")
                print(f"   Author: {message.author}")
                print(f"   Channel: {message.channel}")
                print(f"   Content: {message.content}")
                print()

        @client.event
        async def on_error(event, *args, **kwargs):
            print(f"❌ Discord client error in {event}: {args}")

        # Start the bot
        print("🔌 Connecting to Discord...")
        await client.start(token)

    except Exception as e:
        print(f"💥 Test failed with error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_message_processing())
