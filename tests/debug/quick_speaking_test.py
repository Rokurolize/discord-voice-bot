#!/usr/bin/env python3
"""Quick test of Discord speaking protocol."""

import asyncio

import discord
from discord.ext import commands

from src.config import config


class QuickVoiceTest(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)
        self.test_completed = False

    async def on_ready(self):
        print(f"🤖 Bot ready: {self.user}")

        # Set a timeout for the entire test
        asyncio.create_task(self.timeout_handler())

        try:
            channel = self.get_channel(config.target_voice_channel_id)
            if not channel:
                print("❌ Voice channel not found")
                self.test_completed = True
                return

            print(f"🎯 Connecting to: {channel.name}")
            voice_client = await channel.connect()
            print("✅ Voice connected")

            # Quick speaking protocol test
            if hasattr(voice_client, "ws") and voice_client.ws:
                print("🎤 Testing speaking protocol...")
                await voice_client.ws.speak(True)
                print("✅ Speaking TRUE sent")
                await asyncio.sleep(1)

                await voice_client.ws.speak(False)
                print("✅ Speaking FALSE sent")

                # Quick audio test
                print("🎵 Testing brief audio playback...")

                # Use a simple audio command instead of file
                from src.audio_debugger import audio_debugger

                test_path = audio_debugger.create_test_audio(800, 1.0, 48000)  # Short 1-second beep

                ffmpeg_options = {"options": "-ar 48000 -ac 2 -f s16le"}
                audio_source = discord.FFmpegPCMAudio(str(test_path), **ffmpeg_options)

                # Critical: Speaking state management
                await voice_client.ws.speak(True)
                voice_client.play(audio_source)

                # Wait briefly then stop
                await asyncio.sleep(2)
                if voice_client.is_playing():
                    voice_client.stop()

                await voice_client.ws.speak(False)
                print("✅ Audio test completed")

            else:
                print("❌ No WebSocket for speaking protocol")

            await voice_client.disconnect()
            print("✅ Disconnected")

        except Exception as e:
            print(f"❌ Error: {type(e).__name__}: {e!s}")

        self.test_completed = True

    async def timeout_handler(self):
        """Force exit if test takes too long."""
        await asyncio.sleep(30)  # 30 second timeout
        if not self.test_completed:
            print("⏱️  Test timeout - force closing")
            await self.close()


async def main():
    print("🚀 Quick Discord Speaking Protocol Test (30s timeout)")
    bot = QuickVoiceTest()

    try:
        await bot.start(config.discord_token)
    except Exception as e:
        print(f"Test error: {e}")
    finally:
        if not bot.is_closed():
            await bot.close()


if __name__ == "__main__":
    asyncio.run(main())
