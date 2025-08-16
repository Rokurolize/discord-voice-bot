#!/usr/bin/env python3
"""Test Discord voice connection and speaking protocol."""

import asyncio

import discord
from discord.ext import commands

from src.audio_debugger import audio_debugger
from src.config import config


class VoiceConnectionTester(commands.Bot):
    """Bot for testing voice connection and speaking protocol."""

    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!test_", intents=intents)
        self.voice_client = None

    async def on_ready(self):
        print(f"🤖 Bot connected: {self.user}")
        print(f"🎯 Target voice channel ID: {config.target_voice_channel_id}")

        # Get the voice channel
        channel = self.get_channel(config.target_voice_channel_id)
        if not channel:
            print(f"❌ Could not find voice channel with ID {config.target_voice_channel_id}")
            return

        print(f"📻 Found voice channel: {channel.name}")

        # Connect to voice channel
        try:
            print("🔗 Connecting to voice channel...")
            self.voice_client = await channel.connect()
            print(f"✅ Connected to voice channel: {type(self.voice_client)}")

            # Test voice connection properties
            await self.test_voice_connection()

        except Exception as e:
            print(f"❌ Failed to connect to voice channel: {e}")

    async def test_voice_connection(self):
        """Test voice connection and speaking protocol step by step."""
        if not self.voice_client:
            print("❌ No voice client available")
            return

        print("\n🔍 === Voice Connection Analysis ===")

        # 1. Test basic connection properties
        print(f"🔗 Connected: {self.voice_client.is_connected()}")
        print(f"🎤 Playing: {self.voice_client.is_playing()}")
        print(f"⏸️  Paused: {self.voice_client.is_paused()}")

        # 2. Test voice client attributes
        if hasattr(self.voice_client, "ws"):
            print(f"🌐 WebSocket available: {self.voice_client.ws is not None}")
            if self.voice_client.ws:
                print(f"🔌 WebSocket connected: {not self.voice_client.ws.closed}")

        if hasattr(self.voice_client, "socket"):
            print(f"📡 UDP socket available: {self.voice_client.socket is not None}")

        # 3. Test speaking protocol (Critical for Discord audio transmission)
        print("\n🎤 === Testing Speaking Protocol ===")
        try:
            if hasattr(self.voice_client, "ws") and self.voice_client.ws:
                print("📤 Sending speaking state (microphone on)...")
                await self.voice_client.ws.speak(True)
                await asyncio.sleep(1)

                print("📤 Sending speaking state (microphone off)...")
                await self.voice_client.ws.speak(False)
                print("✅ Speaking protocol commands sent successfully")
            else:
                print("❌ No WebSocket available for speaking protocol")

        except Exception as e:
            print(f"❌ Speaking protocol failed: {type(e).__name__} - {e!s}")

        # 4. Test audio playback with our known working test audio
        print("\\n🎵 === Testing Audio Playback ===")
        await self.test_audio_playback()

        # 5. Disconnect after tests
        print("\\n🚪 Disconnecting from voice channel...")
        await self.voice_client.disconnect()
        print("✅ Voice connection test completed")

        # Exit the bot
        await self.close()

    async def test_audio_playback(self):
        """Test actual audio playback through Discord voice client."""
        try:
            # Create test sine wave
            test_audio_path = audio_debugger.create_test_audio(440, 3.0, 48000)
            print(f"📁 Created test audio: {test_audio_path}")

            # Create Discord audio source
            ffmpeg_options = {"options": f"-ar {config.audio_sample_rate} -ac {config.audio_channels} -f s16le"}

            audio_source = discord.FFmpegPCMAudio(str(test_audio_path), **ffmpeg_options)

            print(f"🎵 Created audio source: {type(audio_source)}")

            # Critical: Set speaking state before playing
            if hasattr(self.voice_client, "ws") and self.voice_client.ws:
                print("🎤 Setting speaking state to TRUE before playback...")
                await self.voice_client.ws.speak(True)

            # Play the audio
            print("🎵 Starting audio playback...")
            self.voice_client.play(audio_source)

            # Wait for playback to complete
            while self.voice_client.is_playing():
                print("🎵 Playing...", end="\\r")
                await asyncio.sleep(0.5)

            print("\\n✅ Audio playback completed")

            # Clear speaking state
            if hasattr(self.voice_client, "ws") and self.voice_client.ws:
                print("🎤 Setting speaking state to FALSE after playback...")
                await self.voice_client.ws.speak(False)

        except Exception as e:
            print(f"❌ Audio playback test failed: {type(e).__name__} - {e!s}")
            import traceback

            traceback.print_exc()


async def run_voice_test():
    """Run the voice connection test."""
    print("🧪 Discord Voice Connection & Speaking Protocol Test")
    print("🎯 This test will validate the complete Discord voice pipeline")

    bot = VoiceConnectionTester()

    try:
        await bot.start(config.discord_token)
    except KeyboardInterrupt:
        print("\\n⏹️  Test interrupted by user")
        await bot.close()
    except Exception as e:
        print(f"❌ Test failed: {type(e).__name__} - {e!s}")
        await bot.close()


if __name__ == "__main__":
    asyncio.run(run_voice_test())
