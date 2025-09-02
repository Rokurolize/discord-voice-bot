"""Queue management for voice handler."""

import asyncio
from typing import Any

from .queues import PriorityAudioQueue, SynthesisQueue


class QueueManager:
    """Manages synthesis and audio queues for voice handler."""

    def __init__(self) -> None:
        """
        Create a QueueManager and initialize its internal queues, state, and synchronization primitives.

        Initializes:
        - synthesis_queue: SynthesisQueue with a maxsize of 100 for pending synthesis tasks.
        - audio_queue: PriorityAudioQueue for queued audio playback items.
        - current_group_id: Optional[str] tracking the active group; starts as None.
        - _recent_messages: list[int] used as a sliding-window cache of recent message hashes for deduplication.
        - _synthesis_lock: asyncio.Lock used to serialize non-blocking insertions into the synthesis queue.
        """
        super().__init__()
        self.synthesis_queue = SynthesisQueue(maxsize=100)
        self.audio_queue = PriorityAudioQueue()
        self.current_group_id: str | None = None
        self._recent_messages: list[int] = []
        self._synthesis_lock = asyncio.Lock()

    async def add_to_queue(self, message_data: dict[str, Any]) -> None:
        """
        Add a message's chunks to the synthesis queue, skipping duplicates and honoring queue capacity.

        Expects message_data to contain a "chunks" iterable of text chunks. Also reads (if present) "original_content" to detect duplicates, "user_id", "username", and "group_id". Behavior:
        - Skips queuing if "chunks" is missing or if the message's content hash was seen recently (deduplication).
        - Maintains a short (recent) history of message hashes to prevent re-queuing the same content.
        - Respects the synthesis queue's maxsize; if the queue is full the message (or remaining chunks) will not be enqueued.
        - Enqueues each chunk as a dict containing text, user info, group_id, chunk index/total, and the message hash.

        This method is asynchronous and uses an internal lock to protect the non-blocking enqueue critical section. It does not return a value.
        """
        from loguru import logger

        logger.debug(f"🎤 QUEUE: add_to_queue called with message_data keys: {list(message_data.keys())}")
        logger.debug(f"🎤 QUEUE: message_data content preview: {str(message_data.get('original_content', ''))[:100]}")

        if not message_data.get("chunks"):
            logger.warning("🎤 QUEUE: No 'chunks' key found in message_data - message will not be queued")
            logger.warning(f"🎤 QUEUE: Available keys: {list(message_data.keys())}")
            return

        logger.debug(f"🎤 QUEUE: Found {len(message_data['chunks'])} chunks to process")

        # Check for message deduplication
        message_hash = hash(message_data.get("original_content", ""))
        if message_hash in self._recent_messages:
            logger.debug("🎤 QUEUE: Message is duplicate - skipping")
            return

        # Keep only last 100 message hashes
        if len(self._recent_messages) > 100:
            _ = self._recent_messages.pop(0)
        self._recent_messages.append(message_hash)

        # Check if we have any capacity for chunks
        maxsize = getattr(self.synthesis_queue, "maxsize", 100)
        current_size = self.synthesis_queue.qsize()
        available_capacity = maxsize - current_size

        if available_capacity <= 0:
            logger.warning(
                f"🎤 QUEUE: Synthesis queue is full ({current_size}/{maxsize}) - skipping entire message"
            )
            return

        # Warn if we might not fit all chunks
        chunk_count = len(message_data["chunks"])
        if available_capacity < chunk_count:
            logger.info(
                f"🎤 QUEUE: Only {available_capacity} slots available for {chunk_count} chunks - some may be dropped"
            )

        logger.debug(f"🎤 QUEUE: Adding {len(message_data['chunks'])} chunks to synthesis queue")

        # Lock only the non-blocking critical section; never await under the lock
        async with self._synthesis_lock:
            for i, chunk in enumerate(message_data["chunks"]):
                item = {
                    "text": chunk,
                    "user_id": message_data.get("user_id"),
                    "username": message_data.get("username", "Unknown"),
                    "group_id": message_data.get("group_id", f"msg_{id(message_data)}"),
                    "chunk_index": i,
                    "total_chunks": chunk_count,
                    "message_hash": message_hash,
                }
                try:
                    self.synthesis_queue.put_nowait(item)
                except asyncio.QueueFull:
                    logger.warning(
                        f"🎤 QUEUE: Synthesis queue became full after adding {i} chunks (failed at chunk {i + 1}/{chunk_count}); stopping"
                    )
                    break
                logger.debug(
                    f"🎤 QUEUE: Added chunk {i + 1}/{chunk_count} to queue (size={self.synthesis_queue.qsize()}/{maxsize})"
                )

        logger.info(f"🎤 QUEUE: Successfully queued message with {len(message_data['chunks'])} chunks from {message_data.get('username', 'Unknown')}")

    async def skip_current(self) -> int:
        """Skip the current message group."""
        if not self.current_group_id:
            return 0

        skipped = await self.audio_queue.clear_group(self.current_group_id)
        return skipped

    async def clear_group_from_synthesis_queue(self, group_id: str) -> int:
        """
        Remove all items with the given group_id from the synthesis queue and return how many were removed.

        This acquires the manager's internal synthesis lock and performs a non-blocking drain/reinsert of queue items: items whose "group_id" does not match are kept and reinserted, preserving their relative order. Returns the number of items removed (original queue size minus final queue size).
        """
        # This is a simplified implementation - in real scenario,
        # you might need more sophisticated queue management
        original_size = self.synthesis_queue.qsize()
        # Use a temporary list to hold items we keep; reinsert without awaiting
        kept_items: list[dict[str, Any]] = []

        async with self._synthesis_lock:
            # Filter out items with the specified group_id
            while True:
                try:
                    queue_item = self.synthesis_queue.get_nowait()
                    if queue_item.get("group_id") != group_id:
                        kept_items.append(queue_item)
                except asyncio.QueueEmpty:
                    break

            # Put remaining items back without blocking while holding the lock
            for remaining_item in kept_items:
                try:
                    self.synthesis_queue.put_nowait(remaining_item)
                except asyncio.QueueFull:
                    # This should never happen (we removed at least as many as we're putting back)
                    # but log it just in case for debugging
                    from loguru import logger as _logger
                    _logger.error(
                        f"🎤 QUEUE: Unexpected QueueFull while restoring items during clear_group - item lost: {remaining_item}"
                    )
                    break

        return original_size - self.synthesis_queue.qsize()

    async def clear_group(self, group_id: str) -> int:
        """Clear a specific group from audio queue."""
        return await self.audio_queue.clear_group(group_id)

    async def clear_all(self) -> int:
        """Clear all queues."""
        total = self.synthesis_queue.qsize() + self.audio_queue.qsize()

        _ = await self.synthesis_queue.clear()
        _ = await self.audio_queue.clear()

        return total

    def get_queue_sizes(self) -> dict[str, int]:
        """Get current queue sizes."""
        return {"synthesis_queue_size": self.synthesis_queue.qsize(), "audio_queue_size": self.audio_queue.qsize(), "total_queue_size": self.synthesis_queue.qsize() + self.audio_queue.qsize()}

    def set_current_group(self, group_id: str | None) -> None:
        """Set the current group ID."""
        self.current_group_id = group_id

    def get_current_group(self) -> str | None:
        """Get the current group ID."""
        return self.current_group_id
