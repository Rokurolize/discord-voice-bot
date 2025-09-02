# Coding Style and Conventions for Discord Voice Bot

## General
- Language: Python 3.12
- Formatter: Ruff (double quotes, spaces, line length 200)
- Type hints: required throughout; strict type checking via Pyright
- Imports: sorted by Ruff; prefer `uv run poe format`/`uv run poe fix` before commits

## Naming
- Modules/files: snake_case (e.g., `voice_handler.py`)
- Classes: PascalCase (e.g., `VoiceHandler`)
- Functions/methods: snake_case (e.g., `process_message`)
- Constants: UPPER_SNAKE_CASE (e.g., `MAX_MESSAGE_LENGTH`)

## Quality Gates
- Lint: Ruff (non-destructive via `poe lint`, autofix via `poe fix`)
- Pre-commit: install hooks with `pre-commit install`; blocks files > 500 lines
- PR readiness: `uv run poe check` must pass locally (lint + type-check + tests)

## Testing
- Framework: pytest (+ pytest-asyncio auto)
- Naming: `test_*.py` or `*_test.py`, `Test*` classes, `test_*` functions
- Targeted runs: `uv run pytest -k voice_handler -q`
- Integration: `test_discord_api/` requires `DISCORD_BOT_TOKEN` and Message Content Intent; excluded from routine runs

## Security & Configuration
- `.env` is gitignored; never commit secrets
- Copy `.env.example` → `.env` and set: `DISCORD_BOT_TOKEN`, `TARGET_VOICE_CHANNEL_ID`, `TTS_ENGINE`, `VOICEVOX_URL`/`AIVIS_URL`
- Intent: Ensure Discord "Message Content Intent" is enabled for the bot
- Precedence: environment variables override `.env`; `.env` overrides secrets; all override built-in defaults
- Test mode: enable with `TEST_MODE=true` (truthy: `true`, `1`, `yes`, `on`; case-insensitive)
  - `TEST_TARGET_VOICE_CHANNEL_ID` (default `123456789`), `TEST_RATE_LIMIT_MESSAGES` (default `5`), `TEST_RATE_LIMIT_PERIOD` (default `60`) — positive integers; `_`, space, and `,` allowed in digits (quote when using spaces/commas)

## Design Patterns
- Prefer async/await for I/O
- Decouple via dependency injection for config/services
- Event-driven Discord handlers; queue-based voice pipeline; health monitoring
