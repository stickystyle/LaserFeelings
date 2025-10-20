# ABOUTME: Redis database cleanup utility for fresh CLI session initialization.
# ABOUTME: Flushes all Redis data (messages, queues, state) while preserving Neo4j graph memory.

from loguru import logger
from redis import Redis, RedisError


def cleanup_redis_for_new_session(redis_client: Redis) -> dict:
    """
    Clean Redis database to ensure fresh session state.

    Flushes all data from the current Redis database, including:
    - Message queues (OOC, IC, P2C channels)
    - RQ job queues
    - Turn state
    - Session state

    NOTE: This does NOT affect Neo4j graph memory, which persists across sessions.

    Args:
        redis_client: Connected Redis client instance

    Returns:
        Dict with success status and message:
        - {"success": True, "message": "..."}  on success
        - {"success": False, "message": "..."}  on error

    Examples:
        >>> from redis import Redis
        >>> redis_client = Redis.from_url("redis://localhost:6379")
        >>> result = cleanup_redis_for_new_session(redis_client)
        >>> result["success"]
        True
    """
    try:
        logger.info("Cleaning Redis database for new session")
        redis_client.flushdb()
        logger.info("Redis database cleaned successfully")

        return {
            "success": True,
            "message": "Redis cleaned - starting fresh session"
        }

    except RedisError as e:
        logger.error(f"Failed to clean Redis database: {e}")
        return {
            "success": False,
            "message": f"Failed to clean Redis: {e}"
        }

    except Exception as e:
        logger.error(f"Unexpected error during Redis cleanup: {e}")
        return {
            "success": False,
            "message": f"Unexpected error during cleanup: {e}"
        }
