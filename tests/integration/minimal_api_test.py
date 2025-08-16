#!/usr/bin/env python3
"""Minimal AivisSpeech API test to isolate high-pitch issue."""

import asyncio
import json
import urllib.parse
from pathlib import Path

import aiohttp

# Direct AivisSpeech API configuration
API_URL = "http://127.0.0.1:10101"
OUTPUT_DIR = Path("/tmp/minimal_pitch_test")

# Test configurations
TEST_CONFIGS = [
    # Zundamon tests with different pitch scales
    {"speaker": 1512153249, "pitchScale": 0.0, "name": "zunda_amai_pitch_0.0_raw"},
    {
        "speaker": 1512153249,
        "pitchScale": 0.65,
        "name": "zunda_amai_pitch_0.65_reduced",
    },
    {
        "speaker": 1512153249,
        "pitchScale": 0.3,
        "name": "zunda_amai_pitch_0.3_aggressive",
    },
    {"speaker": 1512153250, "pitchScale": 0.0, "name": "zunda_normal_pitch_0.0_raw"},
    {
        "speaker": 1512153250,
        "pitchScale": 0.65,
        "name": "zunda_normal_pitch_0.65_reduced",
    },
    # Non-Zundamon for comparison
    {"speaker": 888753760, "pitchScale": 0.0, "name": "anneli_normal_pitch_0.0_raw"},
    {
        "speaker": 888753760,
        "pitchScale": 0.85,
        "name": "anneli_normal_pitch_0.85_reduced",
    },
]


async def direct_api_call(text: str, speaker: int, pitch_scale: float) -> bytes:
    """Make direct API call to AivisSpeech, bypassing all our existing code."""
    async with aiohttp.ClientSession() as session:
        # Step 1: Generate audio_query
        params = {"text": text, "speaker": speaker}
        query_url = f"{API_URL}/audio_query?" + urllib.parse.urlencode(params)

        print(f"  📡 Calling audio_query: speaker={speaker}")
        async with session.post(query_url) as response:
            if response.status != 200:
                raise Exception(f"Audio query failed: {response.status}")
            audio_query = await response.json()

        # Step 2: Modify pitch if requested
        if pitch_scale != 0.0:
            audio_query["pitchScale"] = pitch_scale
            print(f"  🔧 Modified pitchScale to {pitch_scale}")
        else:
            print(f"  📊 Using raw pitchScale: {audio_query.get('pitchScale', 'NOT_SET')}")

        # Ensure 48kHz output
        audio_query["outputSamplingRate"] = 48000

        # Step 3: Synthesize audio
        synthesis_params = {"speaker": speaker}
        synthesis_url = f"{API_URL}/synthesis?" + urllib.parse.urlencode(synthesis_params)

        headers = {"Content-Type": "application/json"}
        data = json.dumps(audio_query).encode("utf-8")

        print("  🎵 Synthesizing audio...")
        async with session.post(synthesis_url, data=data, headers=headers) as response:
            if response.status != 200:
                raise Exception(f"Synthesis failed: {response.status}")
            return await response.read()


async def run_minimal_tests():
    """Run minimal API tests to isolate pitch issues."""
    print("🧪 MINIMAL AIVISPEECH API PITCH TEST")
    print("🎯 Testing raw API calls to isolate high-pitch issue\n")

    test_text = "ピッチテスト：この音声の高さを確認してください。"
    generated_files = []

    OUTPUT_DIR.mkdir(exist_ok=True)

    for i, config in enumerate(TEST_CONFIGS, 1):
        speaker = config["speaker"]
        pitch_scale = config["pitchScale"]
        file_name = config["name"]

        print(f"🎤 Test {i}/{len(TEST_CONFIGS)}: {file_name}")

        try:
            # Make direct API call
            audio_data = await direct_api_call(test_text, speaker, pitch_scale)

            # Save audio file
            output_path = OUTPUT_DIR / f"{file_name}.wav"
            with open(output_path, "wb") as f:
                f.write(audio_data)

            file_size = len(audio_data)
            print(f"  ✅ Generated: {output_path} ({file_size} bytes)")
            generated_files.append(str(output_path))

        except Exception as e:
            print(f"  ❌ Failed: {type(e).__name__}: {e!s}")

    print("\n📊 MINIMAL TEST RESULTS:")
    print(f"   Output directory: {OUTPUT_DIR}")
    print(f"   Files generated: {len(generated_files)}")

    print("\n📁 Generated audio files:")
    for file_path in generated_files:
        print(f"   {file_path}")

    print("\n🔍 ANALYSIS INSTRUCTIONS:")
    print("   Listen to each file to identify which parameters affect pitch:")
    print("   - Files with '_pitch_0.0_' show raw AivisSpeech output")
    print("   - Files with '_pitch_0.65_' show our current correction")
    print("   - Files with '_pitch_0.3_' show aggressive correction")
    print("   - Compare Zundamon vs Anneli speakers")

    print("\n🎯 KEY FILES TO CHECK:")
    key_files = [f for f in generated_files if "raw" in f or "aggressive" in f]
    for file_path in key_files:
        print(f"   {file_path}")


if __name__ == "__main__":
    asyncio.run(run_minimal_tests())
