Core Commands
- Run bot: `uv run discord-voice-bot` (or `python -m discord_voice_bot`)

Quality Checks
- Lint: `uv run poe lint`
- Format: `uv run poe format`
- Autofix + sort + format: `uv run poe fix`
- Type-check: `uv run poe type-check`
- Full check (lint + type + tests): `uv run poe check`

Testing
- Run tests: `uv run poe test` or `uv run pytest -q`
- Targeted tests: `uv run pytest -k voice_handler -q`

Environment & Test Mode
- Example `.env` setup: copy `.env.example` → `.env`
- One-off test mode run:
  `export TEST_MODE=true TEST_TARGET_VOICE_CHANNEL_ID=987654321 TEST_RATE_LIMIT_MESSAGES=7 TEST_RATE_LIMIT_PERIOD=30 && uv run poe check`

Review & Diffs
- Inspect working tree: `git status`
- Review exact diffs: `git diff -U0`

Git Push (fork-based PRs)
- Verify remotes: `git remote -v`
- Show branch tracking: `git branch -vv`
- Push current HEAD to PR branch: `git push -u origin HEAD:$(git branch --show-current)`