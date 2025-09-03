Repository Structure
- `src/discord_voice_bot/`: core package and entrypoint (`__main__.py`).
- `src/discord_voice_bot/voice/`: voice pipeline, queues, workers, health.
- `src/discord_voice_bot/slash/`: slash commands, autocomplete, embeds.
- `tests/`: pytest suite (async enabled); pytest config in `pyproject.toml`.
- `test_discord_api/`: optional manual API checks (requires bot token; not part of default run).
- `scripts/`: tooling (e.g., `check-max-lines.sh`).
- `.env.example`: copy to `.env` for local config.

Notable Conventions
- Python sources live under `src/`; module import root is `discord_voice_bot`.
- Tests follow pytest async conventions and naming rules.
- Pre-commit enforces Ruff and max file length (≤ 500 lines).