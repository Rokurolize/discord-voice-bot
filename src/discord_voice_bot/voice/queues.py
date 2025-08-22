"""Queue implementations for voice operations."""

import asyncio
from typing import Any, Optional


class SynthesisQueue:
    """Priority queue for TTS synthesis requests."""

    def __init__(self, maxsize: int = 100):
        self._queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=maxsize)

    async def put(self, item: dict[str, Any]) -> None:
        """Add item to synthesis queue."""
        await self._queue.put(item)

    async def get(self) -> dict[str, Any]:
        """Get item from synthesis queue."""
        return await self._queue.get()

    def qsize(self) -> int:
        """Get queue size."""
        return self._queue.qsize()

    def empty(self) -> bool:
        """Check if queue is empty."""
        return self._queue.empty()

    async def clear(self) -> int:
        """Clear all items from queue."""
        count = 0
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
                count += 1
            except asyncio.QueueEmpty:
                break
        return count


class PriorityAudioQueue:
    """Priority queue for audio playback with proper ordering."""

    def __init__(self):
        self._queue: asyncio.Queue[tuple[str, str, int, int]] = asyncio.Queue()

    async def put(self, item: tuple[str, str, int, int]) -> None:
        """Add item to priority queue."""
        await self._queue.put(item)

    async def get(self) -> tuple[str, str, int, int]:
        """Get highest priority item from queue."""
        return await self._queue.get()

    def qsize(self) -> int:
        """Get queue size."""
        return self._queue.qsize()

    def empty(self) -> bool:
        """Check if queue is empty."""
        return self._queue.empty()

    async def get_highest_priority_item(self) -> Optional[tuple[str, str, int, int]]:
        """Get the highest priority item from the audio queue."""
        if self._queue.empty():
            return None

        # Convert queue to list to find highest priority item
        items: list[tuple[str, str, int, int]] = []
        while not self._queue.empty():
            try:
                item = self._queue.get_nowait()
                items.append(item)
            except asyncio.QueueEmpty:
                break

        if not items:
            return None

        # Find highest priority item (lower number = higher priority)
        items.sort(key=lambda x: x[2])  # Sort by priority (index 2)
        highest_priority_item = items[0]

        # Put back all items except the highest priority one
        for item in items[1:]:
            await self._queue.put(item)

        return highest_priority_item

    async def clear(self) -> int:
        """Clear all items from queue."""
        count = 0
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
                count += 1
            except asyncio.QueueEmpty:
                break
        return count

    async def clear_group(self, group_id: str) -> int:
        """Clear all items with specified group_id from queue."""
        cleared = 0

        # Collect all items
        items: list[tuple[str, str, int, int]] = []
        while not self._queue.empty():
            try:
                item = self._queue.get_nowait()
                if item[1] != group_id:  # item[1] is group_id
                    items.append(item)
                else:
                    cleared += 1
            except asyncio.QueueEmpty:
                break

        # Put back non-cleared items
        for item in items:
            await self._queue.put(item)

        return cleared
