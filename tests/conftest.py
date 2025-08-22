"""Pytest configuration and shared fixtures."""

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

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
    voice_client = AsyncMock()
    voice_client.is_connected = MagicMock(return_value=True)
    voice_client.is_playing = MagicMock(return_value=False)
    voice_client.play = MagicMock()
    voice_client.stop = MagicMock()
    voice_client.disconnect = AsyncMock()
    return voice_client


# Test Authentication System
@pytest.fixture
def test_user():
    """Create a test user for authentication."""
    return {"id": 123456789, "username": "testuser", "discriminator": "1234", "avatar": "test_avatar_hash", "email": "test@example.com"}


@pytest.fixture
def test_token(test_user):
    """Generate a test JWT token for the test user."""
    import time

    import jwt

    # Mock token generation
    payload = {"sub": str(test_user["id"]), "username": test_user["username"], "iat": int(time.time()), "exp": int(time.time()) + 3600}  # 1 hour expiration

    # Use a simple secret for testing
    secret = "test_secret_key"
    token = jwt.encode(payload, secret, algorithm="HS256")
    return token


@pytest.fixture
def auth_headers(test_token):
    """Create authentication headers for test requests."""
    return {"Authorization": f"Bearer {test_token}"}


@pytest.fixture
def invalid_token():
    """Generate an invalid JWT token."""
    import time

    import jwt

    # Create expired token
    payload = {"sub": "123", "iat": int(time.time()) - 7200, "exp": int(time.time()) - 3600}  # 2 hours ago  # 1 hour ago (expired)

    secret = "test_secret_key"
    token = jwt.encode(payload, secret, algorithm="HS256")
    return token


@pytest.fixture
def invalid_auth_headers(invalid_token):
    """Create invalid authentication headers."""
    return {"Authorization": f"Bearer {invalid_token}"}


@pytest.fixture
def malformed_auth_headers():
    """Create malformed authentication headers."""
    return {"Authorization": "NotBearer token123"}


@pytest.fixture
def admin_user():
    """Create an admin test user."""
    return {"id": 987654321, "username": "admin", "discriminator": "0001", "avatar": "admin_avatar_hash", "email": "admin@example.com", "roles": ["admin"]}


@pytest.fixture
def admin_token(admin_user):
    """Generate a test JWT token for admin user."""
    import time

    import jwt

    payload = {"sub": str(admin_user["id"]), "username": admin_user["username"], "roles": admin_user["roles"], "iat": int(time.time()), "exp": int(time.time()) + 3600}

    secret = "test_secret_key"
    token = jwt.encode(payload, secret, algorithm="HS256")
    return token


@pytest.fixture
def admin_auth_headers(admin_token):
    """Create admin authentication headers."""
    return {"Authorization": f"Bearer {admin_token}"}
