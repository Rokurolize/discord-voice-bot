from __future__ import annotations

from typing import Any, Tuple, List

import discord


async def check_voice_connection_health(
    guild: discord.Guild | None,
    voice_client: discord.VoiceClient | None,
    connection_state_getter: Callable[[], Any] | None = None,
) -> tuple[bool, list[str]]:
    """Lightweight wrapper extracted from HealthMonitor._check_voice_connection_health.

    Returns (healthy, issues).
    """
    issues: List[str] = []

    # Guild or voice client absent typically means not connected yet; consider healthy but informative.
    if guild is None or voice_client is None:
        return True, issues

    # Basic invariants: connected flag and channel presence
    try:
        if not voice_client.is_connected():
            issues.append("VoiceClient is not connected")
        if getattr(voice_client, "channel", None) is None:
            issues.append("VoiceClient has no channel bound")
    except Exception as e:  # best-effort diagnostics
        issues.append(f"VoiceClient check error: {type(e).__name__}")

    # Optional extra state
    if connection_state_getter is not None:
        try:
            _ = connection_state_getter()
        except Exception as e:
            issues.append(f"Connection state getter error: {type(e).__name__}")

    return (len(issues) == 0), issues

