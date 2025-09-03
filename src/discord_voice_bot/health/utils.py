from __future__ import annotations

import time
from typing import Callable

class WarningDebouncer:
    def __init__(self, window_seconds: float = 10.0) -> None:
        self.window = window_seconds
        self._last: dict[str, float] = {}

    def should_emit(self, key: str, now: float | None = None) -> bool:
        t = now or time.time()
        last = self._last.get(key)
        if last is None or (t - last) >= self.window:
            self._last[key] = t
            return True
        return False

def format_issue(prefix: str, detail: str) -> str:
    return f"{prefix}: {detail}".strip()

