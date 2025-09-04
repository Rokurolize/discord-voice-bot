# Code Review Triage (Filtered by Rule Zero)

Policy: Delegate everything possible to discord.py (no wheel‑reinventing). Use existing utilities (send_interaction, Cog listeners), keep logic minimal, and prefer type safety/robustness without duplicating library behavior.

## Address
- src/discord_voice_bot/event_message_handler.py: After `process_commands`, check `ctx = await bot.get_context(message)` and if `ctx.command` is set, return early to avoid reading commands into TTS.
- src/discord_voice_bot/voice/connection_manager.py: In `connect_to_channel`, set `self.target_channel = channel` and `self.connection_state = "CONNECTING"` before `channel.connect(...)`, and set `self.connection_state = "CONNECTED"` after success.
- src/discord_voice_bot/voice/connection_manager.py: In `is_connected`, add fallback using `self.target_channel.guild.voice_client` when `self.voice_client` is None; scope by guild to avoid false positives.
- src/discord_voice_bot/cogs/voice_group.py: Replace direct `interaction.response.send_message` uses with `send_interaction` and remove `_safe_error`; unify response path and error handling.
- src/discord_voice_bot/cogs/voice_group.py: For `/tts set reset` branch, switch to `send_interaction` to avoid double‑response risk.
- src/discord_voice_bot/cogs/voice_group.py: Consider making `/tts list` and test replies ephemeral to reduce channel noise; acceptable UX improvement.
- src/discord_voice_bot/utils/respond.py: Log exceptions instead of swallowing; skip when both `content` and `embed` are None to avoid 400; keep best‑effort behavior.
- src/discord_voice_bot/event_startup_manager.py: Replace `sys.exit(1)` with raising `RuntimeError`; handle `monitor_task.start()` for sync/async (use `asyncio.create_task` if coroutine returned).
- src/discord_voice_bot/protocols.py: Add `get_voice_client_class() -> type[discord.VoiceProtocol] | None` to `ConfigManager` protocol for type safety.
- src/discord_voice_bot/event_startup_manager.py: Gate “API compliance” log behind a debug flag to avoid stale/misleading info.
- src/discord_voice_bot/utils/speakers.py: Improve matching with `casefold()` and add prefix match fallback for UX.
- src/discord_voice_bot/cogs/status.py: When erroring in hybrid command, only pass `ephemeral=True` if invoked via interaction; otherwise omit ephemeral.
- src/discord_voice_bot/voice/rate_limiter_manager.py: Simplify `_looks_like_discord_callable` (remove redundant `isinstance(owner, object)`), and support sync/async callables (await awaitables; otherwise offload to `asyncio.to_thread`).
- src/discord_voice_bot/bot.py: Use `@override` on event methods; switch `print` to `loguru.logger`; align stats key to `"connection_errors"`; in `on_error` use `get_cog("EventBridge")` and log warning on unhandled.
- src/discord_voice_bot/cogs/events.py: Annotate `self.config_manager: ConfigManager`; add concrete types to `on_voice_state_update` params.
- src/discord_voice_bot/bot_factory.py: Register `EventBridge` first and use `bot.get_cog(...)` for duplicate guards.

## Ignore (with rationale)
- src/discord_voice_bot/cogs/voice_group.py: Making `setup()` handle both sync/async `add_cog` by inspecting return. Discord.py’s documented pattern is `await bot.add_cog(...)`; conditional awaiting is non‑idiomatic and unnecessary per library guidance.
- src/discord_voice_bot/voice/connection_manager.py: Scanning all `bot.voice_clients` across guilds as a last resort. Adds complexity and may still misreport; scoping to `target_channel.guild.voice_client` is sufficient.
- src/discord_voice_bot/voice/ratelimiter_manager.py: External API min‑interval injection via Config. Useful but out of current scope; keep SimpleRateLimiter minimal unless a concrete backend requires it.
- AGENTS.md cosmetic rewording of MCP tool section. Documentation churn without functional value; keep docs minimal.

Notes:
- All accepted items follow the delegation rule, improve robustness, or unify existing helper usage without re‑implementing discord.py features.
