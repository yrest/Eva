"""Task queue management using Redis."""

import json
import uuid
from typing import Any, Dict, Optional

import redis
from redis import Redis

from .config import settings


class TaskQueue:
    """Redis-based task queue."""

    def __init__(self):
        """Initialize task queue."""
        self.redis_client: Redis = redis.from_url(
            settings.redis_url,
            decode_responses=True,
        )
        self.queue_name = settings.task_queue_name
        self.processing_queue = f"{self.queue_name}:processing"

    def enqueue(self, task_id: str, priority: int = 5) -> bool:
        """
        Add task to queue.

        Args:
            task_id: Task UUID
            priority: Priority (1=highest, 10=lowest)

        Returns:
            True if enqueued successfully
        """
        try:
            # Use sorted set for priority queue
            # Score is priority (lower = higher priority)
            self.redis_client.zadd(
                self.queue_name,
                {task_id: priority},
            )
            return True
        except Exception as e:
            print(f"Failed to enqueue task {task_id}: {e}")
            return False

    def dequeue(self) -> Optional[str]:
        """
        Get next task from queue (highest priority).

        Returns:
            Task UUID or None if queue is empty
        """
        try:
            # Get task with lowest score (highest priority)
            result = self.redis_client.zpopmin(self.queue_name, count=1)

            if not result:
                return None

            task_id = result[0][0]  # (task_id, score)

            # Move to processing queue
            self.redis_client.sadd(self.processing_queue, task_id)

            return task_id

        except Exception as e:
            print(f"Failed to dequeue task: {e}")
            return None

    def mark_completed(self, task_id: str) -> bool:
        """
        Mark task as completed and remove from processing queue.

        Args:
            task_id: Task UUID

        Returns:
            True if successful
        """
        try:
            self.redis_client.srem(self.processing_queue, task_id)
            return True
        except Exception as e:
            print(f"Failed to mark task {task_id} as completed: {e}")
            return False

    def requeue(self, task_id: str, priority: int = 5) -> bool:
        """
        Return task to queue (e.g., after failure).

        Args:
            task_id: Task UUID
            priority: Priority

        Returns:
            True if successful
        """
        try:
            # Remove from processing
            self.redis_client.srem(self.processing_queue, task_id)

            # Add back to queue
            return self.enqueue(task_id, priority)

        except Exception as e:
            print(f"Failed to requeue task {task_id}: {e}")
            return False

    def get_queue_size(self) -> int:
        """Get number of pending tasks."""
        try:
            return self.redis_client.zcard(self.queue_name)
        except Exception:
            return 0

    def get_processing_count(self) -> int:
        """Get number of tasks being processed."""
        try:
            return self.redis_client.scard(self.processing_queue)
        except Exception:
            return 0

    def health_check(self) -> bool:
        """Check Redis connection."""
        try:
            self.redis_client.ping()
            return True
        except Exception:
            return False

    def clear_queue(self) -> bool:
        """Clear all tasks from queue (admin operation)."""
        try:
            self.redis_client.delete(self.queue_name)
            self.redis_client.delete(self.processing_queue)
            return True
        except Exception:
            return False


# ============================================================================
# Task Context Cache
# ============================================================================


class TaskContextCache:
    """Cache for task execution context (temporary data during execution)."""

    def __init__(self):
        """Initialize context cache."""
        self.redis_client: Redis = redis.from_url(
            settings.redis_url,
            decode_responses=True,
        )
        self.key_prefix = "task:context:"
        self.ttl = 3600  # 1 hour

    def set_context(self, task_id: str, context: Dict[str, Any]) -> bool:
        """
        Store task execution context.

        Args:
            task_id: Task UUID
            context: Context data

        Returns:
            True if successful
        """
        try:
            key = f"{self.key_prefix}{task_id}"
            self.redis_client.setex(
                key,
                self.ttl,
                json.dumps(context),
            )
            return True
        except Exception as e:
            print(f"Failed to set context for task {task_id}: {e}")
            return False

    def get_context(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get task execution context.

        Args:
            task_id: Task UUID

        Returns:
            Context data or None
        """
        try:
            key = f"{self.key_prefix}{task_id}"
            data = self.redis_client.get(key)

            if data:
                return json.loads(data)
            return None

        except Exception as e:
            print(f"Failed to get context for task {task_id}: {e}")
            return None

    def delete_context(self, task_id: str) -> bool:
        """
        Delete task execution context.

        Args:
            task_id: Task UUID

        Returns:
            True if successful
        """
        try:
            key = f"{self.key_prefix}{task_id}"
            self.redis_client.delete(key)
            return True
        except Exception as e:
            print(f"Failed to delete context for task {task_id}: {e}")
            return False
