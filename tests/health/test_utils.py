from __future__ import annotations

import time

from discord_voice_bot.health.utils import WarningDebouncer, format_issue


def test_format_issue():
    assert format_issue("Prefix", "Detail") == "Prefix: Detail"
    assert format_issue("Prefix", "") == "Prefix"
    assert format_issue("", "Detail") == "Detail"
    assert format_issue("", "") == ""


def test_warning_debouncer_initial_emit():
    debouncer = WarningDebouncer(window_seconds=10)
    assert debouncer.should_emit("test_key") is True


def test_warning_debouncer_suppresses_within_window():
    debouncer = WarningDebouncer(window_seconds=10)
    debouncer.should_emit("test_key")
    assert debouncer.should_emit("test_key") is False


def test_warning_debouncer_emits_after_window():
    debouncer = WarningDebouncer(window_seconds=0.1)
    debouncer.should_emit("test_key")
    time.sleep(0.2)
    assert debouncer.should_emit("test_key") is True


def test_warning_debouncer_multiple_keys():
    debouncer = WarningDebouncer(window_seconds=10)
    assert debouncer.should_emit("key1") is True
    assert debouncer.should_emit("key2") is True
    assert debouncer.should_emit("key1") is False
    assert debouncer.should_emit("key2") is False
