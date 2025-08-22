"""Slash command handlers."""

from .clear import handle as clear
from .reconnect import handle as reconnect
from .skip import handle as skip
from .status import handle as status
from .test_tts import handle as test_tts
from .voice import handle as voice
from .voicecheck import handle as voicecheck
from .voices import handle as voices

__all__ = [
    "clear",
    "reconnect",
    "skip",
    "status",
    "test_tts",
    "voice",
    "voicecheck",
    "voices",
]
