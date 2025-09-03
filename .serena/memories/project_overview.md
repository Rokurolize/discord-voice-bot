Project: discord-voice-bot

Purpose
- Discord voice bot with text-to-speech (TTS), slash commands, and a voice pipeline (queues, workers, health).
- Joins a target voice channel and speaks via TTS engines (configurable).

Tech Stack
- Language: Python 3.12
- Tooling: uv (runner), poe (task runner), pytest (tests), Ruff (lint/format), Pyright (type-check), pre-commit hooks
- TTS: configurable engines via env (VOICEVOX, AIVIS)

Entrypoints
- Run bot: `uv run discord-voice-bot` or `python -m discord_voice_bot`

Configuration
- Copy `.env.example` to `.env` and set:
  - `DISCORD_BOT_TOKEN`, `TARGET_VOICE_CHANNEL_ID`
  - TTS settings: `TTS_ENGINE`, `VOICEVOX_URL` / `AIVIS_URL`
- Message Content Intent must be enabled for the bot.
- Test mode: set `TEST_MODE=true` (env takes precedence over `.env`).
- Test-only overrides (in test mode):
  - `TEST_TARGET_VOICE_CHANNEL_ID` (default: 123456789)
  - `TEST_RATE_LIMIT_MESSAGES` (default: 5)
  - `TEST_RATE_LIMIT_PERIOD` (default: 60)
  - Accept digits with `_`, spaces, or commas; quote values with spaces/commas in `.env`.

Behavioral Notes
- Precedence: environment vars override `.env`; `.env` overrides secrets; all override built-ins.
- Truthy values (case-insensitive): `true`, `1`, `yes`, `on`. Anything else (or unset) is false.

Development Checklist (high level)
- Use `uv run poe check` routinely (lint + type-check + tests)
- Keep changes small and focused; ensure type hints are correct and formatting is clean
- Never commit secrets; `.env` is gitignored