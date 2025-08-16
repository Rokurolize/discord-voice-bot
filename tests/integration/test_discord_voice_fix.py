#!/usr/bin/env python3
"""Test the voice fix directly in Discord with new speaker."""

import asyncio

import discord
from discord.ext import commands

from src.config import config
from src.tts_engine import tts_engine


class VoiceFixTester(commands.Bot):
    """Bot for testing voice fix in Discord."""

    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!voice_test_", intents=intents)
        self.test_completed = False

    async def on_ready(self):
        print(f"🤖 Voice fix tester ready: {self.user}")

        # Set timeout
        asyncio.create_task(self.timeout_handler())

        try:
            # Connect to voice channel
            channel = self.get_channel(config.target_voice_channel_id)
            if not channel:
                print("❌ Voice channel not found")
                self.test_completed = True
                return

            print(f"🎯 Connecting to: {channel.name}")
            voice_client = await channel.connect()
            print("✅ Voice connected")

            # Test with both speakers for comparison
            await tts_engine.start()

            await self.test_voice_comparison(voice_client)

            await voice_client.disconnect()
            print("✅ Voice fix test completed")

        except Exception as e:
            print(f"❌ Error: {type(e).__name__}: {e!s}")

        self.test_completed = True

    async def test_voice_comparison(self, voice_client):
        """Test both speaker voices in Discord."""
        print("\\n🧪 === DISCORD VOICE COMPARISON TEST ===")

        test_messages = [
            (
                "高いピッチのテスト：これは従来のあまあまずんだもんの声です。",
                1512153249,
                "zunda_amai (HIGH-PITCHED)",
            ),
            (
                "通常ピッチのテスト：これが新しいノーマルずんだもんの声です。",
                1512153250,
                "zunda_normal (NORMAL PITCH)",
            ),
        ]

        for i, (message, speaker_id, description) in enumerate(test_messages, 1):
            print(f"\\n🎤 Test {i}/2: {description}")
            print(f"📝 Message: {message}")

            try:
                # Create audio with specific speaker ID
                audio_source = await tts_engine.create_audio_source(message, speaker_id)

                if audio_source:
                    print(f"✅ Audio created with speaker ID {speaker_id}")

                    # Set speaking state
                    if hasattr(voice_client, "ws") and voice_client.ws:
                        await voice_client.ws.speak(True)

                    # Play audio
                    voice_client.play(audio_source)
                    print("🎵 Playing in Discord... Listen for the difference!")

                    # Wait for completion
                    start_time = asyncio.get_event_loop().time()
                    while voice_client.is_playing():
                        await asyncio.sleep(0.1)

                    duration = asyncio.get_event_loop().time() - start_time
                    print(f"✅ Playback completed ({duration:.1f}s)")

                    # Clear speaking state
                    if hasattr(voice_client, "ws") and voice_client.ws:
                        await voice_client.ws.speak(False)

                    # Cleanup
                    tts_engine.cleanup_audio_source(audio_source)

                    # Wait between tests
                    if i < len(test_messages):
                        print("⏳ Waiting 3 seconds before next test...")
                        await asyncio.sleep(3)

                else:
                    print(f"❌ Failed to create audio with speaker {speaker_id}")

            except Exception as e:
                print(f"❌ Test {i} failed: {type(e).__name__}: {e!s}")

        print("\\n🎯 Voice comparison completed!")
        print("🔊 You should have heard two different voice pitches:")
        print('   1. High-pitched "amai" voice (old setting)')
        print('   2. Normal-pitched "normal" voice (new setting)')
        print("\\n📊 If the second voice sounded more natural, the fix worked!")

    async def timeout_handler(self):
        """Force exit after timeout."""
        await asyncio.sleep(30)
        if not self.test_completed:
            print("⏱️  Voice fix test timeout - closing")
            await self.close()


async def main():
    """Run voice fix test in Discord."""
    print("🎤 DISCORD VOICE FIX TEST")
    print("🎯 This will play both high-pitched and normal voices in Discord")
    print("🔊 Listen carefully to hear the difference!\\n")

    bot = VoiceFixTester()

    try:
        await bot.start(config.discord_token)
    except Exception as e:
        print(f"Test error: {e}")
    finally:
        if not bot.is_closed():
            await bot.close()

        await tts_engine.close()


if __name__ == "__main__":
    asyncio.run(main())
