# PR Notes: Discord.py-first Refactor (Hybrid + Group Cogs)

## Overview
- Replace legacy slash registry/handlers with discord.py Hybrid Cogs and a GroupCog (`/tts`).
- Delegate Discord API rate limiting to discord.py; keep local limiter only for external TTS.
- Standardize voice connection flow via `VoiceChannel.connect()` and `Guild.voice_client`.
- Add optional `connect(cls=...)` hook to allow custom `VoiceProtocol` subclasses.

## Why (Avoid Reinventing the Wheel)
- Use `discord.ext.commands` and `discord.app_commands` as intended: registration, checks, cooldowns, autocomplete, sync.
- Remove duplicate registries/wrappers and rely on `CommandTree` as source of truth.
- Follow discord.py’s presence/permissions/cooldown patterns for maintainability and compatibility.

## Key Changes
- Hybrid Cogs for all commands; new GroupCog: `/tts` (set, list, check, reconnect, test, skip, clear).
- Removed: `slash/registry.py`, `slash/handlers/*`, legacy `slash_command_handler.py` and `slash/__init__.py`.
- VoiceConnectionManager: better `is_connected()` fallbacks and `get_connection_info()`; optional `connect(cls=...)` hook.
- Event processing: `bot.process_commands(message)` directly (rate handled by discord.py).
- Deprecate legacy `VoiceHandler.stats` setter in favor of `StatsTracker`.

## Tests Added
- `tests/test_tts_group_commands.py`: ensures `/tts` group is registered after adding `TTSGroup`.
- `tests/test_voice_connection_manager_protocol.py`: validates protocol resolver returns custom `VoiceProtocol` class.

## Migration Notes
- Replace any imports of legacy slash registry/handlers with Hybrid/Group Cogs.
- If you need a custom voice client, implement a `get_voice_client_class()` on config manager returning a `VoiceProtocol` subclass, e.g., derived from `discord.VoiceClient`.

## References (discord.py)
- Commands (ext.commands): https://discordpy.readthedocs.io/en/stable/ext/commands/commands.html
- Interactions (app_commands): https://discordpy.readthedocs.io/en/stable/interactions/api.html
- Hybrid commands & CommandTree sync: see ext.commands and interactions docs above

