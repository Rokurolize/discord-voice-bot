#!/usr/bin/env python3
"""Test Discord audio playback mechanism with known working audio."""

import asyncio

import discord

from src.audio_debugger import audio_debugger
from src.config import config


async def test_discord_audio_playback():
    """Test Discord FFmpegPCMAudio with sine wave audio."""
    print("🎵 Testing Discord Audio Playback Mechanism...")

    # Create a test sine wave
    test_audio_path = audio_debugger.create_test_audio(440, 2.0, 48000)
    print(f"📁 Test audio created: {test_audio_path}")

    # Test Discord FFmpegPCMAudio creation
    try:
        ffmpeg_options = {"options": f"-ar {config.audio_sample_rate} -ac {config.audio_channels} -f s16le"}

        print(f"⚙️  FFmpeg options: {ffmpeg_options}")

        # Create Discord audio source
        audio_source = discord.FFmpegPCMAudio(str(test_audio_path), **ffmpeg_options)

        print(f"✅ Successfully created Discord audio source: {type(audio_source)}")
        print(f'🎯 Audio source title: {getattr(audio_source, "title", "Unknown")}')

        # Test if we can read some data from the source
        try:
            # Read a small chunk to verify the source works
            data_chunk = audio_source.read()
            if data_chunk:
                print(f"✅ Successfully read {len(data_chunk)} bytes from audio source")
                print("🎵 Discord audio pipeline is functional!")

                # Save the read data for analysis
                debug_chunk_path = audio_debugger.save_audio_stage(
                    data_chunk,
                    "discord_read_test",
                    "sine wave chunk",
                    {"source_type": "discord_ffmpeg", "chunk_size": len(data_chunk)},
                )
                print(f"🔍 Saved read chunk for analysis: {debug_chunk_path}")

            else:
                print("⚠️  No data read from audio source")

        except Exception as read_error:
            print(f"❌ Failed to read from audio source: {read_error}")

        # Clean up the source
        if hasattr(audio_source, "cleanup"):
            audio_source.cleanup()

        return True

    except Exception as e:
        print(f"❌ Failed to create Discord audio source: {type(e).__name__} - {e!s}")
        return False


if __name__ == "__main__":
    print("🧪 Discord Audio Playback Test")
    success = asyncio.run(test_discord_audio_playback())
    print(f"🎯 Test result: {'✅ PASSED' if success else '❌ FAILED'}")
