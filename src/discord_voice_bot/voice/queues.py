"""Queue implementations for voice operations."""

import asyncio
import heapq
from typing import Any, NamedTuple


class AudioItem(NamedTuple):
    """Typed audio queue item used across voice workers.

    Fields:
    - path: path to the audio file on disk
    - group_id: logical group identifier for batching/cancellation
    - priority: lower value means higher playback priority
    - chunk_index: zero-based index for multi-chunk messages
    - size: audio file size in bytes (0 if unknown)
    """

    path: str
    group_id: str
    priority: int
    chunk_index: int
    size: int


class SynthesisQueue:
    """Priority queue for TTS synthesis requests."""

    def __init__(self, maxsize: int = 100):
        super().__init__()
        self._queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=maxsize)
        self.maxsize = maxsize

    async def put(self, item: dict[str, Any]) -> None:
        """
        Enqueue a synthesis request, awaiting until space is available.

        Args:
            item: Synthesis request payload with text, voice settings, and metadata.

        """
        await self._queue.put(item)

    def put_nowait(self, item: dict[str, Any]) -> None:
        """
        Enqueue a synthesis request without awaiting.

        Adds the item immediately; raises if the internal queue is full.

        Args:
            item: Synthesis request payload (TTS request details) to enqueue.

        Raises:
            asyncio.QueueFull: If the queue has reached its maxsize.

        """
        self._queue.put_nowait(item)

    async def get(self) -> dict[str, Any]:
        """
        Retrieve the next synthesis request from the queue, awaiting until one is available.

        Returns:
            dict[str, Any]: The next queued synthesis item (a request dictionary).

        """
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
    """Priority queue for audio playback with proper ordering.

    Item layout used by the public API:
    - put(): (audio_path, group_id, priority, chunk_index, audio_size)
    - get(): (audio_path, group_id, priority, chunk_index, audio_size)

    Internally we store a heap tuple to maintain stable ordering:
    (priority, counter, audio_path, group_id, priority, chunk_index, audio_size)
    """

    def __init__(self):
        super().__init__()
        self._heap: list[tuple[int, int, str, str, int, int, int]] = []
        self._lock = asyncio.Lock()
        self._counter = 0  # For FIFO ordering with same priority

    async def put(
        self,
        item: AudioItem | tuple[Any, ...],
    ) -> None:
        """Add item to priority queue with proper ordering.

        Accepts both 5-tuple (preferred) and legacy 4-tuple input:
        - (audio_path, group_id, priority, chunk_index, audio_size)
        - (audio_path, group_id, priority, chunk_index)  # audio_size assumed 0
        """
        async with self._lock:
            # item format: (audio_path, group_id, priority, chunk_index, [audio_size])
            if isinstance(item, AudioItem):
                audio_path, group_id, priority, chunk_index, audio_size = item
            else:
                # Validate tuple input strictly for clearer errors
                if len(item) == 4:
                    audio_path, group_id, priority, chunk_index = item
                    audio_size = 0
                elif len(item) == 5:
                    audio_path, group_id, priority, chunk_index, audio_size = item
                else:
                    raise ValueError(
                        f"Invalid audio tuple length {len(item)}. Expected 4-tuple (path, group, priority, chunk) or 5-tuple (path, group, priority, chunk, size)."
                    )
            # heap format: (priority, counter, audio_path, group_id, priority, chunk_index, audio_size)
            heapq.heappush(
                self._heap,
                (priority, self._counter, audio_path, group_id, priority, chunk_index, audio_size),
            )
            self._counter += 1

    async def get(self) -> AudioItem:
        """Get highest priority item from queue (lowest priority number first)."""
        async with self._lock:
            if not self._heap:
                raise asyncio.QueueEmpty("Queue is empty")

            # Get item from heap: (priority, counter, audio_path, group_id, priority, chunk_index, audio_size)
            _, _, audio_path, group_id, priority, chunk_index, audio_size = heapq.heappop(self._heap)
            return AudioItem(audio_path, group_id, priority, chunk_index, audio_size)

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
