"""Queue management for voice handler."""

import asyncio
from typing import Any

from .queues import PriorityAudioQueue, SynthesisQueue


class QueueManager:
    """Manages synthesis and audio queues for voice handler."""

    def __init__(self) -> None:
        """Initialize queue manager."""
        super().__init__()
        self.synthesis_queue = SynthesisQueue(maxsize=100)
        self.audio_queue = PriorityAudioQueue()
        self.current_group_id: str | None = None
        self._recent_messages: list[int] = []
        self._synthesis_lock = asyncio.Lock()

    async def add_to_queue(self, message_data: dict[str, Any]) -> None:
        """Add message to synthesis queue with deduplication."""
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

        # Check queue size limits against actual maxsize
        maxsize = getattr(self.synthesis_queue, "maxsize", 100)
        if self.synthesis_queue.qsize() >= maxsize:
            logger.warning(
                f"🎤 QUEUE: Synthesis queue is full ({self.synthesis_queue.qsize()}/{maxsize}) - skipping message"
            )
            return

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
                    "total_chunks": len(message_data["chunks"]),
                    "message_hash": message_hash,
                }
                try:
                    self.synthesis_queue.put_nowait(item)
                except asyncio.QueueFull:
                    logger.warning(
                        f"🎤 QUEUE: Synthesis queue became full while adding (at chunk {i + 1}/{len(message_data['chunks'])}); stopping adds"
                    )
                    break
                logger.debug(
                    f"🎤 QUEUE: Added chunk {i + 1}/{len(message_data['chunks'])} to queue (size={self.synthesis_queue.qsize()}/{maxsize})"
                )

        logger.info(f"🎤 QUEUE: Successfully queued message with {len(message_data['chunks'])} chunks from {message_data.get('username', 'Unknown')}")

    async def skip_current(self) -> int:
        """Skip the current message group."""
        if not self.current_group_id:
            return 0

        skipped = await self.audio_queue.clear_group(self.current_group_id)
        return skipped

    async def clear_group_from_synthesis_queue(self, group_id: str) -> int:
        """Clear items with specific group_id from synthesis queue."""
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
                self.synthesis_queue.put_nowait(remaining_item)

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
