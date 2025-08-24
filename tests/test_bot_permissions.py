#!/usr/bin/env python3
"""Test script to verify bot permissions and connectivity to target Discord server/channel."""

import asyncio

import discord
from src.discord_voice_bot.config_manager import ConfigManagerImpl


async def test_bot_permissions():
    """Test bot permissions and connectivity."""
    try:
        # Initialize configuration
        config_manager = ConfigManagerImpl()
        token = config_manager.get_discord_token()
        target_guild_id = config_manager.get_target_guild_id()
        target_channel_id = config_manager.get_target_voice_channel_id()

        print("🤖 Bot Configuration Test")
        print(f"   Target Guild ID: {target_guild_id}")
        print(f"   Target Channel ID: {target_channel_id}")
        print()

        # Create Discord client with minimal intents
        intents = discord.Intents.default()
        intents.guilds = True
        intents.voice_states = True

        client = discord.Client(intents=intents)

        @client.event
        async def on_ready():
            print(f"✅ Bot connected as: {client.user}")
            print(f"   Bot is in {len(client.guilds)} servers")
            print()

            # Find target guild
            target_guild = client.get_guild(target_guild_id)
            if not target_guild:
                print(f"❌ Target guild {target_guild_id} not found!")
                print("   Bot may not be invited to this server or the Guild ID may be incorrect.")
                for guild in client.guilds:
                    print(f"   Available guild: {guild.name} (ID: {guild.id})")
                await client.close()
                return

            print(f"✅ Found target guild: {target_guild.name}")
            print(f"   Guild member count: {target_guild.member_count}")
            print()

            # Check bot's permissions in the guild
            bot_member = target_guild.get_member(client.user.id)
            if not bot_member:
                print("❌ Bot is not a member of the target guild!")
                await client.close()
                return

            print("🔐 Bot Permissions Check:")

            # Check voice permissions
            voice_permissions = bot_member.guild_permissions
            voice_perms_ok = voice_permissions.connect and voice_permissions.speak and voice_permissions.use_voice_activation

            print(f"   Connect to voice channels: {'✅' if voice_permissions.connect else '❌'}")
            print(f"   Speak in voice channels: {'✅' if voice_permissions.speak else '❌'}")
            print(f"   Use voice activation: {'✅' if voice_permissions.use_voice_activation else '❌'}")

            if not voice_perms_ok:
                print("❌ Bot is missing required voice permissions!")
            else:
                print("✅ Bot has required voice permissions")

            print()

            # Find target voice channel
            target_channel = client.get_channel(target_channel_id)
            if not target_channel:
                print(f"❌ Target channel {target_channel_id} not found!")
                print("   Channel may not exist or the Channel ID may be incorrect.")
                for channel in target_guild.channels:
                    if isinstance(channel, discord.VoiceChannel):
                        print(f"   Available voice channel: {channel.name} (ID: {channel.id})")
                await client.close()
                return

            print(f"✅ Found target voice channel: {target_channel.name}")
            print(f"   Channel type: {type(target_channel).__name__}")
            print(f"   User limit: {getattr(target_channel, 'user_limit', 'N/A')}")
            print()

            # Test message sending to a text channel (if available)
            text_channels = [c for c in target_guild.channels if isinstance(c, discord.TextChannel)]
            if text_channels:
                test_channel = text_channels[0]  # Use first available text channel
                try:
                    await test_channel.send("🔧 Bot permission test - this message can be deleted")
                    print(f"✅ Successfully sent test message to {test_channel.name}")
                except Exception as e:
                    print(f"❌ Failed to send test message: {e}")
            else:
                print("⚠️ No text channels available for message test")

            print()
            print("🎉 Bot permissions and connectivity test completed!")
            await client.close()

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
    asyncio.run(test_bot_permissions())
