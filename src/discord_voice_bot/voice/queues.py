"""Queue implementations for voice operations."""

import asyncio
import heapq
from typing import Any


class SynthesisQueue:
    """Priority queue for TTS synthesis requests."""

    def __init__(self, maxsize: int = 100):
        super().__init__()
        self._queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=maxsize)
        self.maxsize = maxsize

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
                result = self._queue.get_nowait()
                _ = result  # Handle unused result
                count += 1
            except asyncio.QueueEmpty:
                break
        return count

    def get_nowait(self) -> dict[str, Any]:
        """Get item from queue without waiting (synchronous)."""
        return self._queue.get_nowait()


class PriorityAudioQueue:
    """Priority queue for audio playback with proper ordering."""

    def __init__(self):
        super().__init__()
        self._heap: list[tuple[int, int, str, str, int, int]] = []
        self._lock = asyncio.Lock()
        self._counter = 0  # For FIFO ordering with same priority

    async def put(self, item: tuple[str, str, int, int]) -> None:
        """Add item to priority queue with proper ordering."""
        async with self._lock:
            # item format: (audio_path, group_id, priority, chunk_index)
            # heap format: (priority, counter, audio_path, group_id, priority, chunk_index)
            heapq.heappush(self._heap, (item[2], self._counter, item[0], item[1], item[2], item[3]))
            self._counter += 1

    async def get(self) -> tuple[str, str, int, int]:
        """Get highest priority item from queue (lowest priority number first)."""
        async with self._lock:
            if not self._heap:
                raise asyncio.QueueEmpty("Queue is empty")

            # Get item from heap: (priority, counter, audio_path, group_id, priority, chunk_index)
            _, _, audio_path, group_id, priority, chunk_index = heapq.heappop(self._heap)
            return (audio_path, group_id, priority, chunk_index)

    def qsize(self) -> int:
        """Get queue size."""
        return len(self._heap)

    def empty(self) -> bool:
        """Check if queue is empty."""
        return len(self._heap) == 0

    async def clear(self) -> int:
        """Clear all items from queue."""
        async with self._lock:
            count = len(self._heap)
            self._heap.clear()
            self._counter = 0
            return count

    async def clear_group(self, group_id: str) -> int:
        """Clear all items with specified group_id from queue."""
        async with self._lock:
            # Filter out items with matching group_id
            original_heap = self._heap[:]
            self._heap = [item for item in original_heap if item[3] != group_id]
            cleared_count = len(original_heap) - len(self._heap)
            # Re-heapify after filtering
            heapq.heapify(self._heap)
            return cleared_count
