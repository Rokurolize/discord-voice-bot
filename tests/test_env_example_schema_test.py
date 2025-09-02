# Tests for the .env-style configuration template at tests/test_env_example.py
# Testing library/framework: pytest
import re
from pathlib import Path
from urllib.parse import urlparse

import pytest

ENV_EXAMPLE_PATH = Path(__file__).with_name("test_env_example.py")


def _parse_env_file(path: Path):
    """
    Lightweight .env parser:
    - Ignores blank lines and lines that start with '#'
    - Accepts KEY=VALUE pairs
    - Strips trailing inline comments that begin with ' #'
    - Strips surrounding single/double quotes from VALUE
    Returns: (env_dict, duplicate_keys_list)
    """
    env = {}
    seen = set()
    duplicates = []
    with path.open("r", encoding="utf-8") as f:
        for idx, raw in enumerate(f, start=1):
            line = raw.rstrip("\n")
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if "=" not in stripped:
                raise AssertionError(f"Line {idx} must be KEY=VALUE: {line}")
            key, value = stripped.split("=", 1)
            key = key.strip()
            value = value.strip()
            # Remove trailing inline comment if present: VALUE  # comment
            value = re.sub(r"\s+#.*$", "", value)
            # Remove surrounding quotes
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
                value = value[1:-1]
            if key in seen:
                duplicates.append(key)
            seen.add(key)
            env[key] = value
    return env, duplicates


@pytest.fixture(scope="module")
def parsed():
    assert ENV_EXAMPLE_PATH.exists(), f"Missing file: {ENV_EXAMPLE_PATH}"
    env, dups = _parse_env_file(ENV_EXAMPLE_PATH)
    return {"env": env, "dups": dups}


def test_env_example_exists_and_is_readable():
    assert ENV_EXAMPLE_PATH.exists(), "The env example file must exist."
    content = ENV_EXAMPLE_PATH.read_text(encoding="utf-8")
    assert len(content) > 0, "The env example file should not be empty."


def test_no_duplicate_keys(parsed):
    assert not parsed["dups"], f"Duplicate keys found: {parsed['dups']}"


def test_required_keys_present(parsed):
    # Focused on keys present in the provided diff/content
    expected = {
        "DISCORD_BOT_TOKEN",
        "TARGET_VOICE_CHANNEL_ID",
        "TTS_ENGINE",
        "VOICEVOX_URL",
        "AIVIS_URL",
        "COMMAND_PREFIX",
        "MAX_MESSAGE_LENGTH",
        "ENABLE_SELF_MESSAGE_PROCESSING",
        "MESSAGE_QUEUE_SIZE",
        "RECONNECT_DELAY",
        "RATE_LIMIT_MESSAGES",
        "RATE_LIMIT_PERIOD",
        "LOG_LEVEL",
        "DEBUG",
        # Test-only overrides (optional and may be blank)
        "TEST_RATE_LIMIT_MESSAGES",
        "TEST_RATE_LIMIT_PERIOD",
        "TEST_TARGET_VOICE_CHANNEL_ID",
    }
    keys = set(parsed["env"].keys())
    missing = expected - keys
    assert not missing, f"Missing expected keys: {missing}"


def test_keys_are_uppercase_snake_case(parsed):
    snake = re.compile(r"^[A-Z0-9_]+$")
    bad = list(parsed["env"].keys())
    bad = [k for k in bad if not snake.match(k)]
    assert not bad, f"Non-UPPER_SNAKE_CASE keys: {bad}"


def _assert_int_non_negative(name: str, value: str):
    try:
        iv = int(value)
    except Exception as e:
        raise AssertionError(f"{name} must be an integer, got {value!r}") from e
    assert iv >= 0, f"{name} must be non-negative, got {iv}"


def _parse_bool(name: str, value: str) -> bool:
    lv = value.lower()
    assert lv in {"true", "false"}, f"{name} must be 'true' or 'false' (case-insensitive), got {value!r}"
    return lv == "true"


def test_integer_fields_non_negative(parsed):
    env = parsed["env"]
    for key in ["MAX_MESSAGE_LENGTH", "MESSAGE_QUEUE_SIZE", "RECONNECT_DELAY", "RATE_LIMIT_MESSAGES", "RATE_LIMIT_PERIOD"]:
        assert key in env, f"Missing {key}"
        _assert_int_non_negative(key, env[key])


def test_boolean_fields_and_defaults(parsed):
    env = parsed["env"]
    for key in ["ENABLE_SELF_MESSAGE_PROCESSING", "DEBUG"]:
        assert key in env, f"Missing {key}"
        _parse_bool(key, env[key])
        # The template defaults in the diff show these as 'false'
        assert env[key].lower() == "false", f"{key} should default to 'false' in example, got {env[key]!r}"
    # Ensure inline comment on ENABLE_SELF_MESSAGE_PROCESSING didn't pollute its value
    assert env["ENABLE_SELF_MESSAGE_PROCESSING"].lower() == "false"


def test_urls_are_valid_and_expected_defaults(parsed):
    env = parsed["env"]
    for key in ["VOICEVOX_URL", "AIVIS_URL"]:
        assert key in env, f"Missing {key}"
        u = urlparse(env[key])
        assert u.scheme in {"http", "https"}, f"{key} must have http/https scheme, got {env[key]!r}"
        assert u.netloc, f"{key} must include host:port, got {env[key]!r}"
    # Validate default ports per the provided template
    vv = urlparse(env["VOICEVOX_URL"])
    ai = urlparse(env["AIVIS_URL"])
    assert vv.port == 50021, f"VOICEVOX_URL should default to port 50021, got {vv.port}"
    assert ai.port == 10101, f"AIVIS_URL should default to port 10101, got {ai.port}"


def test_command_prefix_default(parsed):
    env = parsed["env"]
    cp = env["COMMAND_PREFIX"]
    assert cp, "COMMAND_PREFIX must not be empty"
    assert cp.startswith("!"), f"COMMAND_PREFIX should start with '!', got {cp!r}"
    assert len(cp) <= 10, "COMMAND_PREFIX should be concise"


def test_log_level_valid_default(parsed):
    env = parsed["env"]
    allowed = {"DEBUG", "INFO", "WARNING", "ERROR"}
    assert env["LOG_LEVEL"] in allowed, f"LOG_LEVEL must be one of {sorted(allowed)}, got {env['LOG_LEVEL']!r}"
    assert env["LOG_LEVEL"] == "INFO", f"LOG_LEVEL should default to 'INFO' in example, got {env['LOG_LEVEL']!r}"


def test_placeholders_and_sensible_defaults(parsed):
    env = parsed["env"]
    assert env["DISCORD_BOT_TOKEN"] == "your_bot_token_here", "DISCORD_BOT_TOKEN should be a placeholder value"
    assert env["TARGET_VOICE_CHANNEL_ID"] == "your_voice_channel_id_here", "TARGET_VOICE_CHANNEL_ID should be a placeholder value"
    assert env["TTS_ENGINE"] == "voicevox", "TTS_ENGINE should default to 'voicevox' per template"


def test_test_override_fields_blank_or_valid(parsed):
    env = parsed["env"]
    # Blank is acceptable, otherwise must be valid integers (non-negative)
    for key in ["TEST_RATE_LIMIT_MESSAGES", "TEST_RATE_LIMIT_PERIOD"]:
        val = env.get(key, "")
        if val != "":
            _assert_int_non_negative(key, val)
    # For TEST_TARGET_VOICE_CHANNEL_ID: blank allowed; if set, must be positive integer
    tvid = env.get("TEST_TARGET_VOICE_CHANNEL_ID", "")
    if tvid != "":
        try:
            iv = int(tvid)
        except Exception as e:
            raise AssertionError(f"TEST_TARGET_VOICE_CHANNEL_ID must be an integer if set, got {tvid!r}") from e
        assert iv > 0, f"TEST_TARGET_VOICE_CHANNEL_ID must be > 0 if provided, got {iv}"
