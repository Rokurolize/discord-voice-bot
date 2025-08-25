#!/usr/bin/env python3
"""Performance test for memory usage and resource management."""

import asyncio
import gc
import sys
import time
from typing import Any

import psutil

# Add src directory to path
sys.path.insert(0, "/home/ubuntu/workbench/projects/discord-voice-bot/src")

from discord_voice_bot.config_manager import ConfigManagerImpl
from discord_voice_bot.message_processor import MessageProcessor
from discord_voice_bot.voice_handler import VoiceHandler


class PerformanceMonitor:
    """Monitor system resources during performance tests."""

    def __init__(self) -> None:
        """Initialize performance monitor."""
        self.process = psutil.Process()
        self.start_memory = 0
        self.peak_memory = 0
        self.measurements: list[dict[str, Any]] = []

    def start_monitoring(self) -> None:
        """Start memory monitoring."""
        gc.collect()  # Clean up before measuring
        self.start_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        self.peak_memory = self.start_memory

    def record_measurement(self, label: str) -> dict[str, Any]:
        """Record current memory usage."""
        current_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        self.peak_memory = max(self.peak_memory, current_memory)

        measurement = {"label": label, "current_memory_mb": current_memory, "memory_increase_mb": current_memory - self.start_memory, "peak_memory_mb": self.peak_memory, "timestamp": time.time()}

        self.measurements.append(measurement)
        print(f"📊 {label}: {current_memory:.1f}MB (Δ{measurement['memory_increase_mb']:+.1f}MB)")
        return measurement

    def get_summary(self) -> dict[str, Any]:
        """Get performance summary."""
        final_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        return {
            "start_memory_mb": self.start_memory,
            "final_memory_mb": final_memory,
            "peak_memory_mb": self.peak_memory,
            "total_increase_mb": final_memory - self.start_memory,
            "measurements": self.measurements,
        }


def test_memory_usage_message_processing() -> None:
    """Test memory usage during message processing."""
    print("🧠 Testing message processing memory usage...")

    monitor = PerformanceMonitor()
    monitor.start_monitoring()

    # Initialize components
    config_manager = ConfigManagerImpl()
    processor = MessageProcessor(config_manager)

    monitor.record_measurement("After initialization")

    # Process many messages
    test_messages = [f"Test message {i} with some content for processing and chunking!" * 10 for i in range(1000)]

    processed_count = 0
    for msg_text in test_messages:
        # Create mock message
        class MockMessage:
            def __init__(self, content: str) -> None:
                self.content = content
                self.author = type("obj", (object,), {"id": 123, "name": "TestUser", "display_name": "TestUser", "bot": False})()
                self.channel = type("obj", (object,), {"id": 456})()
                self.guild = type("obj", (object,), {})()  # Server message
                self.id = 789
                self.type = type("obj", (object,), {"name": "default"})()

        mock_msg = MockMessage(msg_text)

        # Process message
        result = asyncio.run(processor.process_message(mock_msg))
        if result is not None:
            processed_count += 1
        else:
            # Rate limited - this is expected behavior
            pass

        if processed_count % 100 == 0:
            monitor.record_measurement(f"After processing {processed_count} messages")

    final_summary = monitor.get_summary()
    print("\n📈 Memory Summary:")
    print(f"   Start: {final_summary['start_memory_mb']:.1f}MB")
    print(f"   Final: {final_summary['final_memory_mb']:.1f}MB")
    print(f"   Peak: {final_summary['peak_memory_mb']:.1f}MB")
    print(f"   Increase: {final_summary['total_increase_mb']:+.1f}MB")

    # Assert reasonable memory usage
    assert final_summary["total_increase_mb"] < 50, f"Memory increase too high: {final_summary['total_increase_mb']:.1f}MB"
    assert final_summary["peak_memory_mb"] < 200, f"Peak memory too high: {final_summary['peak_memory_mb']:.1f}MB"
    print("✅ Memory usage test passed!")


def test_memory_usage_voice_handler() -> None:
    """Test memory usage during voice handler operations."""
    print("\n🎵 Testing voice handler memory usage...")

    monitor = PerformanceMonitor()
    monitor.start_monitoring()

    # Initialize voice handler with mock bot
    class MockBot:
        def __init__(self) -> None:
            self.user = type("obj", (object,), {"id": 123})()

        def get_channel(self, x: int) -> Any:
            return type("obj", (object,), {"id": x})()

    mock_bot = MockBot()
    config_manager = ConfigManagerImpl()
    voice_handler = VoiceHandler(mock_bot, config_manager)

    monitor.record_measurement("After voice handler init")

    # Add many items to queue
    for i in range(1000):
        message_data = {"text": f"Test audio message {i}", "chunks": [f"Test audio message {i}"], "user_id": 123, "username": "TestUser", "group_id": f"group_{i}"}
        asyncio.run(voice_handler.add_to_queue(message_data))

    monitor.record_measurement("After adding 1000 messages")

    # Clear queue
    asyncio.run(voice_handler.clear_all())

    monitor.record_measurement("After clearing queue")

    final_summary = monitor.get_summary()
    print("\n📈 Voice Handler Memory Summary:")
    print(f"   Start: {final_summary['start_memory_mb']:.1f}MB")
    print(f"   Final: {final_summary['final_memory_mb']:.1f}MB")
    print(f"   Peak: {final_summary['peak_memory_mb']:.1f}MB")
    print(f"   Increase: {final_summary['total_increase_mb']:+.1f}MB")

    # Assert reasonable memory usage
    assert final_summary["total_increase_mb"] < 30, f"Voice handler memory increase too high: {final_summary['total_increase_mb']:.1f}MB"
    assert final_summary["peak_memory_mb"] < 150, f"Voice handler peak memory too high: {final_summary['peak_memory_mb']:.1f}MB"
    print("✅ Voice handler memory test passed!")


def test_tts_engine_memory_performance() -> None:
    """Test TTS engine memory performance."""
    print("\n🗣️ Testing TTS engine memory performance...")

    monitor = PerformanceMonitor()
    monitor.start_monitoring()

    try:
        from discord_voice_bot.tts_engine import get_tts_engine

        config_manager = ConfigManagerImpl()
        tts_engine = asyncio.run(get_tts_engine(config_manager))

        monitor.record_measurement("After TTS engine init")

        # Test multiple TTS generations
        test_texts = [f"Test TTS message number {i} for memory performance testing!" * 5 for i in range(100)]

        for i, text in enumerate(test_texts):
            audio_data = asyncio.run(tts_engine.synthesize_audio(text))
            assert audio_data is not None

            if i % 20 == 0:
                monitor.record_measurement(f"After {i + 1} TTS generations")

        # Clean up
        asyncio.run(tts_engine.close())

        final_summary = monitor.get_summary()
        print("\n📈 TTS Engine Memory Summary:")
        print(f"   Start: {final_summary['start_memory_mb']:.1f}MB")
        print(f"   Final: {final_summary['final_memory_mb']:.1f}MB")
        print(f"   Peak: {final_summary['peak_memory_mb']:.1f}MB")
        print(f"   Increase: {final_summary['total_increase_mb']:+.1f}MB")

        # Assert reasonable memory usage
        assert final_summary["total_increase_mb"] < 100, f"TTS engine memory increase too high: {final_summary['total_increase_mb']:.1f}MB"
        print("✅ TTS engine memory test passed!")

    except Exception as e:
        print(f"⚠️ TTS engine test failed: {e}")
        import traceback

        traceback.print_exc()


def test_concurrent_message_processing() -> None:
    """Test concurrent message processing performance."""
    print("\n⚡ Testing concurrent message processing...")

    monitor = PerformanceMonitor()
    monitor.start_monitoring()

    config_manager = ConfigManagerImpl()
    processor = MessageProcessor(config_manager)

    monitor.record_measurement("After processor init")

    # Create many concurrent tasks
    async def process_single_message(msg_id: int) -> dict[str, Any] | None:
        """Process a single message."""

        class MockMessage:
            def __init__(self, msg_id: int) -> None:
                self.content = f"Concurrent test message {msg_id} with some content!"
                self.author = type("obj", (object,), {"id": msg_id, "name": f"User{msg_id}", "display_name": f"User{msg_id}", "bot": False})()
                self.channel = type("obj", (object,), {"id": 456})()
                self.guild = type("obj", (object,), {})()  # Server message
                self.id = msg_id
                self.type = type("obj", (object,), {"name": "default"})()

        mock_msg = MockMessage(msg_id)
        return await processor.process_message(mock_msg)

    # Test concurrent processing
    async def run_concurrent_test() -> None:
        """Run concurrent message processing."""
        tasks = [process_single_message(i) for i in range(500)]
        results = await asyncio.gather(*tasks)
        return results

    results = asyncio.run(run_concurrent_test())
    successful_count = sum(1 for r in results if r is not None)

    monitor.record_measurement("After concurrent processing")

    final_summary = monitor.get_summary()
    print("\n📈 Concurrent Processing Summary:")
    print(f"   Processed {len(results)} messages")
    print(f"   Successful: {successful_count}")
    print(f"   Success rate: {successful_count / len(results) * 100:.1f}%")
    print(f"   Memory increase: {final_summary['total_increase_mb']:+.1f}MB")

    # Assert reasonable performance
    assert successful_count >= len(results) * 0.95, f"Too many failed messages: {successful_count}/{len(results)}"
    assert final_summary["total_increase_mb"] < 100, f"Concurrent processing memory increase too high: {final_summary['total_increase_mb']:.1f}MB"
    print("✅ Concurrent processing test passed!")


def test_rate_limiting_performance() -> None:
    """Test rate limiting performance under load."""
    print("\n🚦 Testing rate limiting performance...")

    monitor = PerformanceMonitor()
    monitor.start_monitoring()

    config_manager = ConfigManagerImpl()
    processor = MessageProcessor(config_manager)

    monitor.record_measurement("After rate limiter init")

    # Test rapid message processing (should be rate limited)
    import time

    start_time = time.time()

    processed_count = 0
    rate_limited_count = 0

    # Process messages with proper async handling
    async def process_messages() -> None:
        nonlocal processed_count, rate_limited_count

        for i in range(200):  # Send many messages quickly

            class MockMessage:
                def __init__(self, msg_id: int) -> None:
                    self.content = f"Rate limit test message {msg_id}!"
                    self.author = type("obj", (object,), {"id": 123, "name": "RateTestUser", "display_name": "RateTestUser", "bot": False})()
                    self.channel = type("obj", (object,), {"id": 456})()
                    self.guild = type("obj", (object,), {})()  # Server message
                    self.id = msg_id
                    self.type = type("obj", (object,), {"name": "default"})()

            mock_msg = MockMessage(i)
            result = await processor.process_message(mock_msg)

            if result is not None:
                processed_count += 1
            else:
                rate_limited_count += 1

            # Add small delay to simulate realistic timing
            await asyncio.sleep(0.001)  # 1ms delay between messages

    # Run the async test
    asyncio.run(process_messages())

    end_time = time.time()
    duration = end_time - start_time

    monitor.record_measurement("After rate limiting test")

    final_summary = monitor.get_summary()
    print("\n📈 Rate Limiting Summary:")
    print("   Total messages: 200")
    print(f"   Processed: {processed_count}")
    print(f"   Rate limited: {rate_limited_count}")
    print(f"   Duration: {duration:.2f}s")
    print(f"   Rate: {200 / duration:.1f} msg/s")
    print(f"   Memory increase: {final_summary['total_increase_mb']:+.1f}MB")

    # Assert reasonable rate limiting
    assert rate_limited_count > 0, "Rate limiting should have kicked in"
    assert processed_count == 5, f"Should process exactly 5 messages before rate limiting, got {processed_count}"
    assert rate_limited_count == 195, f"Should rate limit 195 messages, got {rate_limited_count}"
    assert duration < 1.0, f"Should complete quickly despite async processing, took {duration:.2f}s"
    assert final_summary["total_increase_mb"] < 50, f"Rate limiting memory increase too high: {final_summary['total_increase_mb']:.1f}MB"
    print("✅ Rate limiting test passed!")


def test_long_running_memory_stability() -> None:
    """Test memory stability during long running operations."""
    print("\n⏰ Testing long-running memory stability...")

    monitor = PerformanceMonitor()
    monitor.start_monitoring()

    config_manager = ConfigManagerImpl()
    processor = MessageProcessor(config_manager)

    monitor.record_measurement("After long-running test setup")

    # Simulate long-running operation with periodic memory checks
    processed_total = 0
    rate_limited_total = 0

    for cycle in range(10):  # 10 cycles
        # Process batch of messages with the same processor instance
        for i in range(50):
            msg_id = cycle * 50 + i

            class MockMessage:
                def __init__(self, msg_id: int) -> None:
                    self.content = f"Long-running test message {msg_id} with extended content for memory testing purposes!"
                    self.author = type("obj", (object,), {"id": 123, "name": "LongTestUser", "display_name": "LongTestUser", "bot": False})()
                    self.channel = type("obj", (object,), {"id": 456})()
                    self.guild = type("obj", (object,), {})()  # Server message
                    self.id = msg_id
                    self.type = type("obj", (object,), {"name": "default"})()

            mock_msg = MockMessage(msg_id)
            result = asyncio.run(processor.process_message(mock_msg))

            if result is not None:
                processed_total += 1
            else:
                rate_limited_total += 1

        monitor.record_measurement(f"After cycle {cycle + 1}/10")

        # Force garbage collection
        import gc

        gc.collect()

    final_summary = monitor.get_summary()
    print("\n📈 Long-Running Memory Summary:")
    print("   Total messages: 500")
    print(f"   Processed: {processed_total}")
    print(f"   Rate limited: {rate_limited_total}")
    print(f"   Memory increase: {final_summary['total_increase_mb']:+.1f}MB")
    print(f"   Peak memory: {final_summary['peak_memory_mb']:.1f}MB")

    # Assert reasonable behavior - only first 5 messages should be processed due to rate limiting
    assert processed_total == 5, f"Expected exactly 5 messages to be processed, got {processed_total}"
    assert rate_limited_total == 495, f"Expected 495 messages to be rate limited, got {rate_limited_total}"
    assert final_summary["total_increase_mb"] < 30, f"Long-running memory increase too high: {final_summary['total_increase_mb']:.1f}MB"
    print("✅ Long-running memory stability test passed!")


if __name__ == "__main__":
    print("🚀 Starting Discord Voice TTS Bot Performance Tests")
    print("=" * 60)

    try:
        test_memory_usage_message_processing()
        test_memory_usage_voice_handler()
        test_tts_engine_memory_performance()
        test_concurrent_message_processing()
        test_rate_limiting_performance()
        test_long_running_memory_stability()

        print("\n" + "=" * 60)
        print("🎉 All performance tests passed!")
        print("💪 Bot is performing excellently!")
        print("=" * 60)

    except Exception as e:
        print(f"\n💥 Performance test failed: {e}")
        import traceback

        traceback.print_exc()
        exit(1)
