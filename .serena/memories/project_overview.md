# Discord Voice Bot Project Overview

## Purpose
Discord bot that converts text messages to speech in voice channels. Supports multiple TTS engines and slash-command driven controls.

## Tech Stack
- Language: Python 3.12
- Core: discord.py[voice]
- Dev tooling: uv + poethepoet, Ruff, Pyright, pytest (+ pytest-asyncio), pre-commit

## Project Structure
- `src/discord_voice_bot/`: core package and entrypoint (`__main__.py`)
- `src/discord_voice_bot/voice/`: voice pipeline, queues, workers, health
- `src/discord_voice_bot/slash/`: slash commands, autocomplete, embeds
- `tests/`: pytest suite (async enabled; config in `pyproject.toml`)
- `test_discord_api/`: optional manual API checks (requires bot token; excluded from routine runs)
- `scripts/`: tooling (e.g., `check-max-lines.sh`)

## Entrypoints
- `uv run discord-voice-bot` or `python -m discord_voice_bot`

## Configuration
- Copy `.env.example` → `.env`
- Required: `DISCORD_BOT_TOKEN`, `TARGET_VOICE_CHANNEL_ID`
- TTS: `TTS_ENGINE`, `VOICEVOX_URL`/`AIVIS_URL`
- Discord: enable Message Content Intent for the bot
- Secrets: `.env` is gitignored; never commit tokens

## Test Mode
- Enable via `TEST_MODE=true` or `ConfigManagerImpl(test_mode=True)`
- Truthy values: `true`, `1`, `yes`, `on` (case-insensitive). Anything else (incl. empty/unset) is false.
- Test-only overrides (env or `.env`):
  - `TEST_TARGET_VOICE_CHANNEL_ID` (default `123456789`) — positive integer; digits may include `_`, space, or `,` (quote when using spaces/commas)
  - `TEST_RATE_LIMIT_MESSAGES` (default `5`) — positive integer; accepts `_`/space/`,`
  - `TEST_RATE_LIMIT_PERIOD` (default `60`) — positive integer; accepts `_`/space/`,`

## Notes
- Prefer small, focused commits; run `uv run poe check` locally before PRs
- Large files (>500 lines) are blocked by pre-commit
