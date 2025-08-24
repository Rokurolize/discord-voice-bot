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

        # Check queue size limits
        if self.synthesis_queue.qsize() >= 100:
            logger.warning(f"🎤 QUEUE: Synthesis queue is full ({self.synthesis_queue.qsize()}/100) - skipping message")
            return

        logger.debug(f"🎤 QUEUE: Adding {len(message_data['chunks'])} chunks to synthesis queue")

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
            await self.synthesis_queue.put(item)
            logger.debug(f"🎤 QUEUE: Added chunk {i + 1}/{len(message_data['chunks'])} to queue")

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
        temp_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=self.synthesis_queue.maxsize)

        # Filter out items with the specified group_id
        while not self.synthesis_queue.empty():
            try:
                queue_item: dict[str, Any] = await asyncio.wait_for(self.synthesis_queue.get(), timeout=0.1)
                if queue_item.get("group_id") != group_id:
                    await temp_queue.put(queue_item)
            except TimeoutError:
                break

        # Put remaining items back
        while not temp_queue.empty():
            try:
                remaining_item: dict[str, Any] = await asyncio.wait_for(temp_queue.get(), timeout=0.1)
                await self.synthesis_queue.put(remaining_item)
            except TimeoutError:
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
