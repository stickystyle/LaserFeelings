# ABOUTME: RQ queue configuration for AI TTRPG agent worker pools.
# ABOUTME: Defines queue creation, timeout settings, and TTL policies for workers.

from typing import Any

from loguru import logger
from redis import Redis
from rq import Queue

# Queue names as constants
BASE_PERSONA_QUEUE = "base_persona"
CHARACTER_QUEUE = "character"
VALIDATION_QUEUE = "validation"

# Timeout settings (in seconds)
JOB_TIMEOUT = 30  # Maximum job execution time
RESULT_TTL = 300  # Keep successful results for 5 minutes
FAILURE_TTL = 600  # Keep failed job info for 10 minutes (debugging)


def create_redis_connection(host: str = "localhost", port: int = 6379, db: int = 0) -> Redis:
    """
    Create Redis connection for RQ workers.

    Args:
        host: Redis host (default: localhost)
        port: Redis port (default: 6379)
        db: Redis database number (default: 0)

    Returns:
        Redis connection instance

    Raises:
        ConnectionError: When Redis is not accessible
    """
    try:
        redis_conn = Redis(host=host, port=port, db=db, decode_responses=False)
        # Test connection
        redis_conn.ping()
        logger.info(f"Redis connection established: {host}:{port} (db={db})")
        return redis_conn
    except Exception as e:
        logger.error(f"Failed to connect to Redis at {host}:{port}: {e}")
        raise ConnectionError(f"Redis connection failed: {e}") from e


def create_queue(
    queue_name: str,
    redis_conn: Redis,
    default_timeout: int = JOB_TIMEOUT,
) -> Queue:
    """
    Create RQ queue with configured timeout and TTL settings.

    Args:
        queue_name: Name of the queue (e.g., 'base_persona', 'character')
        redis_conn: Redis connection instance
        default_timeout: Default job timeout in seconds (default: JOB_TIMEOUT)

    Returns:
        Configured RQ Queue instance
    """
    queue = Queue(
        queue_name,
        connection=redis_conn,
        default_timeout=default_timeout,
    )
    logger.info(
        f"Created queue '{queue_name}' with timeout={default_timeout}s, "
        f"result_ttl={RESULT_TTL}s, failure_ttl={FAILURE_TTL}s"
    )
    return queue


def get_base_persona_queue(redis_conn: Redis) -> Queue:
    """
    Get or create base_persona queue for BasePersonaAgent workers.

    Args:
        redis_conn: Redis connection instance

    Returns:
        Queue for base_persona workers
    """
    return create_queue(BASE_PERSONA_QUEUE, redis_conn)


def get_character_queue(redis_conn: Redis) -> Queue:
    """
    Get or create character queue for CharacterAgent workers.

    Args:
        redis_conn: Redis connection instance

    Returns:
        Queue for character workers
    """
    return create_queue(CHARACTER_QUEUE, redis_conn)


def get_validation_queue(redis_conn: Redis) -> Queue:
    """
    Get or create validation queue for action validation workers.

    Args:
        redis_conn: Redis connection instance

    Returns:
        Queue for validation workers
    """
    return create_queue(VALIDATION_QUEUE, redis_conn)


def enqueue_job(
    queue: Queue,
    func: Any,
    args: tuple = (),
    kwargs: dict | None = None,
    job_timeout: int = JOB_TIMEOUT,
    result_ttl: int = RESULT_TTL,
    failure_ttl: int = FAILURE_TTL,
) -> Any:
    """
    Enqueue a job with standard timeout and TTL settings.

    Args:
        queue: RQ Queue instance
        func: Worker function to execute
        args: Positional arguments for func
        kwargs: Keyword arguments for func
        job_timeout: Maximum execution time in seconds
        result_ttl: Time to keep successful results (seconds)
        failure_ttl: Time to keep failed job info (seconds)

    Returns:
        RQ Job instance
    """
    if kwargs is None:
        kwargs = {}

    job = queue.enqueue(
        func,
        args=args,
        kwargs=kwargs,
        job_timeout=job_timeout,
        result_ttl=result_ttl,
        failure_ttl=failure_ttl,
    )

    logger.debug(
        f"Enqueued job {job.id} on queue '{queue.name}': {func.__name__} "
        f"(timeout={job_timeout}s)"
    )
    return job


def initialize_all_queues(redis_conn: Redis) -> dict[str, Queue]:
    """
    Initialize all worker queues for the AI TTRPG system.

    Args:
        redis_conn: Redis connection instance

    Returns:
        Dictionary mapping queue names to Queue instances
    """
    queues = {
        BASE_PERSONA_QUEUE: get_base_persona_queue(redis_conn),
        CHARACTER_QUEUE: get_character_queue(redis_conn),
        VALIDATION_QUEUE: get_validation_queue(redis_conn),
    }

    logger.info(f"Initialized {len(queues)} worker queues: {list(queues.keys())}")
    return queues
