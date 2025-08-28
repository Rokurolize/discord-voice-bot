import pytest

from discord_voice_bot.config import Config


import dataclasses


@pytest.fixture
def config() -> Config:
    """
    Returns a default, test-safe, immutable Config object.

    Since Config is a frozen dataclass, tests that need to override specific
    values must create a new config object using `dataclasses.replace()`.

    Example:
        new_config = dataclasses.replace(config, tts_engine="aivis")
    """
    return Config(
        discord_token="test_discord_token",
        target_guild_id=987654321,
        target_voice_channel_id=123456789,
        tts_engine="voicevox",
        tts_speaker="normal",
        engines={
            "voicevox": {
                "url": "http://localhost:50021",
                "default_speaker": 3,
                "speakers": {"normal": 3},
            }
        },
        command_prefix="!tts",
        max_message_length=100,
        message_queue_size=10,
        reconnect_delay=5,
        audio_sample_rate=48000,
        audio_channels=2,
        audio_frame_duration=20,
        rate_limit_messages=5,
        rate_limit_period=60,
        log_level="DEBUG",
        log_file=None,
        debug=True,
        test_mode=True,
        enable_self_message_processing=False,
    )
