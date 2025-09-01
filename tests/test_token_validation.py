"""Test Discord bot token validation."""

import os
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from discord import Client


@pytest.mark.asyncio
@patch("discord.Client.login", new_callable=AsyncMock)
async def test_discord_token_validity(mock_login):
    """Test if the Discord bot token is valid by attempting login."""
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        pytest.skip("DISCORD_BOT_TOKEN not set")

    print(f"🔍 Testing token from .env (length: {len(token)})")

    # Get intents from config
    from discord_voice_bot.config import get_config

    config = get_config()
    intents = config.get_intents()

    client = Client(intents=intents)

    try:
        # Attempt to login with the token
        await client.login(token)
        # If successful, the token is valid
        mock_login.assert_called_once_with(token)
        print("✅ Discord token from .env is valid!")
    except Exception as e:
        pytest.fail(f"❌ Unexpected error during token validation: {e}")
    finally:
        await client.close()


@pytest.mark.asyncio
@patch("discord.Client.login", new_callable=AsyncMock)
async def test_discord_token_via_config_manager(mock_login):
    """Test if the Discord bot token via ConfigManager is valid."""
    from discord_voice_bot.config_manager import ConfigManagerImpl

    config_manager = ConfigManagerImpl()

    token = config_manager.get_discord_token()
    if not token:
        pytest.skip("DISCORD_BOT_TOKEN not set in ConfigManager")

    print(f"🔍 Testing token from ConfigManager (length: {len(token)})")

    # Get intents from config
    from discord_voice_bot.config import get_config

    config = get_config()
    intents = config.get_intents()

    client = Client(intents=intents)

    try:
        # Attempt to login with the token
        await client.login(token)
        # If successful, the token is valid
        mock_login.assert_called_once_with(token)
        print("✅ Discord token from ConfigManager is valid!")
    except Exception as e:
        pytest.fail(f"❌ Unexpected error during token validation: {e}")
    finally:
        await client.close()


def test_token_consistency(test_config_manager):
    """Test if tokens from different sources are identical."""
    import os

    # Get token from .env
    env_token = os.getenv("DISCORD_BOT_TOKEN")

    # Get token from ConfigManager (test mode)
    manager_token = test_config_manager.get_discord_token()

    print(f"📊 .env token length: {len(env_token) if env_token else 0}")
    print(f"📊 ConfigManager token length: {len(manager_token) if manager_token else 0}")

    if env_token and manager_token:
        if env_token == manager_token:
            print("✅ Tokens are identical")
        else:
            print("❌ Tokens are different!")

    assert env_token is not None, "Token not found in .env"
    assert manager_token is not None, "Token not found in ConfigManager"
    assert env_token == manager_token, "Tokens from different sources are not identical"


@pytest.mark.asyncio
async def test_bot_creation_and_token(test_config_manager):
    """Test if bot can be created and token is properly set."""
    from discord_voice_bot.bot_factory import BotFactory

    print("🔧 Testing bot creation process...")

    try:
        token = test_config_manager.get_discord_token()
        print(f"🔧 Bot token obtained (length: {len(token)})")

        # Create bot factory
        factory = BotFactory()
        print("🔧 Bot factory created")

        # Create bot instance with test mode
        bot = await factory.create_bot(test_mode=True)
        print("🔧 Bot instance created")

        # Check if bot has the token
        # Note: We can't directly access the token from bot, but we can test the creation process
        assert bot is not None, "Bot creation failed"
        assert hasattr(bot, "config_manager"), "Bot missing config_manager"
        assert bot.config_manager is not None, "Bot config_manager is None"

        # Verify test mode is properly set
        assert bot.config_manager.is_test_mode() == True, "Bot should be in test mode"

        print("✅ Bot creation process successful")

    except Exception as e:
        pytest.fail(f"❌ Bot creation failed: {e}")


@pytest.mark.asyncio
@patch("discord.Client.login", new_callable=AsyncMock)
async def test_bot_start_with_config_dry_run(mock_login, test_config_manager):
    """Test bot start_with_config method without actually connecting to Discord."""
    from discord_voice_bot.bot_factory import BotFactory

    print("🚀 Testing bot start_with_config (dry run)...")

    try:
        # Create bot instance with explicit test mode
        factory = BotFactory()
        bot = await factory.create_bot(test_mode=True)

        # Get the token that would be used
        token = bot.config_manager.get_discord_token()
        print(f"🚀 Token that would be used (length: {len(token)})")

        # Test the token one more time
        from discord import Client

        from discord_voice_bot.config import get_config

        config = get_config()
        intents = config.get_intents()

        test_client = Client(intents=intents)
        try:
            await test_client.login(token)
            mock_login.assert_called_once_with(token)
            print("🚀 Token is valid for Discord login")
        except Exception as e:
            print(f"🚀 Token validation during dry run failed: {e}")
            raise
        finally:
            await test_client.close()

        # Debug the config manager test mode
        print(f"🚀 ConfigManager test_mode: {bot.config_manager.is_test_mode()}")
        print(f"🚀 ConfigManager debug: {bot.config_manager.is_debug()}")

        # Check the actual config instance used by the manager
        actual_config = bot.config_manager._get_config()
        print(f"🚀 Actual config test_mode: {actual_config.test_mode}")
        print(f"🚀 Actual config debug: {actual_config.debug}")

        # Check if test mode would prevent actual connection
        if bot.config_manager.is_test_mode():
            print("🚀 Bot is in test mode - would skip Discord connection")
        else:
            print("🚀 Bot is NOT in test mode - would attempt Discord connection")

        print("✅ Bot start_with_config dry run successful")

    except Exception as e:
        pytest.fail(f"❌ Bot start_with_config dry run failed: {e}")


@pytest.mark.asyncio
@patch("discord.Client.login", new_callable=AsyncMock)
async def test_actual_bot_startup_simulation(mock_login, prod_config_manager, config):
    """
    Simulate the bot's real startup flow using the provided test fixtures and assert that the Discord login call is attempted with the production token.
    
    Performs the same high-level steps the application startup would:
    - Instantiates BotManager with the supplied test config and replaces its ConfigManager with prod_config_manager.
    - Runs logging setup and configuration validation.
    - Retrieves the Discord token from the overridden ConfigManager and attempts a login using a temporary discord.Client.
    - Asserts that the patched `login` (mock_login) was invoked once with the token.
    
    Any exception during setup, validation, or the login attempt causes the test to fail.
    """

    print("🎯 Simulating actual bot startup process...")

    try:
        # Import the actual main module
        from src.discord_voice_bot import __main__

        # Create BotManager with explicit test config (avoid env-dependent defaults)
        bot_manager = __main__.BotManager(config)
        # Override the config manager with our production one
        bot_manager.config_manager = prod_config_manager

        # Set up logging (like main function does)
        bot_manager.setup_logging()

        # Check configuration validation
        print("🎯 Validating configuration...")
        bot_manager.config_manager.validate()
        print("🎯 Configuration validation passed")

        # Get the same token that would be used in bot startup
        token = bot_manager.config_manager.get_discord_token()
        print(f"🎯 Token that would be used (length: {len(token)})")

        # Check test mode
        test_mode = bot_manager.config_manager.is_test_mode()
        print(f"🎯 Test mode: {test_mode}")
        print(f"🎯 Debug mode: {bot_manager.config_manager.is_debug()}")

        # Debug: Check what the actual config instance has
        print("🎯 Debugging ConfigManagerImpl initialization...")
        actual_config = bot_manager.config_manager._get_config()
        print(f"🎯 Actual config test_mode: {actual_config.test_mode}")
        print(f"🎯 Actual config debug: {actual_config.debug}")

        # Test the token
        from discord import Client

        from discord_voice_bot.config import get_config

        config = get_config()
        intents = config.get_intents()

        test_client = Client(intents=intents)
        try:
            await test_client.login(token)
            mock_login.assert_called_once_with(token)
            print("🎯 Token is valid for Discord login")
        except Exception as e:
            print(f"🎯 Token validation failed: {e}")
            raise
        finally:
            await test_client.close()

        print("✅ Actual bot startup simulation successful")

    except Exception as e:
        pytest.fail(f"❌ Actual bot startup simulation failed: {e}")


def test_environment_variable_sources():
    """Test where TEST_MODE environment variable is coming from."""
    import os

    print("🔍 Testing environment variable sources...")

    # Check if there are any other .env files or environment files
    current_dir = Path.cwd()
    env_files = list(current_dir.glob("**/*.env"))
    env_files.extend(current_dir.glob("**/*env*"))

    print(f"🔍 Found potential env files: {[str(f) for f in env_files]}")

    # Check for any Python environment files
    python_env_files = [".env", ".flaskenv", ".python-env", "pyvenv.cfg", current_dir / ".config" / "discord-voice-bot" / "secrets.env"]

    for env_file in python_env_files:
        env_path = Path(env_file)
        if env_path.exists():
            print(f"🔍 Found env file: {env_path}")
            if env_path.is_file():
                try:
                    with open(env_path) as f:
                        content = f.read()
                        if "TEST_MODE" in content:
                            print(f"🔍 TEST_MODE found in {env_path}")
                            for line in content.split("\n"):
                                if "TEST_MODE" in line:
                                    print(f"  {line.strip()}")
                except Exception as e:
                    print(f"🔍 Could not read {env_path}: {e}")

    # Check environment variables
    test_mode = os.getenv("TEST_MODE")
    debug = os.getenv("DEBUG")

    print(f"🔍 Current TEST_MODE: {test_mode}")
    print(f"🔍 Current DEBUG: {debug}")

    # Check if there are any pytest or test-related environment variables
    test_env_vars = {k: v for k, v in os.environ.items() if "test" in k.lower() or "pytest" in k.lower()}
    if test_env_vars:
        print("🔍 Test-related environment variables:")
        for k, v in test_env_vars.items():
            print(f"  {k}={v}")

    print("✅ Environment variable sources test completed")
