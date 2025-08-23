"""Task management for voice handler."""

import asyncio


class TaskManager:
    """Manages asyncio tasks for voice handler."""

    def __init__(self) -> None:
        """Initialize task manager."""
        super().__init__()
        self.tasks: list[asyncio.Task[None]] = []

    def add_task(self, task: asyncio.Task[None]) -> None:
        """Add a task to be managed."""
        self.tasks.append(task)

    def get_tasks(self) -> list[asyncio.Task[None]]:
        """Get list of managed tasks."""
        return self.tasks.copy()

    async def cleanup(self) -> None:
        """Cancel and cleanup all managed tasks."""
        for task in self.tasks:
            if not task.done():
                _ = task.cancel()

        # Wait for all tasks to complete cancellation
        if self.tasks:
            try:
                _ = await asyncio.gather(*self.tasks, return_exceptions=True)
            except Exception:
                pass  # Expected when tasks are cancelled

        self.tasks.clear()

    def get_task_count(self) -> int:
        """Get the number of managed tasks."""
        return len(self.tasks)

    def get_active_task_count(self) -> int:
        """Get the number of active (not done) tasks."""
        return len([task for task in self.tasks if not task.done()])
