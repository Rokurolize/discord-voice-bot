#!/usr/bin/env python3
"""Test pitch-corrected voices in Discord."""

import asyncio

import discord
from discord.ext import commands

from src.config import config
from src.tts_engine import tts_engine


class PitchFixDiscordTester(commands.Bot):
    """Test pitch fix in Discord voice channel."""

    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!pitch_", intents=intents)
        self.test_completed = False

    async def on_ready(self):
        print(f"🤖 Pitch fix Discord tester ready: {self.user}")

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

            # Test pitch-corrected voices
            await tts_engine.start()
            await self.test_pitch_corrected_voices(voice_client)

            await voice_client.disconnect()
            print("✅ Pitch correction Discord test completed")

        except Exception as e:
            print(f"❌ Error: {type(e).__name__}: {e!s}")

        self.test_completed = True

    async def test_pitch_corrected_voices(self, voice_client):
        """Test pitch-corrected Zundamon voices in Discord."""
        print("\\n🎵 === DISCORD PITCH CORRECTION TEST ===")

        # Test the most commonly used Zundamon voices
        test_cases = [
            (
                1512153250,
                "zunda_normal",
                "ピッチ修正後の通常ずんだもん：自然な高さで話しています。",
            ),
            (
                1512153249,
                "zunda_amai",
                "ピッチ修正後のあまあまずんだもん：高すぎない声になったはずです。",
            ),
            (
                888753760,
                "anneli_normal",
                "比較用のアネリ：ずんだもんとは違うピッチ調整です。",
            ),
        ]

        for i, (speaker_id, speaker_name, message) in enumerate(test_cases, 1):
            print(f"\\n🎤 Test {i}/3: {speaker_name} (ID: {speaker_id})")
            print(f"📝 Message: {message}")

            try:
                # Create pitch-corrected audio
                audio_source = await tts_engine.create_audio_source(message, speaker_id)

                if audio_source:
                    if str(speaker_id).startswith("1512153"):
                        print("🔧 Applied Zundamon pitch correction (pitchScale=0.65)")
                    else:
                        print("🔧 Applied standard pitch correction (pitchScale=0.85)")

                    # Set speaking state and play
                    if hasattr(voice_client, "ws") and voice_client.ws:
                        await voice_client.ws.speak(True)

                    voice_client.play(audio_source)
                    print("🎵 Playing pitch-corrected voice in Discord...")

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
                    if i < len(test_cases):
                        print("⏳ Waiting 2 seconds before next test...")
                        await asyncio.sleep(2)

                else:
                    print(f"❌ Failed to create audio for {speaker_name}")

            except Exception as e:
                print(f"❌ Test {i} failed: {type(e).__name__}: {e!s}")

        print("\\n🎯 Pitch correction Discord test completed!")
        print("🔊 Did the Zundamon voices sound more natural and less high-pitched?")
        print("📊 The fix should have made a noticeable difference in voice quality!")

    async def timeout_handler(self):
        """Force exit after timeout."""
        await asyncio.sleep(25)
        if not self.test_completed:
            print("⏱️  Pitch fix test timeout - closing")
            await self.close()


async def main():
    """Run pitch correction Discord test."""
    print("🎤 DISCORD PITCH CORRECTION TEST")
    print("🎯 Testing pitch-corrected Zundamon voices in Discord")
    print("🔊 Listen for lower, more natural sounding voices!\\n")

    bot = PitchFixDiscordTester()

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
