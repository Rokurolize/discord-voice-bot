#!/usr/bin/env python3
"""Final end-to-end test with complete AivisSpeech → Discord pipeline."""

import asyncio

import discord
from discord.ext import commands

from src.audio_debugger import audio_debugger
from src.config import config
from src.message_processor import message_processor
from src.tts_engine import tts_engine


class EndToEndTester(commands.Bot):
    """Complete end-to-end pipeline tester."""

    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!final_", intents=intents)
        self.test_completed = False

    async def on_ready(self):
        print(f"🤖 Final test bot ready: {self.user}")

        # Set timeout
        asyncio.create_task(self.timeout_handler())

        try:
            # 1. Connect to voice channel
            channel = self.get_channel(config.target_voice_channel_id)
            if not channel:
                print("❌ Voice channel not found")
                self.test_completed = True
                return

            print(f"🎯 Connecting to: {channel.name}")
            voice_client = await channel.connect()
            print("✅ Voice connected")

            # 2. Test AivisSpeech TTS availability
            await tts_engine.start()
            is_available, error_detail = await tts_engine.check_api_availability()

            if not is_available:
                print(f"❌ AivisSpeech not available: {error_detail}")
                print("🔄 Testing with backup audio instead...")
                await self.test_backup_audio(voice_client)
            else:
                print("✅ AivisSpeech available")
                await self.test_complete_pipeline(voice_client)

            await voice_client.disconnect()
            print("✅ Test completed")

        except Exception as e:
            print(f"❌ Error: {type(e).__name__}: {e!s}")

        self.test_completed = True

    async def test_complete_pipeline(self, voice_client):
        """Test complete TTS pipeline with AivisSpeech."""
        print("\\n🧪 === COMPLETE AIVISPEECH → DISCORD PIPELINE TEST ===")

        # Test messages
        test_messages = [
            "最終テストです！これが聞こえれば、AivisSpeechからDiscordまでの全パイプラインが正常に動作しています！",
            "Second test: English text mixed with 日本語 should work perfectly.",
            "最後のテスト：ずんだもんの声で読み上げられているはずです。",
        ]

        for i, test_message in enumerate(test_messages, 1):
            print(f"\\n🎤 Test {i}/3: {test_message[:50]}...")

            try:
                # Process message
                processed_text = message_processor.process_message_content(test_message, f"FinalTest{i}")
                print(f"📝 Processed: {processed_text[:50]}...")

                # Create audio source via complete TTS pipeline
                audio_source = await tts_engine.create_audio_source(processed_text)

                if audio_source:
                    print("✅ TTS audio source created")

                    # Set speaking state
                    if hasattr(voice_client, "ws") and voice_client.ws:
                        await voice_client.ws.speak(True)

                    # Play audio
                    voice_client.play(audio_source)
                    print("🎵 Playing audio...")

                    # Wait for completion
                    start_time = asyncio.get_event_loop().time()
                    while voice_client.is_playing():
                        await asyncio.sleep(0.1)

                    duration = asyncio.get_event_loop().time() - start_time
                    print(f"✅ Audio completed ({duration:.1f}s)")

                    # Clear speaking state
                    if hasattr(voice_client, "ws") and voice_client.ws:
                        await voice_client.ws.speak(False)

                    # Cleanup
                    tts_engine.cleanup_audio_source(audio_source)

                    # Wait between messages
                    if i < len(test_messages):
                        print("⏳ Waiting 2 seconds before next test...")
                        await asyncio.sleep(2)

                else:
                    print("❌ Failed to create audio source")

            except Exception as e:
                print(f"❌ Test {i} failed: {type(e).__name__}: {e!s}")

        print("\\n✅ Complete pipeline test finished!")
        print("🎯 All audio should have been audible in Discord voice channel")

        # Generate final report
        summary = audio_debugger.get_session_summary()
        print("\\n📊 Debug Summary:")
        print(f'   Session: {summary["session_id"]}')
        print(f'   Files saved: {summary["total_files"]}')
        print(f'   Stages tested: {", ".join(summary["stages_tested"])}')
        print(f'   Debug directory: {summary["session_dir"]}')

    async def test_backup_audio(self, voice_client):
        """Test with backup sine wave if AivisSpeech unavailable."""
        print("\\n🔄 === BACKUP AUDIO TEST (AivisSpeech unavailable) ===")

        # Create test sine wave
        test_path = audio_debugger.create_test_audio(440, 3.0, 48000)
        print(f"📁 Created backup audio: {test_path}")

        # Create Discord audio source
        ffmpeg_options = {"options": "-ar 48000 -ac 2 -f s16le"}
        audio_source = discord.FFmpegPCMAudio(str(test_path), **ffmpeg_options)

        # Play test audio
        if hasattr(voice_client, "ws") and voice_client.ws:
            await voice_client.ws.speak(True)

        voice_client.play(audio_source)
        print("🎵 Playing backup audio...")

        while voice_client.is_playing():
            await asyncio.sleep(0.1)

        if hasattr(voice_client, "ws") and voice_client.ws:
            await voice_client.ws.speak(False)

        print("✅ Backup audio test completed")
        print("🔧 Note: Start AivisSpeech server and retest for full functionality")

    async def timeout_handler(self):
        """Force exit after timeout."""
        await asyncio.sleep(45)  # 45 second timeout
        if not self.test_completed:
            print("⏱️  Final test timeout - closing")
            await self.close()


async def main():
    """Run final end-to-end test."""
    print("🏁 FINAL END-TO-END PIPELINE TEST")
    print("🎯 This will test the complete AivisSpeech → Discord pipeline")
    print("📢 Listen in Discord voice channel for audio output!\\n")

    bot = EndToEndTester()

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
