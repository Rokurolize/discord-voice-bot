# TODOs for Robust Error Propagation, Design Contracts, and Clean Startup Logs

This list captures concrete follow-ups to eliminate diagnostic gaps, align caller/callee contracts, and keep production logs clear and actionable. Each item references the current code location and prescribes a precise change and a test.

## 1) Error Propagation & Diagnostics

- Health-check result guard: replace opaque log with typed error propagation
  - Status: Implemented (code) — tests implemented
  - Where: `src/discord_voice_bot/__main__.py:~200`, `src/discord_voice_bot/errors.py`
  - Problem: `logger.error(f"Health check returned unexpected result: {result!r}")` logs but doesn’t propagate root cause context.
  - Action:
    - Introduced `HealthCheckError` in `src/discord_voice_bot/errors.py`.
    - On invalid result shape, now raises `HealthCheckError` with fields: `result_type`, `result_repr`, `engine_name`, `api_url`.
    - In `main()`, added an explicit `except HealthCheckError` to log structured details and exit with status 1.
  - Remaining Tests:
    - DONE: Extended `tests/test_startup_health_smoke.py` with a “weird return” case asserting `HealthCheckError` is raised and message includes engine/url.

- Standardize exception-to-log mapping for TTS checks
  - Where: `src/discord_voice_bot/tts_client.py:206` and callers
  - Action: Ensure any unexpected exception is converted to a structured `(False, reason)` with short reason and log includes: engine, method, url, exception type, and a brief snippet. Keep cooperative cancellation intact.
  - Tests: Contract test asserting exact tuple shape and non-empty detail on failures.

## 2) Logging Quality & Structure

- Structured log fields (actionable context)
  - Where: hot paths in `__main__.py`, `health_monitor.py`, `tts_client.py`, `voice/` workers
  - Action: Include context fields consistently: `engine`, `api_url`, `target_channel_id`, `guild_id` (when available), `ready`, `in_grace`, `event` code (e.g., `HM-VOICE-NOT-CONNECTED`). Keep human sentence plus fields.
  - Tests: Snapshot/regex tests verifying presence of key fields in warnings after ready.

- Debounce repeated warnings
  - Where: `src/discord_voice_bot/health_monitor.py`
  - Action: Keep a short-lived map of last-emitted issue string → timestamp; suppress identical warning logs within, e.g., 10 seconds.
  - Tests: Simulate repeated detections; assert single warning within window.

## 3) Startup Gating (No False Alarms)

- Correct readiness detection and grace window (implemented, verify coverage)
  - Where: `src/discord_voice_bot/health_monitor.py:_bot_is_ready`, `_in_grace_window`, voice/permission gating
  - Action: Keep as is; ensure permission and voice checks remain suppressed pre-ready and within grace.
  - Tests: `tests/test_health_monitor_startup_gating.py` (done). Consider adding a test that flips ready from False→True and re-runs checks.

- Optional flag to skip network TTS checks locally
  - Where: `src/discord_voice_bot/__main__.py:health_check`
  - Action: Support `STARTUP_SKIP_TTS_CHECK=true` to bypass TTS health in dev; log info that check was skipped. (Implemented)
  - Tests: Unit test toggling the env and verifying skip behavior. (Implemented)

## 4) Caller/Callee Contracts (Type-Safe)

- Replace ad-hoc audio tuples with a single `AudioItem` type
  - Where: `src/discord_voice_bot/voice/queues.py`, `voice/workers/synthesizer.py`, `voice/workers/player.py`
  - Action: Introduce `AudioItem` NamedTuple and return it from `PriorityAudioQueue.get()`. (Implemented)
  - Migration: Keep legacy 4-tuple acceptance in queue; normalize to `AudioItem(size=0)` internally. (Implemented)
  - Tests: Existing `tests/test_audio_queue_contract.py` passes; consider adding explicit type assertion in future.

- Protocols reference shared types
  - Where: `voice/workers/*.py` Protocol declarations
  - Action: Protocols should annotate parameters/returns with `AudioItem` instead of `tuple[...]` to prevent future drift.
  - Tests: Pyright should flag tuple misuse if reintroduced.

## 5) Health Monitor Detail and Severity

- Channel existence checks only after caches are ready (done)
  - Where: `src/discord_voice_bot/health_monitor.py:_check_critical_permissions`
  - Action: Already gated. Add log context when the check is skipped (debug) vs. when it runs (info) to make behavior explicit.
  - Tests: Extend startup gating tests to assert no “target channel not found” pre-ready.

- Permission checks pre-ready
  - Where: `src/discord_voice_bot/health_monitor.py:_check_bot_permissions`
  - Action: Already gated. Add a single info log once the bot becomes ready and permission scan starts.

## 6) Lifecycle & Resource Safety

- Ensure all TTS sessions close on any failure path
  - Where: `src/discord_voice_bot/__main__.py:health_check`
  - Action: Already in `finally`. Add this invariant to tests if not present: “no unclosed client session”.

- Voice client cleanup duration
  - Where: `src/discord_voice_bot/voice/connection_manager.py:cleanup_voice_client`
  - Action: Consider a bounded timeout and a warning if disconnect hangs beyond N seconds.
  - Tests: Stub a hanging disconnect and assert warning.

## 7) Tests (Acceptance + Unit)

- Acceptance
  - Keep `tests/test_startup_health_smoke.py` to emulate CLI health.
  - Add “enqueue→dequeue→playback (stub)” test to assert no unpack errors and correct queue contract end-to-end.

- Unit
  - Health monitor suppression pre-ready (done) and post-ready severity.
  - Debounce behavior on repeated warnings.
  - `AudioItem` contract tests.

## 8) CI & Tooling

- Tighten Pyright for interface drift
  - Enable/report unknown-type/any bans for public interfaces in `voice/` and `health_monitor.py`.

- Pre-commit rule
  - Add simple AST-based check (or ruff rule) to forbid raw audio tuple literals in `voice/` in favor of `AudioItem`.

## 9) Documentation

- README / CONTRIBUTING
  - Document startup grace behavior, structured logs, `STARTUP_SKIP_TTS_CHECK`, and the health-check error contract `(bool, str)`.
  - Add a short “How to interpret health logs” section with examples.

---

Implementation Notes
- Keep changes incremental: raise `HealthCheckError` first, migrate to `AudioItem` second.
- Maintain backward compatibility for tuple inputs until downstream code is fully migrated and tests are updated.
- Prefer small PRs: (1) error propagation + tests, (2) `AudioItem` migration + tests, (3) logging/observability polish.
