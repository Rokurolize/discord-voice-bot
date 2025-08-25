# Suggested Commands for Discord Voice Bot Development

## Running the Bot
- `uv run discord-voice-bot`: Run the Discord voice bot
- `python -m discord_voice_bot`: Alternative way to run the bot

## Testing
- `uv run poe test` or `uv run pytest -q`: Run all tests
- `uv run pytest -k voice_handler -q`: Run targeted tests for voice handler

## Linting and Formatting
- `uv run poe lint`: Run Ruff linting (non-destructive)
- `uv run poe format`: Sort imports and format code with Ruff
- `uv run poe fix`: Autofix, sort imports, and format code

## Type Checking
- `uv run poe type-check`: Run strict type checking with Pyright

## Full Check
- `uv run poe check`: Run linting, type-checking, and tests

## Pre-commit Setup
- `pre-commit install`: Install pre-commit hooks

## Utility Commands (Linux)
- `ls -la`: List files with details
- `cd <directory>`: Change directory
- `grep -r 'pattern' .`: Search for patterns in files
- `find . -name '*.py'`: Find Python files
- `git status`: Check git status
- `git add .`: Stage all changes
- `git commit -m 'message'`: Commit changes
- `git push`: Push to remote
- `git pull`: Pull from remote

## Configuration
- Copy `.env.example` to `.env` and configure settings
- Set `DISCORD_BOT_TOKEN`, `TARGET_VOICE_CHANNEL_ID`, etc.