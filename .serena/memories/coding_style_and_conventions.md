# Coding Style and Conventions for Discord Voice Bot

## General Rules
- **Language**: Python 3.12
- **Formatter**: Ruff (double quotes, spaces, line length 200)
- **Type Hints**: Required, all functions and methods must have type annotations
- **Type Checking**: Strict mode with Pyright

## Naming Conventions
- **Modules/Files**: snake_case (e.g., `voice_handler.py`)
- **Classes**: PascalCase (e.g., `VoiceHandler`)
- **Functions/Methods**: snake_case (e.g., `process_message`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `MAX_MESSAGE_LENGTH`)
- **Variables**: snake_case (e.g., `user_message`)

## Import Organization
- Imports sorted automatically by Ruff
- Use `poe format` or `poe fix` before commits

## Code Quality Rules
- **Linting**: Ruff with comprehensive rule set
- **Pre-commit Hooks**: Must install with `pre-commit install`
- **File Size Limit**: No files over 500 lines (enforced by pre-commit)
- **Docstrings**: Not strictly required but recommended for public APIs

## Testing Guidelines
- **Framework**: pytest with pytest-asyncio
- **Naming**: `test_*.py` or `*_test.py`, `Test*` classes, `test_*` functions
- **Async Tests**: Auto-enabled via pytest-asyncio
- **Targeted Runs**: Use `-k` flag for specific tests (e.g., `uv run pytest -k voice_handler -q`)
- **Integration Tests**: `test_discord_api/` requires `DISCORD_BOT_TOKEN`

## Commit Guidelines
- **Style**: Imperative, concise subjects (e.g., "Fix type-check errors in voice handler")
- **Pre-commit**: Must pass `uv run poe check` before review
- **PR Requirements**: Include description, rationale, linked issues, test results

## Security & Configuration
- **Secrets**: Never commit `.env` file (gitignored)
- **Bot Token**: Set `DISCORD_BOT_TOKEN` in `.env`
- **Voice Channel**: Configure `TARGET_VOICE_CHANNEL_ID`
- **TTS Settings**: Set `TTS_ENGINE`, `VOICEVOX_URL`/`AIVIS_URL`
- **Message Content Intent**: Must be enabled for Discord bot

## Design Patterns
- **Async/Await**: Preferred for all I/O operations
- **Dependency Injection**: Used for configuration and services
- **Event-Driven**: Discord event handlers for message processing
- **Queue-Based**: Voice message queuing system
- **Health Monitoring**: Built-in health checks and monitoring