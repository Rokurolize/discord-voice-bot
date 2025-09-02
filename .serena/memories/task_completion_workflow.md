# Task Completion Workflow for Discord Voice Bot

## Single-Action Summary
- After each fix: `uv run poe check` → commit locally → resolve the specific review thread in the PR UI.
- After all items are addressed: push once to your PR branch to trigger CI a single time.

## Before Committing Code
1) Format and lint
- `uv run poe fix`  # autofix, sort, format

2) Full local verification (must be green)
- `uv run poe check`  # lint + type-check + tests

3) Pre-commit hooks
- `pre-commit install` (once per clone or when hooks change)
- `pre-commit run --all-files`  # optional local validation

## Resolving Review Threads
- Verify the changes exist locally:
  - `git status`
  - `git diff -U0` (or use PR “Files changed”)
- Run verification: `uv run poe check` must exit 0
- Only then resolve the review thread; otherwise continue iterating

## Git & PR Flow
- Stage + commit
  - `git add -A && git commit -m "<imperative, concise subject>"`
- Push strategy
  - Prefer a single push after all review items (keeps CI/reviews consolidated)
  - For fork-based PRs, confirm remotes and push explicitly:
    ```bash
    git remote -v
    git branch -vv
    git push -u origin HEAD:$(git branch --show-current)
    ```
- Pre-push hooks/CI must be green; don’t bypass. If they fail, fix locally and re-run `uv run poe check`.

## Pre-review Checklist
- [ ] `uv run poe check` passes locally
- [ ] New/changed code is fully typed
- [ ] Tests added/updated for behavior changes
- [ ] Docs/examples updated if needed
- [ ] Pre-commit hooks pass (500-line limit enforced)

## Run & Test
- Run bot: `uv run discord-voice-bot` (or `python -m discord_voice_bot`)
- Tests: `uv run poe test` or `uv run pytest -q`
- Targeted tests: `uv run pytest -k voice_handler -q`

## Configuration
- Copy `.env.example` → `.env`; set `DISCORD_BOT_TOKEN`, `TARGET_VOICE_CHANNEL_ID`, TTS settings (`TTS_ENGINE`, `VOICEVOX_URL`/`AIVIS_URL`)
- Enable Discord “Message Content Intent” for the bot
- Test mode:
  - `export TEST_MODE=true TEST_TARGET_VOICE_CHANNEL_ID=987654321 TEST_RATE_LIMIT_MESSAGES=7 TEST_RATE_LIMIT_PERIOD=30`

## Common Issues
- Type-check errors: `uv run poe type-check`; add missing annotations, fix imports
- Lint issues: `uv run poe lint`; then `uv run poe fix` for autofixes
- Test failures: `uv run poe test`; update tests if behavior changed
