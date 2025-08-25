# Task Completion Workflow for Discord Voice Bot

## Before Committing Code Changes

### 1. Format and Lint Code
```bash
timeout 30 uv run poe fix
```
- This runs Ruff autofix, sorts imports, and formats code
- Fixes common issues automatically

### 2. Run Full Quality Checks
```bash
timeout 60 uv run poe check
```
- Runs linting (Ruff), type checking (Pyright), and tests (pytest)
- Must pass completely before proceeding
- If it fails, fix the issues and re-run

### 3. Install/Update Pre-commit Hooks
```bash
timeout 15 pre-commit install
```
- Ensures hooks are active (only needed once or when hooks change)

### 4. Run Pre-commit Checks
```bash
timeout 30 pre-commit run --all-files
```
- Validates all files against pre-commit hooks
- Blocks files over 500 lines
- Enforces Ruff formatting and other quality checks

## Git Workflow

### 5. Stage Changes
```bash
timeout 15 git add .
```

### 6. Commit with Proper Message
```bash
timeout 15 git commit -m "Fix type-check errors in voice handler"
```
- Use imperative mood ("Fix", "Add", "Update", not "Fixed" or "Added")
- Keep subject line concise but descriptive
- Reference issue numbers if applicable

### 7. Push Changes
```bash
timeout 15 git push
```

## Pull Request Process

### 8. Create PR
- Include clear description of changes
- Reference any related issues
- Attach test results and logs if user-facing

### 9. Pre-Review Checklist
- [ ] `uv run poe check` passes
- [ ] All new code has type hints
- [ ] Tests added/updated for changed behavior
- [ ] Documentation updated if needed
- [ ] Pre-commit hooks pass

### 10. Address Review Feedback
- Fix any issues found during review
- Re-run `uv run poe check` after changes
- Update tests if behavior changed

## Running and Testing

### Development Server
```bash
timeout 30 uv run discord-voice-bot
```

### Test Commands
```bash
timeout 30 uv run poe test          # All tests
timeout 30 uv run pytest -k voice_handler -q  # Targeted tests
```

## Configuration Setup

### Initial Setup
```bash
cp .env.example .env
# Edit .env with your settings:
# - DISCORD_BOT_TOKEN
# - TARGET_VOICE_CHANNEL_ID
# - TTS_ENGINE, VOICEVOX_URL/AIVIS_URL
```

### Bot Permissions
- Ensure "Message Content Intent" is enabled in Discord Developer Portal

## File Organization

### Don't Commit
- `.env` (contains secrets)
- `/external-docs/` directory
- `__pycache__/` directories
- `.ruff_cache/` and other cache directories

### Always Commit
- Source code changes
- Test additions/modifications
- Documentation updates
- Configuration examples (`.env.example`)

## Emergency Fixes

If you need to bypass pre-commit (not recommended):
```bash
# NEVER DO THIS unless absolutely necessary
git commit --no-verify -m "Emergency fix: [reason]"
```

## Common Issues and Solutions

### Type Check Errors
- Run `uv run poe type-check` to see specific errors
- Add missing type hints
- Check import statements

### Test Failures
- Run `uv run poe test` to see failing tests
- Check test logic and assertions
- Update tests for changed behavior

### Linting Errors
- Run `uv run poe lint` to see issues
- Use `uv run poe fix` to auto-fix where possible
- Manually fix remaining issues