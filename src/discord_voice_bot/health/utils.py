from __future__ import annotations

import time


class WarningDebouncer:
    def __init__(self, window_seconds: float = 10.0) -> None:
        super().__init__()
        self.window = window_seconds
        self._last: dict[str, float] = {}

    def should_emit(self, key: str, now: float | None = None) -> bool:
        t = now if now is not None else time.time()
        last = self._last.get(key)
        if last is None or (t - last) >= self.window:
            self._last[key] = t
            return True
        return False


def format_issue(prefix: str, detail: str) -> str:
    if prefix and detail:
        return f"{prefix}: {detail}"
    if prefix:
        return prefix
    return detail
