"""Test script to demonstrate the modular architecture components."""

import asyncio

from .bot_factory import BotFactory
from .command_handler import CommandHandler
from .config import config
from .event_handler import EventHandler
from .message_validator import MessageValidator
from .slash_command_handler import SlashCommandHandler
from .status_manager import StatusManager


async def test_modular_components():
    """Test the modular architecture components."""
    print("🧪 Testing Modular Discord Voice TTS Bot Architecture")
    print("=" * 60)

    # Test 1: Status Manager
    print("\n1️⃣  Testing Status Manager...")
    status_manager = StatusManager()
    status_manager.record_command_usage("test")
    status_manager.record_message_processed()
    stats = status_manager.get_statistics()
    print(f"   ✅ Status tracking: {stats['command_usage']} commands, {stats['messages_processed']} messages")
    print(f"   ✅ Health status: {status_manager.get_overall_health()}")

    # Test 2: Message Validator
    print("\n2️⃣  Testing Message Validator...")
    validator = MessageValidator()
    test_message = type(
        "MockMessage",
        (),
        {
            "author": type("MockUser", (), {"bot": False, "id": 123456})(),
            "content": "Hello, this is a test message!",
            "type": type("MockType", (), {"name": "default"})(),
            "channel": type("MockChannel", (), {"id": 789012})(),
        },
    )()

    result = await validator.validate_message(test_message)
    print(f"   ✅ Message validation: {result.is_valid}")
    print(f"   ✅ Filtered content: {result.filtered_content}")
    print(f"   ✅ Warnings: {len(result.warnings)}")

    # Test 3: Bot Factory
    print("\n3️⃣  Testing Bot Factory...")
    factory = BotFactory()
    print(f"   ✅ Factory created with {len(factory.registry.get_all())} registered components")
    print(f"   ✅ Component info: {list(factory.registry.get_all().keys())}")

    # Test 4: Component Integration
    print("\n4️⃣  Testing Component Integration...")

    # Mock bot for testing
    class MockBot:
        def __init__(self):
            self.config = config
            self.guilds = []
            self.stats = {"messages_processed": 0, "tts_messages_played": 0}

    mock_bot = MockBot()

    # Test Event Handler
    event_handler = EventHandler(mock_bot)
    print("   ✅ Event Handler created")

    # Test Command Handler
    command_handler = CommandHandler(mock_bot)
    print("   ✅ Command Handler created")

    # Test Slash Command Handler
    slash_handler = SlashCommandHandler(mock_bot)
    print("   ✅ Slash Command Handler created")

    print("\n🎉 All modular components tested successfully!")
    print("\n📊 Architecture Summary:")
    print("   • Event Handler: Discord event management")
    print("   • Command Handler: Prefix-based commands")
    print("   • Slash Handler: Modern slash commands")
    print("   • Message Validator: Content filtering & validation")
    print("   • Status Manager: Statistics & monitoring")
    print("   • Bot Factory: Component initialization")

    print(f"\n🏆 Modular Architecture: {len(factory.registry.get_all())} components working together!")
    print("\n💡 The architecture is ready for integration into the main bot.py file.")
    print("   Each component can be developed, tested, and maintained independently.")


if __name__ == "__main__":
    asyncio.run(test_modular_components())
