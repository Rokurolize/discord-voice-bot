"""Pytest configuration and shared fixtures."""

import asyncio
import sys
from pathlib import Path

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_discord_client():
    """Create a mock Discord client."""
    from unittest.mock import AsyncMock, MagicMock

    client = AsyncMock()
    client.user = MagicMock()
    client.user.id = 123456789
    client.user.name = "TestBot"
    client.guilds = []
    client.voice_clients = []
    return client


@pytest.fixture
def mock_voice_client():
    """Create a mock Discord voice client."""
    from unittest.mock import AsyncMock, MagicMock

    voice_client = AsyncMock()
    voice_client.is_connected = MagicMock(return_value=True)
    voice_client.is_playing = MagicMock(return_value=False)
    voice_client.play = MagicMock()
    voice_client.stop = MagicMock()
    voice_client.disconnect = AsyncMock()
    return voice_client
