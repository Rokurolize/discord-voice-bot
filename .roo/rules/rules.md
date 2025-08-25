# Repository Guidelines

## Project Structure & Module Organization
- `src/discord_voice_bot/`: core package and entrypoint (`__main__.py`).
- `src/discord_voice_bot/voice/`: voice pipeline, queues, workers, and health.
- `src/discord_voice_bot/slash/`: slash commands, autocomplete, and embeds.
- `tests/`: pytest suite (async enabled); config lives in `pyproject.toml`.
- `test_discord_api/`: optional manual API checks (needs bot token; not part of default run).
- `scripts/`: tooling (e.g., `check-max-lines.sh`).
- `.env.example`: copy to `.env` for local config.

## Build, Test, and Development Commands
- `uv run discord-voice-bot`: run the bot (or `python -m discord_voice_bot`).
- `uv run poe test` or `uv run pytest -q`: run tests.
- `uv run poe lint`: Ruff linting (non-destructive).
- `uv run poe format`: import sort + formatting.
- `uv run poe fix`: autofix, then sort, then format.
- `uv run poe type-check`: strict type checking via Pyright.
- `uv run poe check`: lint + type-check + tests.

## Coding Style & Naming Conventions
- Python 3.12; formatter is Ruff (double quotes, spaces, line length 200).
- Imports sorted by Ruff; prefer `poe format`/`poe fix` before commits.
- Type hints required; changes should pass `poe type-check`.
- Pre-commit hooks: run `pre-commit install` (enforces Ruff and blocks files > 500 lines).
- Naming: modules/files snake_case; classes PascalCase; functions snake_case; constants UPPER_SNAKE.

## Testing Guidelines
- Framework: pytest (+ pytest-asyncio auto). Naming: `test_*.py` or `*_test.py`, `Test*` classes, `test_*` functions.
- Targeted runs: `uv run pytest -k voice_handler -q`.
- Integration: `test_discord_api/` requires `DISCORD_BOT_TOKEN` and Message Content Intent; exclude from routine runs.

## Commit & Pull Request Guidelines
- Commits: imperative, concise subjects (e.g., "Fix type-check errors in voice handler").
- PRs: include description, rationale, linked issues, and local test results; attach logs/screenshots when user-facing.
- Before requesting review: `uv run poe check` must pass; update/ add tests for changed behavior.

## Security & Configuration Tips
- Copy `.env.example` → `.env`; set `DISCORD_BOT_TOKEN`, `TARGET_VOICE_CHANNEL_ID`, and TTS settings (`TTS_ENGINE`, `VOICEVOX_URL`/`AIVIS_URL`).
- Never commit secrets; `.env` is gitignored. Ensure Discord "Message Content Intent" is enabled for the bot.

## Git rules

Commit your code changes via Git while adhering to the following rules.

The rules are as follows:
- typeCheckingMode = "strict"
- Ignoring errors is not allowed.
- Avoiding type errors is not allowed.
- Modifying pyright configuration settings is not allowed.
- Changing `pyrightconfig.json` is not allowed.
- Modifying `pyproject.toml` is not allowed.
- Ignoring type checker configuration settings is not allowed.
- Properly modifying type checker configuration settings is not allowed.
- Using `--no-verify` to forcefully commit changes is not allowed.
- Add `timeout 15 ` (or whatever reasonable amount of time is needed to execute the command) timeouts to all commands executed in Bash.
- you MUST use `uv`

You must resolve any issues identified by the type checker based on the actual error content, addressing each issue exactly as intended by the question: "What is the purpose of this specific error?"

Do not commit /external-docs/ directory.

--no-verifyはダメだよ！ちゃんとリファクタリングすればプッシュできるはずだから、時間をかけて頑張ってね！
