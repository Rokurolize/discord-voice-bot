Coding Style & Conventions
- Python 3.12
- Formatting: Ruff formatter
  - Double quotes, spaces, line length 200
  - Imports sorted by Ruff; prefer `uv run poe format` or `uv run poe fix` before commits
- Type hints: required; `uv run poe type-check` must pass (Pyright, strict)
- Testing: pytest (+ pytest-asyncio auto)
  - Test naming: files `test_*.py` or `*_test.py`; classes `Test*`; functions `test_*`
- Naming: modules/files snake_case; classes PascalCase; functions snake_case; constants UPPER_SNAKE
- Pre-commit hooks: run `pre-commit install`
  - Enforces Ruff and blocks files > 500 lines

Design/Process Guidelines
- Small, focused commits; accumulate locally; push once after all review items addressed
- Update/add tests for changed behavior
- Keep changes minimal and consistent with existing style

Security/Config
- Never commit secrets
- `.env` is gitignored
- Discord Message Content Intent must be enabled