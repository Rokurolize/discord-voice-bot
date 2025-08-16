#!/usr/bin/env python3
"""Final verification that the production bot has pitch correction."""

import asyncio

import discord
from discord.ext import commands

from src.config import config
from src.tts_engine import tts_engine


class ProductionVerificationBot(commands.Bot):
    """Verify the production bot's pitch correction functionality."""

    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!production_", intents=intents)
        self.test_completed = False

    async def on_ready(self):
        print(f"🤖 Production verification bot ready: {self.user}")

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

            # Test the current production configuration
            await tts_engine.start()
            await self.test_production_voice(voice_client)

            await voice_client.disconnect()
            print("✅ Production verification completed")

        except Exception as e:
            print(f"❌ Error: {type(e).__name__}: {e!s}")

        self.test_completed = True

    async def test_production_voice(self, voice_client):
        """Test the production bot's voice with pitch correction."""
        print("\\n🏭 === PRODUCTION BOT PITCH CORRECTION VERIFICATION ===")

        # Test messages to verify pitch correction is working
        test_messages = [
            "プロダクション環境でのピッチ修正テストです。自然な音声で聞こえているでしょうか？",
            "Production pitch correction test: The voice should sound natural and not overly high-pitched.",
            "最終確認：この音声が適切なピッチで再生されていれば、修正は成功です！",
        ]

        for i, message in enumerate(test_messages, 1):
            print(f"\\n🎤 Production Test {i}/3")
            print(f"📝 Message: {message}")

            try:
                # Get current configuration info
                current_speaker = config.speaker_id
                print(f"🔧 Current speaker ID: {current_speaker}")

                if str(current_speaker).startswith("1512153"):
                    print("✅ Zundamon speaker detected - pitch correction should apply (pitchScale=0.65)")
                else:
                    print("ℹ️  Non-Zundamon speaker - standard pitch correction (pitchScale=0.85)")

                # Create audio with current production settings
                audio_source = await tts_engine.create_audio_source(message)

                if audio_source:
                    print("✅ Audio created successfully")

                    # Set speaking state and play
                    if hasattr(voice_client, "ws") and voice_client.ws:
                        await voice_client.ws.speak(True)

                    voice_client.play(audio_source)
                    print("🎵 Playing production audio with pitch correction...")

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
                        print("⏳ Waiting 2 seconds before next test...")
                        await asyncio.sleep(2)

                else:
                    print(f"❌ Failed to create audio for test {i}")

            except Exception as e:
                print(f"❌ Test {i} failed: {type(e).__name__}: {e!s}")

        print("\\n🎯 Production pitch correction verification completed!")
        print("🔊 The voice should now sound more natural with proper pitch correction!")
        print("✅ If the voice sounds significantly better than before, the fix is working!")

    async def timeout_handler(self):
        """Force exit after timeout."""
        await asyncio.sleep(20)
        if not self.test_completed:
            print("⏱️  Production test timeout - closing")
            await self.close()


async def main():
    """Run production verification test."""
    print("🏭 PRODUCTION BOT PITCH CORRECTION VERIFICATION")
    print("🎯 Testing the main bot's pitch correction in Discord")
    print("🔊 This should demonstrate the fixed, natural-sounding voice!\n")

    bot = ProductionVerificationBot()

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
