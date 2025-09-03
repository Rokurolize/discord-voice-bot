Before Resolving Review Threads / Completing a Task
- Verify working tree and diffs: `git status`, `git diff -U0`
- Run full checks (must pass): `uv run poe check`
- Even for doc-only changes, run checks to catch lint/type issues

Commit & PR Hygiene
- Commit messages: imperative, concise (e.g., "Fix type-check errors in voice handler")
- PRs: include description, rationale, linked issues, and local test results; attach logs/screenshots when user-facing
- Update/add tests for changed behavior

Pushing
- Prefer a single final push after addressing all review items
- For forks: verify `origin` is your fork; push current HEAD to PR branch
- Do not bypass pre-push hooks; if hooks fail, fix issues and rerun `uv run poe check`

Maintenance Notes
- Keep commits small and focused; optional: tidy via `git rebase -i origin/main` (avoid rewriting shared/published history)
- If rebased, run `uv run poe check` again; push with `--force-with-lease` if needed

Security
- Never commit secrets; ensure `.env` is gitignored
- Discord Message Content Intent must be enabled for the bot