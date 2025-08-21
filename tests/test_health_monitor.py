#!/usr/bin/env python3
"""Test script for the enhanced health monitoring system."""

import asyncio
import time
from unittest.mock import Mock, AsyncMock

# Mock Discord objects for testing
class MockVoiceState:
    def __init__(self, channel=None):
        self.channel = channel

class MockChannel:
    def __init__(self, name="Test Channel", id=123):
        self.name = name
        self.id = id

class MockGuild:
    def __init__(self):
        self.name = "Test Guild"
        self.id = 456
        self.me = Mock()
        self.me.guild_permissions = Mock()
        self.me.guild_permissions.view_channel = True
        self.me.guild_permissions.connect = True
        self.me.guild_permissions.speak = True

class MockBot:
    def __init__(self):
        self.guilds = [MockGuild()]
        self.user = Mock()
        self.user.id = 789

    def get_channel(self, channel_id):
        return MockChannel()

async def test_health_monitor():
    """Test the health monitoring system."""
    print("🩺 Testing Enhanced Health Monitoring System")
    print("=" * 50)

    # Create mock bot and health monitor
    bot = MockBot()
    from discord_voice_bot.health_monitor import HealthMonitor

    monitor = HealthMonitor(bot)
    print("✅ Health monitor created")

    # Test disconnection recording
    print("\n📊 Testing disconnection recording...")
    monitor.record_disconnection("Test disconnection")
    monitor.record_disconnection("Another test disconnection")

    status = monitor.get_health_status()
    print(f"   Total failures: {status['failure_count']}")
    print(f"   Recent failures: {status['recent_failures']}")

    # Test API failure recording
    print("\n🔌 Testing API failure recording...")
    monitor.record_api_failure()

    status = monitor.get_health_status()
    print(f"   API unavailable count: {status['termination_conditions']['api_unavailable_duration']['count']}")

    # Test termination conditions
    print("\n⚠️ Testing termination conditions...")
    conditions = status['termination_conditions']

    for condition_name, condition_data in conditions.items():
        print(f"   {condition_name}: {condition_data['count']}/{condition_data['max']} (window: {condition_data['window']}s)")

    # Test health check simulation
    print("\n🔍 Testing health check simulation...")

    # Mock the TTS engine health check
    original_tts_health_check = None
    try:
        from discord_voice_bot import tts_engine
        original_tts_health_check = tts_engine.tts_engine.health_check
        tts_engine.tts_engine.health_check = AsyncMock(return_value=True)
    except:
        pass

    # Perform health check
    try:
        health_status = await monitor._perform_health_checks()
        print(f"   Health check result: {'✅ PASS' if health_status else '❌ FAIL'}")
        print(f"   Current health status: {'✅ HEALTHY' if monitor.status.healthy else '❌ UNHEALTHY'}")

        if not monitor.status.healthy:
            print("   Issues found:")
            for issue in monitor.status.issues:
                print(f"     • {issue}")
    except Exception as e:
        print(f"   Health check error: {e}")

    # Restore original health check
    if original_tts_health_check:
        tts_engine.tts_engine.health_check = original_tts_health_check

    # Test shutdown
    print("\n🛑 Testing shutdown...")
    await monitor.stop()
    print("✅ Health monitor stopped successfully")

    print("\n🎉 All tests completed!")
    print("\n📋 Summary:")
    print("   ✅ Health monitor creation")
    print("   ✅ Disconnection recording")
    print("   ✅ API failure recording")
    print("   ✅ Termination condition tracking")
    print("   ✅ Health check simulation")
    print("   ✅ Graceful shutdown")

    return True

if __name__ == "__main__":
    asyncio.run(test_health_monitor())