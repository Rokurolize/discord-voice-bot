# Suggested Commands for Discord Voice Bot Development

## Run Bot
- `uv run discord-voice-bot`
- `python -m discord_voice_bot`

## Quality Checks
- `uv run poe check`                # lint + type-check + tests
- `uv run poe type-check`           # strict Pyright

## Testing
- `uv run poe test`                 # all tests
- `uv run pytest -q`                # quiet mode
- `uv run pytest -k voice_handler -q`  # targeted run

## Lint, Format, Fix
- `uv run poe lint`                 # Ruff lint (non-destructive)
- `uv run poe format`               # import sort + formatting
- `uv run poe fix`                  # autofix, sort, format

## Pre-commit
- `pre-commit install`              # ensure hooks are active
- `pre-commit run --all-files`      # run hooks locally

## Repo Tooling
- `bash scripts/check-max-lines.sh` # enforce 500-line limit

## Configuration
- `cp .env.example .env`            # create local config
- Edit `.env`: `DISCORD_BOT_TOKEN`, `TARGET_VOICE_CHANNEL_ID`, `TTS_ENGINE`, `VOICEVOX_URL`/`AIVIS_URL`

## Test Mode Examples
- One-off shell (no file change):
  - `export TEST_MODE=true TEST_TARGET_VOICE_CHANNEL_ID=987654321 TEST_RATE_LIMIT_MESSAGES=7 TEST_RATE_LIMIT_PERIOD=30`
  - `uv run poe check`
- .env snippet (quote spaces/commas in numbers):
  ```dotenv
  TEST_MODE=true
  TEST_TARGET_VOICE_CHANNEL_ID=987654321
  TEST_RATE_LIMIT_MESSAGES=7
  TEST_RATE_LIMIT_PERIOD=30
  ```

## Git Essentials
- `git status` / `git diff -U0`
- `git add -A && git commit -m "<subject>"`
- `git push` (prefer a single push after all review items)
