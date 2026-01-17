"""
Memory indexing tasks for Qdrant
"""
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime

from app.celery_app import celery_app
from shared.utils import get_logger, qdrant_client

logger = get_logger(__name__)


def _index_message_sync(
    user_id: int,
    content: str,
    message_id: Optional[int] = None,
    dialog_id: Optional[int] = None,
    role: str = "user"
) -> Dict[str, Any]:
    """
    Synchronous implementation of message indexing

    Args:
        user_id: User ID
        content: Message content
        message_id: Message ID from PostgreSQL
        dialog_id: Dialog ID
        role: Message role (user/assistant)

    Returns:
        Dict with indexing result
    """
    try:
        # Skip very short messages
        if len(content.strip()) < 10:
            logger.debug(f"Skipping short message for user {user_id}")
            return {
                "status": "skipped",
                "reason": "message_too_short",
                "user_id": user_id
            }

        # Index in Qdrant
        point_id = qdrant_client.store_memory(
            user_id=user_id,
            content=content,
            message_id=message_id,
            dialog_id=dialog_id,
            role=role,
            metadata={
                "indexed_at": datetime.utcnow().isoformat()
            }
        )

        logger.info(
            f"Message indexed for user {user_id}",
            extra={
                "point_id": point_id,
                "message_id": message_id,
                "dialog_id": dialog_id,
                "role": role
            }
        )

        return {
            "status": "success",
            "point_id": point_id,
            "user_id": user_id,
            "message_id": message_id,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to index message for user {user_id}: {e}", exc_info=True)
        raise


@celery_app.task(name="memory.index_message", bind=True, max_retries=3)
def index_message(
    self,
    user_id: int,
    content: str,
    message_id: Optional[int] = None,
    dialog_id: Optional[int] = None,
    role: str = "user"
):
    """
    Index a message in Qdrant for long-term memory

    Args:
        user_id: User ID
        content: Message content
        message_id: Message ID from PostgreSQL
        dialog_id: Dialog ID
        role: Message role (user/assistant)

    Returns:
        Dict with indexing result
    """
    try:
        return _index_message_sync(
            user_id=user_id,
            content=content,
            message_id=message_id,
            dialog_id=dialog_id,
            role=role
        )
    except Exception as e:
        logger.error(f"Index message task failed: {e}", exc_info=True)
        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=30 * (2 ** self.request.retries))


def _delete_user_memories_sync(user_id: int) -> Dict[str, Any]:
    """
    Synchronous implementation of memory deletion

    Args:
        user_id: User ID

    Returns:
        Dict with deletion result
    """
    try:
        deleted_count = qdrant_client.delete_user_memories(user_id)

        logger.info(
            f"Deleted {deleted_count} memories for user {user_id}",
            extra={"user_id": user_id, "deleted": deleted_count}
        )

        return {
            "status": "success",
            "deleted": deleted_count,
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to delete memories for user {user_id}: {e}", exc_info=True)
        raise


@celery_app.task(name="memory.delete_user_memories", bind=True, max_retries=3)
def delete_user_memories(self, user_id: int):
    """
    Delete all memories for a user from Qdrant

    Args:
        user_id: User ID

    Returns:
        Dict with deletion result
    """
    try:
        return _delete_user_memories_sync(user_id)
    except Exception as e:
        logger.error(f"Delete memories task failed: {e}", exc_info=True)
        raise self.retry(exc=e, countdown=30 * (2 ** self.request.retries))


@celery_app.task(name="memory.health_check")
def memory_health_check():
    """
    Check Qdrant health

    Returns:
        Dict with health status
    """
    try:
        is_healthy = qdrant_client.health_check()
        return {
            "status": "healthy" if is_healthy else "unhealthy",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Memory health check failed: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }
