"""Audio utility functions for voice operations."""

import os
import tempfile
from typing import Any

from loguru import logger


def validate_wav_format(audio_data: bytes) -> bool:
    """Validate audio data format and basic properties."""
    try:
        if len(audio_data) < 44:  # WAV header is at least 44 bytes
            return False

        # Check WAV header
        if audio_data[:4] != b"RIFF" or audio_data[8:12] != b"WAVE":
            return False

        # Extract basic format info
        channels = int.from_bytes(audio_data[22:24], byteorder="little")
        sample_rate = int.from_bytes(audio_data[24:28], byteorder="little")
        bits_per_sample = int.from_bytes(audio_data[34:36], byteorder="little")

        # Validate reasonable audio parameters
        if channels not in [1, 2]:
            return False
        if sample_rate not in [8000, 16000, 22050, 44100, 48000]:
            return False
        if bits_per_sample not in [8, 16, 24, 32]:
            return False

        return True

    except Exception as e:
        logger.error(f"Audio format validation error: {e}")
        return False


def cleanup_file(audio_path: str) -> None:
    """Clean up temporary audio file."""
    try:
        if audio_path and os.path.exists(audio_path):
            os.remove(audio_path)
    except Exception as e:
        logger.warning(f"Failed to cleanup audio file: {e}")


def calculate_message_priority(item: dict[str, Any]) -> int:
    """Calculate priority for message processing."""
    priority = 5  # Default priority

    # Higher priority for shorter messages (quicker processing)
    if len(item.get("text", "")) < 50:
        priority -= 1

    # Higher priority for commands
    if item.get("text", "").startswith("!"):
        priority -= 2

    # Lower priority for very long messages
    if len(item.get("text", "")) > 200:
        priority += 2

    return max(1, min(10, priority))  # Clamp between 1-10


async def create_temp_audio_file(audio_data: bytes, suffix: str = ".wav") -> str:
    """Create a temporary audio file with the given data."""
    with tempfile.NamedTemporaryFile(mode="wb", suffix=suffix, delete=False) as f:
        result = f.write(audio_data)
        _ = result  # Handle unused result
        return f.name


def get_audio_size(audio_data: bytes) -> int:
    """Get the size of audio data in bytes."""
    return len(audio_data)
