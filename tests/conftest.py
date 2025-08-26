from unittest.mock import MagicMock, patch

import pytest


def build_config_mock():
    """Build a spec-safe mock for the Config object."""
    mock_instance = MagicMock(
        spec_set=[
            "discord_token",
            "target_voice_channel_id",
            "tts_engine",
            "log_level",
            "rate_limit_messages",
            "rate_limit_period",
            "get_enable_self_message_processing",
            "max_message_length",
        ]
    )
    mock_instance.discord_token = "test_token_from_conftest"
    mock_instance.target_voice_channel_id = 1234567890
    mock_instance.tts_engine = "voicevox"
    mock_instance.log_level = "DEBUG"
    mock_instance.rate_limit_messages = 5
    mock_instance.rate_limit_period = 60
    mock_instance.get_enable_self_message_processing.return_value = False
    return mock_instance


MOCK_CONFIG_INSTANCE = build_config_mock()
PATCHERS = []


def pytest_sessionstart(session):
    """
    Called after the Session object has been created and
    before performing test collection.
    """
    global PATCHERS
    # ruff: noqa: PLW0602
    patcher = patch("discord_voice_bot.config.get_config", lambda: MOCK_CONFIG_INSTANCE)
    PATCHERS.append(patcher)
    patcher.start()


def pytest_sessionfinish(session, exitstatus):
    """
    Called after whole test run finished, right before
    returning the exit status to the system.
    """
    global PATCHERS
    # ruff: noqa: PLW0602
    for patcher in PATCHERS:
        patcher.stop()


@pytest.fixture(autouse=True)
def mock_config_get(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """
    Autouse fixture that patches get_config() to return a fresh MagicMock per test.
    Each test gets an isolated mock instance.
    """
    # 1) Create a Config-shaped mock so attribute access matches the real type.
    mock_instance = build_config_mock()

    # 2) Set baseline values for common test scenarios.
    mock_instance.discord_token = "test_token_from_conftest"
    mock_instance.target_voice_channel_id = 1234567890
    mock_instance.tts_engine = "voicevox"
    mock_instance.log_level = "DEBUG"
    mock_instance.rate_limit_messages = 5
    mock_instance.rate_limit_period = 60

    # 3) The most important step: replace the real get_config function
    # with a lambda that always returns our mock instance.
    monkeypatch.setattr("discord_voice_bot.config.get_config", lambda: mock_instance, raising=True)

    # Also patch any direct imports of get_config
    for module in [
        "discord_voice_bot.message_validator",
        "discord_voice_bot.slash.handlers.reconnect",
        "discord_voice_bot.slash.handlers.voice",
        "discord_voice_bot.slash.embeds.status",
        "discord_voice_bot.slash.embeds.voices",
        "discord_voice_bot.config_manager",
    ]:
        monkeypatch.setattr(f"{module}.get_config", lambda: mock_instance, raising=False)

    # 4) Return the mock instance so tests can tweak it if needed.
    return mock_instance
