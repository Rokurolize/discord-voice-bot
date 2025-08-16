# Development Commands

## Essential Commands

All development commands work via the `uv` wrapper script in the project root:

### Format code (BLACK + RUFF)
```bash
uv run poe format
```
Automatically formats all Python code using Black and fixes import issues with Ruff.

### Check code style
```bash
uv run poe lint
```
Checks code style without making changes. Shows any style issues that need fixing.

### Type checking
```bash
uv run poe type-check
```
Runs mypy type checking on the `src` directory to ensure type safety.

### Run tests
```bash
uv run poe test
```
Runs all tests in the `tests` directory using pytest with async support.

## How it works

The `uv` script in the project root is a wrapper that:
1. Intercepts `uv run poe` commands
2. Activates the existing virtual environment
3. Runs the appropriate tools directly

This ensures compatibility with the existing project structure while maintaining the standard command interface.

## Virtual Environment

The project uses a virtual environment at `./venv/`. All development tools are installed there:
- black (code formatter)
- ruff (linter and import sorter)
- mypy (type checker)
- pytest (test runner)
- poethepoet (task runner)

## Configuration

All tool configurations are in `pyproject.toml`:
- Black: 88 character line length
- Ruff: PEP8 with import sorting
- Mypy: Strict type checking
- Pytest: Async support enabled