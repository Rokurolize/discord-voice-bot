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

## Code Review Ops (gh + GraphQL)
- Prereqs: Install `gh` and `jq`. Authenticate with `gh auth login`.
- Host Support (GHES): Set `GH_HOST` or pass `--host <hostname>` (defaults to `github.com`). All `gh` calls and auth use this host.
- Auth Check: `gh auth status -h ${GH_HOST:-github.com}` (verify repo:write if resolving).
- List Unresolved (summary): `scripts/gh-review-threads.sh --owner <O> --repo <R> --pr <N> list-unresolved`
  - Shows thread id, status, comment count, and comment databaseIds (no bodies).
- List Unresolved (details): `scripts/gh-review-threads.sh --owner <O> --repo <R> --pr <N> list-unresolved-details`
  - Shows each comment’s path, url, databaseId, and a truncated body preview (200–400 chars) for quick scanning.
- Unresolved JSON (threads, full): `scripts/gh-review-threads.sh --owner <O> --repo <R> --pr <N> list-unresolved-json`
  - Emits raw JSON thread nodes including full bodies and diffHunks (best for scripting).
- Unresolved NDJSON (comments, full): `scripts/gh-review-threads.sh --owner <O> --repo <R> --pr <N> list-unresolved-ndjson`
  - Emits one JSON object per unresolved comment (full bodies, unescaped) — ideal for tooling.
- Unresolved Details (full body TSV): `scripts/gh-review-threads.sh --owner <O> --repo <R> --pr <N> list-unresolved-details-full`
  - Tabular output with full, untruncated bodies for human review.
- Unresolved XML (optional): `scripts/gh-review-threads.sh --owner <O> --repo <R> --pr <N> list-unresolved-xml`
  - XML-escaped output with full bodies for systems that prefer XML.
- Resolve By IDs: `scripts/gh-review-threads.sh --owner <O> --repo <R> --pr <N> resolve-by-discussion-ids <id ...>`
- Resolve By URLs: `scripts/gh-review-threads.sh --owner <O> --repo <R> --pr <N> resolve-by-urls <url ...>`
- Resolve All: `scripts/gh-review-threads.sh --owner <O> --repo <R> --pr <N> resolve-all-unresolved`
- Unresolve: `scripts/gh-review-threads.sh --owner <O> --repo <R> --pr <N> unresolve-thread-ids <thread-id ...>`
- Dry‑Run: `DRY_RUN=1 scripts/gh-review-threads.sh --owner <O> --repo <R> --pr <N> resolve-all-unresolved`

## GraphQL Snippets (Reference)
- Fetch Threads: `gh api graphql -F owner='<O>' -F name='<R>' -F number=<N> -f query='query($owner:String!,$name:String!,$number:Int!){ repository(owner:$owner,name:$name){ pullRequest(number:$number){ reviewThreads(first:100){ nodes{ id isResolved isOutdated comments(first:50){ nodes{ databaseId url path body diffHunk } } } }}}}' --jq '.data.repository.pullRequest.reviewThreads.nodes'`
- Purpose: Map `discussion_r<databaseId>` numbers to `thread.id`, inspect `path/body/diffHunk`, and decide resolution.

## Verification Playbook Before Resolve
- Read Thread: Fetch thread bodies and `path/diffHunk` (see GraphQL snippet).
- Compare Code: Open the referenced file(s) and confirm the suggestion is applied.
- Run Checks: `uv run poe check` (ruff + pyright + tests) must pass.
- Resolve: Use `scripts/gh-review-threads.sh` to resolve only addressed threads.

## Single‑Action Workflow: “Address the Review Comments”
- Fetch unresolved comments with full context:
  - Threads JSON: `scripts/gh-review-threads.sh --owner <O> --repo <R> --pr <N> list-unresolved-json`
  - Or Comments NDJSON (recommended for tooling): `scripts/gh-review-threads.sh --owner <O> --repo <R> --pr <N> list-unresolved-ndjson`
- Apply changes per comments; prefer precise, minimal patches.
- Verify locally: `uv run poe check` must pass.
- Resolve addressed comments by ID: `scripts/gh-review-threads.sh --owner <O> --repo <R> --pr <N> resolve-by-discussion-ids <id ...>`
  - Use only IDs you actually addressed.
- Commit and push: `git add -A && git commit -m "<concise subject>" && git push origin HEAD`.

### One‑by‑One Resolution (NDJSON + jq)
- Set env (once per session):
  - `export GH_OWNER=<O> GH_REPO=<R> GH_PR=<N>` and optionally `export GH_HOST=<host>` for GHES
- Fetch full comments (unescaped, not truncated):
  - `scripts/gh-review-threads.sh list-unresolved-ndjson > /tmp/review.ndjson`
- Loop one comment at a time:
  1) Select next comment
     - `line="$(sed -n '1p' /tmp/review.ndjson)"`
     - If empty → done
  2) Inspect context
     - Path/URL: `echo "$line" | jq -r '.path, .url'`
     - Diff: `echo "$line" | jq -r '.diffHunk' | less -R`
     - Body: `echo "$line" | jq -r '.body' | less -R`
  3) Implement fix in code, then verify
     - `uv run poe check`
  4) Resolve just that thread
     - `id="$(echo "$line" | jq -r '.databaseId')"`
     - `scripts/gh-review-threads.sh resolve-by-discussion-ids "$id"`
  5) Refresh list and repeat
     - `scripts/gh-review-threads.sh list-unresolved-ndjson > /tmp/review.ndjson`
- Tips:
  - Skip outdated by default: `scripts/gh-review-threads.sh list-unresolved-ndjson | jq 'select(.outdated==false)' > /tmp/review.ndjson`
  - Resolution is at thread level; a single `databaseId` maps to and resolves its entire thread.

## Script Reference
- Location: `scripts/gh-review-threads.sh:1`
- Subcommands: `list`, `list-unresolved`, `list-details`, `list-unresolved-details`, `list-unresolved-details-full`, `list-unresolved-json`, `list-unresolved-xml`, `list-unresolved-ndjson`, `resolve-all-unresolved`, `resolve-by-discussion-ids`, `resolve-by-urls`, `unresolve-thread-ids`
- Notes: Uses GraphQL `resolveReviewThread` / `unresolveReviewThread`. Accepts IDs (`discussion_r...` numbers) or URLs. Supports pagination and `DRY_RUN`.
 - Host: Honors `--host` flag or `GH_HOST` environment variable for GitHub Enterprise.

## PR Ops (gh)
- View PR: `gh pr view <N> --json title,headRefName,mergeable,url`
- Append Body: `gh pr view <N> --json body -q .body > /tmp/body.md && echo "\n<update>\n" >> /tmp/body.md && gh pr edit <N> --body-file /tmp/body.md`
- Submit Review: `gh pr review <N> --comment -b "<summary>"` or `--approve`/`--request-changes` as needed.

## Maintenance Cheatsheet
- Timeout Aliases (UP041): Prefer builtin `TimeoutError` (Python ≥3.11).
  - Scan: `rg -n "asyncio\.TimeoutError|socket\.timeout" -S`
  - Replace: Use `TimeoutError` directly and remove local `noqa: UP041`.
  - Re‑enable: Ensure UP041 is not ignored in `pyproject.toml:169`.
- PR Update Flow:
  - Commit: `git add -A && git commit -m "refactor: replace timeout aliases (UP041) and re-enable rule"`
  - Push: `git push origin HEAD`
  - Validate: `uv run poe check`
  - Resolve remaining threads after verification (see Code Review Ops).
