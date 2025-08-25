"""Test Discord bot token validation."""

import os
from pathlib import Path
import pytest
from discord import Client
from discord.errors import LoginFailure
from dotenv import load_dotenv


# Load environment variables from .env
load_dotenv(Path(__file__).parent.parent / ".env")


@pytest.mark.asyncio
async def test_discord_token_validity():
    """Test if the Discord bot token is valid by attempting login."""
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        pytest.skip("DISCORD_BOT_TOKEN not set")

    # Get intents from config
    from discord_voice_bot.config import get_config
    config = get_config()
    intents = config.get_intents()

    client = Client(intents=intents)

    try:
        # Attempt to login with the token
        await client.login(token)
        # If successful, the token is valid
        assert client.user is not None, "Token login failed - user is None"
        print("✅ Discord token is valid!")
    except LoginFailure as e:
        pytest.fail(f"❌ Discord token is invalid: {e}")
    except Exception as e:
        pytest.fail(f"❌ Unexpected error during token validation: {e}")
    finally:
        await client.close()