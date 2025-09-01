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

- Test mode is enabled by setting the `TEST_MODE` environment variable (e.g., `TEST_MODE=true`) or by instantiating with `ConfigManagerImpl(test_mode=True)`.
- Precedence: process environment variables override entries in `.env`; `.env` overrides built-in defaults.
- Values recognized as true (case-insensitive): `true`, `1`, `yes`, `on`. Any other value (or an unset/empty `TEST_MODE`) is treated as false.

### Test-only overrides
- `TEST_TARGET_VOICE_CHANNEL_ID` (default: `123456789`) — overrides the voice channel while in test mode (set via environment variables or `.env`). Must be a positive integer; accepts underscores/spaces/commas in digits (e.g., `1_234_567_890` or `1,234,567,890`).
- `TEST_RATE_LIMIT_MESSAGES` (default: `5`) and `TEST_RATE_LIMIT_PERIOD` (default: `60`) — override rate limits in test mode (set via environment variables or `.env`). Must be positive integers; accept digits with underscores/spaces/commas.

Examples:

```dotenv
# .env (test mode)
TEST_MODE=true
TEST_TARGET_VOICE_CHANNEL_ID=987654321
TEST_RATE_LIMIT_MESSAGES=7
TEST_RATE_LIMIT_PERIOD=30
```

```bash
# one-off shell (no .env change)
export TEST_MODE=true TEST_TARGET_VOICE_CHANNEL_ID=987654321 TEST_RATE_LIMIT_MESSAGES=7 TEST_RATE_LIMIT_PERIOD=30
uv run poe check
```

## Resolving Review Threads
- Verify locally that the referenced changes are applied in your working tree:
  - Inspect working tree: `git status`
  - Review exact diffs: `git diff -U0` (or open the PR "Files changed" tab, or download the raw patch)
- Run verification: `uv run poe check` must exit with status code 0 before resolving a thread.
- Even for doc-only changes, still run the checks to ensure linting, type checking, and tests remain green.

## Single-Action Summary
- After each fix: `uv run poe check` → commit locally → resolve in the PR UI.
- After all items: push once to your PR branch (e.g., `git push`).
- Do not bypass pre-push hooks; if hooks fail, address issues and rerun `uv run poe check` before pushing again.
  If your PR originates from a fork, verify your remotes and push explicitly:
  ```bash
  set -euo pipefail
  git remote -v
  # Tip: In fork-based PRs, 'origin' is your fork and 'upstream' is the base repository.
  # Confirm your fork is 'origin'. If not, set it explicitly:
  # git remote set-url origin git@github.com:<your-username>/<your-fork>.git
  git branch -vv
  # Push the current HEAD to your PR branch on your fork:
  git push -u origin HEAD:$(git branch --show-current)
  ```
- Tip: A single final push triggers pre-push hooks and CI only once, keeping reviews consolidated.

## Maintenance Note
- Prefer small, focused commits. Accumulate them locally and push once after all review items are addressed to consolidate CodeRabbit into a single review run.
  - Optionally, tidy history before pushing:
    - `git rebase -i origin/main` to squash commits or mark work-in-progress commits as `fixup`.
    - If this branch is shared or already published, avoid history rewrites; prefer a new commit or merge.
    - Or use "Squash and merge" on GitHub to keep the main history clean.
    - If you rebased local history, run `uv run poe check` again, then push safely: `git push --force-with-lease`
