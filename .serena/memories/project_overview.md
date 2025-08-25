# Discord Voice Bot Project Overview

## Purpose
This project is a Discord voice channel text-to-speech bot that uses Zundamon voice to convert text messages into speech in Discord voice channels.

## Tech Stack
- **Language**: Python 3.12
- **Framework**: discord.py[voice] >= 2.6.0
- **Dependencies**: python-dotenv, aiofiles, loguru, zstandard
- **Development Tools**: pyright, poethepoet, ruff, pytest, pytest-asyncio, pre-commit

## Project Structure
- `src/discord_voice_bot/`: Core package and entrypoint (`__main__.py`)
- `src/discord_voice_bot/voice/`: Voice pipeline, queues, workers, and health
- `src/discord_voice_bot/slash/`: Slash commands, autocomplete, and embeds
- `tests/`: Pytest suite (async enabled)
- `test_discord_api/`: Optional manual API checks
- `scripts/`: Tooling (e.g., check-max-lines.sh)

## Entry Points
- `uv run discord-voice-bot` or `python -m discord_voice_bot`