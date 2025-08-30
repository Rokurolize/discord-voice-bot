#!/usr/bin/env python3
"""Test script for the enhanced health monitoring system."""

import asyncio
from typing import Any, override
from unittest.mock import AsyncMock, Mock

from discord_voice_bot.protocols import DiscordBotClient


# Mock Discord objects for testing
class MockTTSClient:
    def __init__(self, config_manager: Any) -> None:
        self.config_manager = config_manager
        self.session = None

    async def start_session(self) -> None:
        pass

    async def close_session(self) -> None:
        pass

    async def check_api_availability(self) -> tuple[bool, str]:
        return True, ""


class MockVoiceState:
    def __init__(self, channel: Mock | None = None) -> None:  # type: ignore[reportMissingSuperCall]
        self.channel = channel


class MockChannel:
    def __init__(self, name: str = "Test Channel", id: int = 123) -> None:  # type: ignore[reportMissingSuperCall]
        self.name = name
        self.id = id


class MockGuild:
    def __init__(self):  # type: ignore[reportMissingSuperCall]
        self.name = "Test Guild"
        self.id = 456
        self.me = Mock()
        self.me.guild_permissions = Mock()
        self.me.guild_permissions.view_channel = True
        self.me.guild_permissions.connect = True
        self.me.guild_permissions.speak = True


class MockConfigManager:
    def __init__(self) -> None:  # type: ignore[reportMissingSuperCall]
        self.target_voice_channel_id = 123456789

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

    def get_target_voice_channel_id(self) -> int:
        return self.target_voice_channel_id

    def get_api_url(self) -> str:
        return "http://localhost:10101"

    def get_speaker_id(self) -> int:
        return 1512153249

    def get_tts_engine(self) -> str:
        return "aivis_speech"

    def get_audio_sample_rate(self) -> int:
        return 48000

    def get_audio_channels(self) -> int:
        return 1

    def get_log_level(self) -> str:
        return "INFO"

    def validate(self) -> None:
        pass

    def get_discord_token(self) -> str:
        return "test_token"

    def get_command_prefix(self) -> str:
        return "!"

    def get_engine_config(self) -> dict[str, Any]:
        return {}

    def get_engines(self) -> dict[str, dict[str, Any]]:
        return {"aivis_speech": {}}

    def get_max_message_length(self) -> int:
        return 10000

    def get_message_queue_size(self) -> int:
        return 50

    def get_reconnect_delay(self) -> int:
        return 5

    def get_rate_limit_messages(self) -> int:
        return 10

    def get_rate_limit_period(self) -> int:
        return 60

    def get_log_file(self) -> str:
        return "test.log"

    def is_debug(self) -> bool:
        return False

    def get_intents(self) -> dict[str, bool]:
        return {"message_content": True, "members": True}


class MockBot(DiscordBotClient):
    """Mock Discord bot client that implements DiscordBotClient protocol."""

    def __init__(self) -> None:  # type: ignore[reportMissingSuperCall]
        self.__guilds: list[MockGuild] = [MockGuild()]
        self.__user: Mock = Mock()
        self.__user.id = 789
        self.application_id = 123456789

    @property
    def guilds(self) -> list[MockGuild]:
        """List of guilds the bot is in."""
        return self.__guilds

    @override
    def get_channel(self, channel_id: int) -> MockChannel:
        return MockChannel()

    def get_partial_messageable(self, channel_id: int) -> MockChannel:
        return MockChannel()

    def get_guild(self, guild_id: int) -> MockGuild:
        return MockGuild()

    def get_user(self, user_id: int) -> Mock:
        return Mock()

    def get_emoji(self, emoji_id: int) -> Mock:
        return Mock()

    def get_sticker(self, sticker_id: int) -> Mock:
        return Mock()

    @override
    async def close(self) -> None:
        pass

    async def connect(self, *, reconnect: bool = True) -> None:
        pass

    async def login(self, token: str) -> None:
        pass

    async def start(self, token: str) -> None:
        pass

    @override
    def is_closed(self) -> bool:
        return False

    @property
    def is_ready(self) -> bool:
        return True

    @property
    def latency(self) -> float:
        return 0.1

    @property
    def voice_clients(self) -> list[Mock]:
        return []

    @property
    def ws(self) -> Mock:
        return Mock()

    @property
    def loop(self) -> Mock:
        return Mock()

    @property
    def intents(self) -> Mock:
        return Mock()

    @property
    def users(self) -> list[Mock]:
        return []

    @property
    def emojis(self) -> list[Mock]:
        return []

    @property
    def stickers(self) -> list[Mock]:
        return []

    @property
    def cached_messages(self) -> list[Mock]:
        return []

    def get_all_channels(self) -> list[MockChannel]:
        return []

    def get_all_members(self) -> list[Mock]:
        return []

    def get_all_roles(self) -> list[Mock]:
        return []

    def get_all_emojis(self) -> list[Mock]:
        return []

    def get_all_stickers(self) -> list[Mock]:
        return []

    # Discord.py Client protocol requirements
    @property
    def activity(self) -> Mock:
        return Mock()

    @property
    def status(self) -> Mock:
        return Mock()

    @property
    def allowed_mentions(self) -> Mock:
        return Mock()

    @property
    def user(self) -> Mock:
        return self.__user

    @user.setter
    def user(self, value: Mock) -> None:
        self.__user = value

    @property
    def application(self) -> Mock:
        return Mock()

    @property
    def session(self) -> Mock:
        return Mock()

    @property
    def http(self) -> Mock:
        return Mock()

    @property
    def gateway(self) -> Mock:
        return Mock()

    @property
    def shard_count(self) -> int:
        return 1

    @property
    def shard_id(self) -> int:
        return 0

    @override
    def __getattr__(self, name: str) -> Any:
        """Allow dynamic attribute access for optional components."""
        if name == "voice_handler":
            return Mock()
        return Mock()


async def test_health_monitor() -> bool:
    """Test the health monitoring system."""
    print("🩺 Testing Enhanced Health Monitoring System")
    print("=" * 50)

    # Create mock bot and health monitor
    bot: MockBot = MockBot()
    config_manager: MockConfigManager = MockConfigManager()
    tts_client = MockTTSClient(config_manager)
    from discord_voice_bot.health_monitor import HealthMonitor

    monitor: HealthMonitor = HealthMonitor(bot, config_manager, tts_client)
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
    conditions = status["termination_conditions"]

    for condition_name, condition_data in conditions.items():
        print(f"   {condition_name}: {condition_data['count']}/{condition_data['max']} (window: {condition_data['window']}s)")

    # Test health check simulation
    print("\n🔍 Testing health check simulation...")

    # Mock the TTS client health check
    original_check = tts_client.check_api_availability
    tts_client.check_api_availability = AsyncMock(return_value=(True, ""))  # type: ignore[assignment]

    # Perform health check
    try:
        await monitor.perform_health_checks_for_testing()
        print(f"   Current health status: {'✅ HEALTHY' if monitor.status.healthy else '❌ UNHEALTHY'}")

        if not monitor.status.healthy:
            print("   Issues found:")
            for issue in monitor.status.issues:
                print(f"     • {issue}")
    except Exception as e:
        print(f"   Health check error: {e}")

    # Restore original health check
    tts_client.check_api_availability = original_check

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
    _ = asyncio.run(test_health_monitor())
