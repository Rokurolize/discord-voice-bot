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

## PR Review Handling Workflow (gh-review-threads.sh)
- Prereqs: install `gh` and `jq`; authenticate (defaults to `github.com` if `GH_HOST` is unset):
  - `gh auth status -h "${GH_HOST:-github.com}"`
- Project defaults (set once):
  - `export GH_OWNER=Rokurolize`
  - `export GH_REPO=discord-voice-bot`
  - (optional, for GHES) `export GH_HOST=<hostname>`
- Help: `scripts/gh-review-threads.sh --help` shows all flags and subcommands.

### One-by-One Loop (full text, minimal steps)
- Set PR: `export GH_PR=<number>` (or pass `--pr <number>` per call).
- Get next unresolved (full body): `line="$(scripts/gh-review-threads.sh list-next-unresolved-ndjson)"`
  - If the command prints nothing (empty output), you're done — no unresolved items remain.
- Inspect context quickly:
  - Path/URL: `echo "$line" | jq -r '.path, .url'`
  - Diff: `echo "$line" | jq -r '.diffHunk' | less -R`
  - Body: `echo "$line" | jq -r '.body' | less -R`
- Implement the fix, then verify: `uv run poe check`.
- Resolve the addressed thread only:
  - `id="$(echo "$line" | jq -r '.databaseId')"`
  - `scripts/gh-review-threads.sh resolve-by-discussion-ids "$id"`
- Commit after each item: `git add -A && git commit -m "fix: address review — <short>"`.
- Repeat until no more output from `list-next-unresolved-ndjson`.

### Push Policy
Push once at the end to trigger CodeRabbit: `git push origin HEAD`.

Notes:
- Owner/repo are fixed for this project via `GH_OWNER=Rokurolize` and `GH_REPO=discord-voice-bot`; you can still pass `--owner/--repo` explicitly if needed.
- Use `DRY_RUN=1` with resolve subcommands to preview without mutating.
- For GitHub Enterprise Server, set `GH_HOST`, e.g. `export GH_HOST=ghe.company.com`.
- Prefer the one-by-one NDJSON flow above; XML/truncated previews and manual GraphQL are unnecessary here.

## Verification Before Resolve
- Compare the referenced code locally and ensure the change is applied.
- Run checks: `uv run poe check` must pass (exit code 0) before resolving a thread.

## Resolve and Commit Strategy
- Resolve only the thread you addressed using `resolve-by-discussion-ids` (see Loop above).
- Commit each resolved item; push once when all review items are addressed.

## Single-Action Summary
- Use `list-next-unresolved-ndjson` to fetch full-text comments one at a time.
- After each fix: `uv run poe check` → resolve that thread → commit.
- After all items: one final `git push origin HEAD`.

### Optional Filters
- To skip outdated comments, filter: `scripts/gh-review-threads.sh list-unresolved-ndjson | jq 'select(.outdated==false) | first'`.
  - Note: one discussion `databaseId` resolves the entire thread.

## Script Help
See `scripts/gh-review-threads.sh --help` for the complete list of subcommands and flags.

## PR Ops (optional)
- View PR metadata: `gh pr view <N> --json title,headRefName,mergeable,url`.

## Maintenance Note
- When iterating on review fixes, prefer small focused commits; avoid pushing until all review items are addressed, to batch CodeRabbit runs into a single CodeRabbit run.
