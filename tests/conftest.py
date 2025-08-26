"""Pytest configuration and fixtures for the Discord Voice Bot."""

import os

import pytest

# Don't modify global environment variables
# Instead, use fixtures to provide test-specific configuration


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


def pytest_configure(config: pytest.Config) -> None:
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "integration: mark test as integration test requiring Discord API")
    config.addinivalue_line("markers", "requires_credentials: mark test as requiring Discord credentials")


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Modify test collection to handle integration tests."""
    # Skip integration tests if credentials are not available
    skip_integration = pytest.mark.skip(reason="Discord credentials not configured or integration test disabled")

    for item in items:
        # Check if test is marked as integration test
        if item.get_closest_marker("integration"):
            # Check if required environment variables are set
            required_vars = ["DISCORD_BOT_TOKEN", "TARGET_VOICE_CHANNEL_ID", "TTS_ENGINE"]
            missing_vars = [var for var in required_vars if not os.getenv(var)]

            if missing_vars:
                item.add_marker(skip_integration)
                continue

        # Check if test requires credentials but credentials are missing
        if item.get_closest_marker("requires_credentials"):
            if not os.getenv("DISCORD_BOT_TOKEN"):
                item.add_marker(pytest.mark.skip(reason="Discord bot token not configured"))


# Import asyncio here to avoid import issues
import asyncio


@pytest.fixture(scope="session")
def test_config_manager():
    """Provide a ConfigManagerImpl instance with test mode enabled."""
    from discord_voice_bot.config_manager import ConfigManagerImpl

    return ConfigManagerImpl(test_mode=True)


@pytest.fixture(scope="session")
def prod_config_manager():
    """Provide a ConfigManagerImpl instance with test mode disabled."""
    from discord_voice_bot.config_manager import ConfigManagerImpl

    return ConfigManagerImpl(test_mode=False)


@pytest.fixture(autouse=True)
def mock_env_vars(monkeypatch):
    """Mock common environment variables for all tests."""
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "FAKE_BOT_TOKEN_FOR_TESTS")
    monkeypatch.setenv("TARGET_VOICE_CHANNEL_ID", "123456789")  # unified value
    monkeypatch.setenv("TTS_ENGINE", "voicevox")
    monkeypatch.setenv("VOICEVOX_URL", "http://localhost:50021")
    monkeypatch.setenv("TEST_MODE", "1")  # enables deterministic rate limits
    monkeypatch.setenv("TTS_REQUEST_RATE_LIMIT", "10")  # Test-friendly rate limit
    monkeypatch.setenv("TTS_REQUEST_PER", "1")
