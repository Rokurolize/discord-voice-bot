#!/usr/bin/env python3
"""Test edge cases and error handling for the Discord Voice TTS Bot."""

import asyncio
from unittest.mock import Mock

from src.config import config
from src.message_processor import message_processor
from src.tts_engine import tts_engine
from src.voice_handler import VoiceHandler


async def test_tts_engine_robustness():
    """Test TTS engine with various edge cases."""
    print("🧪 Testing TTS Engine Robustness...")

    await tts_engine.start()

    edge_cases = [
        ("", "Empty string"),
        ("a", "Single character"),
        ("A" * 500, "Very long message (500 chars)"),
        ("!@#$%^&*()", "Special characters only"),
        ("🎉🎊✨🌟💫", "Emoji only"),
        ("https://example.com/very/long/url/path", "URL"),
        ("テスト\n改行\nテスト", "Newlines"),
        ("Mix日本語English123!@#", "Mixed content"),
        ("　　　", "Japanese spaces"),
        ("ＡＢＣ１２３", "Full-width characters"),
    ]

    for i, (text, description) in enumerate(edge_cases, 1):
        print(f"\n--- Test {i}: {description} ---")
        print(f'Input: "{text[:50]}{"..." if len(text) > 50 else ""}"')

        try:
            audio_data = await tts_engine.synthesize_audio(text)
            if audio_data:
                print(f"✅ Synthesis successful: {len(audio_data)} bytes")
            else:
                print("⚠️ Synthesis returned None (expected for empty/invalid input)")
        except Exception as e:
            print(f"❌ Synthesis failed: {type(e).__name__} - {e!s}")

    await tts_engine.close()


async def test_message_processor_edge_cases():
    """Test message processor with edge cases."""
    print("\n🧪 Testing Message Processor Edge Cases...")

    class MockMessage:
        def __init__(self, content, user_id=12345):
            self.content = content
            self.author = Mock()
            self.author.id = user_id
            self.author.bot = False
            self.author.display_name = f"User{user_id}"
            self.channel = Mock()
            self.channel.id = config.target_voice_channel_id
            self.type = Mock()
            self.type.name = "default"

    edge_cases = [
        ("", "Empty message"),
        ("   ", "Whitespace only"),
        ("!command", "Command-like message"),
        ("/slash", "Slash command"),
        (".dot", "Dot prefix"),
        (">quote", "Quote prefix"),
        ("<@123456789>", "Mention only"),
        ("**bold** __underline__ ~~strike~~", "Markdown formatting"),
        ("||spoiler||", "Spoiler text"),
        ("`code`", "Inline code"),
        ("```\ncode block\n```", "Code block"),
        ("https://discord.com https://github.com", "Multiple URLs"),
        ("A" * 1000, "Extremely long message"),
    ]

    for i, (content, description) in enumerate(edge_cases, 1):
        print(f"\n--- Message Test {i}: {description} ---")

        mock_msg = MockMessage(content)

        should_process = await message_processor.should_process_message(mock_msg)
        print(f"Should process: {should_process}")

        if should_process:
            processed = message_processor.process_message_content(content, "TestUser")
            print(f'Processed: "{processed}"')
        else:
            print("⏭️ Filtered out")


async def test_rate_limiting():
    """Test rate limiting functionality."""
    print("\n🧪 Testing Rate Limiting...")

    class MockMessage:
        def __init__(self, content, user_id):
            self.content = content
            self.author = Mock()
            self.author.id = user_id
            self.author.bot = False
            self.author.display_name = f"User{user_id}"
            self.channel = Mock()
            self.channel.id = config.target_voice_channel_id
            self.type = Mock()
            self.type.name = "default"

    # Test rate limiting with rapid messages from same user
    user_id = 99999
    for i in range(8):  # Send more than rate limit
        mock_msg = MockMessage(f"Message {i+1}", user_id)
        should_process = await message_processor.should_process_message(mock_msg)
        print(f'Message {i+1}: {"✅ Allowed" if should_process else "❌ Rate limited"}')
        await asyncio.sleep(0.1)  # Small delay


async def test_voice_handler_edge_cases():
    """Test voice handler with mock Discord client."""
    print("\n🧪 Testing Voice Handler Edge Cases...")

    # Mock Discord client
    mock_bot = Mock()
    mock_bot.user = Mock()
    mock_bot.user.id = 12345

    voice_handler = VoiceHandler(mock_bot)

    # Test queue operations
    print("\n--- Queue Management ---")

    # Add items to queue
    success1 = await voice_handler.add_to_queue("Test message 1", "User1")
    success2 = await voice_handler.add_to_queue("", "User2")  # Empty message
    success3 = await voice_handler.add_to_queue("   ", "User3")  # Whitespace only

    print(f'Add valid message: {"✅" if success1 else "❌"}')
    print(f'Add empty message: {"✅" if success2 else "❌"}')
    print(f'Add whitespace message: {"✅" if success3 else "❌"}')

    # Check queue status
    status = voice_handler.get_queue_status()
    print(f'Queue size: {status["queue_size"]}')

    # Test queue clearing
    cleared = voice_handler.clear_queue()
    print(f"Cleared items: {cleared}")

    # Test skip when nothing playing
    skipped = await voice_handler.skip_current()
    print(f'Skip when not playing: {"✅" if not skipped else "❌"}')


async def test_error_scenarios():
    """Test various error scenarios."""
    print("\n🧪 Testing Error Scenarios...")

    # Test TTS engine with invalid API URL
    print("\n--- TTS API Error Handling ---")

    # Save original URL
    original_url = config.api_url

    # Test with invalid URL
    config.api_url = "http://localhost:99999"  # Invalid port

    await tts_engine.start()
    is_available, error = await tts_engine.check_api_availability()
    print(f'Invalid API URL: {"❌" if not is_available else "✅"} Error: {error}')

    # Restore original URL
    config.api_url = original_url
    await tts_engine.close()


if __name__ == "__main__":
    print("🧪 Starting Edge Cases and Error Handling Tests...")

    async def run_all_tests():
        await test_tts_engine_robustness()
        await test_message_processor_edge_cases()
        await test_rate_limiting()
        await test_voice_handler_edge_cases()
        await test_error_scenarios()
        print("\n✅ All edge case tests completed!")

    asyncio.run(run_all_tests())
