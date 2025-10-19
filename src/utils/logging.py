# ABOUTME: Structured logging configuration using loguru for research analysis.
# ABOUTME: Supports context fields (timestamp, phase, agent_id, session_number) and file/console output.

import sys
from pathlib import Path
from typing import Any

from loguru import logger


# Default log format with structured context
DEFAULT_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    "<level>{message}</level> | "
    "{extra}"
)


def setup_logging(
    log_level: str = "INFO",
    log_dir: str | Path | None = None,
    console_output: bool = True,
    file_output: bool = True,
    format_string: str | None = None,
    rotation: str = "100 MB",
    retention: str = "30 days",
    compression: str = "zip"
) -> None:
    """
    Configure loguru for structured logging with research analysis support.

    This setup enables:
    - Structured context fields via logger.bind()
    - Console output with color formatting
    - File output with rotation and compression
    - Multiple log levels (DEBUG, INFO, WARNING, ERROR)

    Usage:
        >>> setup_logging(log_level="DEBUG", log_dir="logs")
        >>> logger = get_logger()
        >>> logger.info("Turn started", phase="DM_NARRATION", session=5)

    Args:
        log_level: Minimum log level ("DEBUG", "INFO", "WARNING", "ERROR")
        log_dir: Directory for log files (default: "logs" in project root)
        console_output: Enable console logging (default: True)
        file_output: Enable file logging (default: True)
        format_string: Custom format string (default: structured format)
        rotation: When to rotate log files (default: "100 MB")
        retention: How long to keep old logs (default: "30 days")
        compression: Compression for rotated logs (default: "zip")

    Returns:
        None

    Raises:
        ValueError: If log_level is invalid
    """
    # Validate log level
    valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
    log_level = log_level.upper()
    if log_level not in valid_levels:
        raise ValueError(
            f"Invalid log level: '{log_level}'. "
            f"Must be one of: {', '.join(valid_levels)}"
        )

    # Remove default handler
    logger.remove()

    # Use default format if not provided
    fmt = format_string or DEFAULT_FORMAT

    # Add console handler
    if console_output:
        logger.add(
            sys.stderr,
            format=fmt,
            level=log_level,
            colorize=True,
            backtrace=True,
            diagnose=True,
        )

    # Add file handler
    if file_output:
        # Determine log directory
        if log_dir is None:
            log_dir = Path("logs")
        else:
            log_dir = Path(log_dir)

        # Create log directory if it doesn't exist
        log_dir.mkdir(parents=True, exist_ok=True)

        # Add rotating file handler
        log_file = log_dir / "ttrpg_ai_{time:YYYY-MM-DD}.log"
        logger.add(
            str(log_file),
            format=fmt,
            level=log_level,
            rotation=rotation,
            retention=retention,
            compression=compression,
            backtrace=True,
            diagnose=True,
            enqueue=True,  # Thread-safe
        )

    logger.info(
        f"Logging configured: level={log_level}, "
        f"console={console_output}, file={file_output}"
    )


def get_logger() -> Any:
    """
    Get configured loguru logger instance.

    Usage:
        >>> logger = get_logger()
        >>> logger.info("Game started", session=1)
        >>> logger = logger.bind(phase="DM_NARRATION", agent_id="agent_alex")
        >>> logger.info("Turn started", turn=23)

    Returns:
        Configured loguru logger instance
    """
    return logger


def log_turn_event(
    message: str,
    phase: str,
    session_number: int,
    turn_number: int,
    agent_id: str | None = None,
    level: str = "INFO",
    **extra_context: Any
) -> None:
    """
    Convenience function to log turn events with standard context fields.

    This function automatically includes the standard research context fields:
    - phase: Current game phase (e.g., "DM_NARRATION", "STRATEGIC_INTENT")
    - session: Session number
    - turn: Turn number
    - agent_id: Optional agent identifier

    Usage:
        >>> log_turn_event(
        ...     "Character performed action",
        ...     phase="CHARACTER_ACTION",
        ...     session_number=5,
        ...     turn_number=23,
        ...     agent_id="agent_alex",
        ...     action="attempt repair"
        ... )

    Args:
        message: Log message
        phase: Current game phase
        session_number: Session number
        turn_number: Turn number
        agent_id: Optional agent identifier
        level: Log level (default: "INFO")
        **extra_context: Additional context fields

    Returns:
        None
    """
    # Build context
    context = {
        "phase": phase,
        "session": session_number,
        "turn": turn_number,
        **extra_context
    }

    if agent_id:
        context["agent_id"] = agent_id

    # Get logger and bind context
    bound_logger = logger.bind(**context)

    # Log at appropriate level
    level = level.upper()
    if level == "DEBUG":
        bound_logger.debug(message)
    elif level == "INFO":
        bound_logger.info(message)
    elif level == "WARNING":
        bound_logger.warning(message)
    elif level == "ERROR":
        bound_logger.error(message)
    else:
        bound_logger.info(message)


def log_phase_transition(
    from_phase: str,
    to_phase: str,
    session_number: int,
    turn_number: int,
    duration_ms: float | None = None
) -> None:
    """
    Log a phase transition with timing information.

    Usage:
        >>> log_phase_transition(
        ...     from_phase="DM_NARRATION",
        ...     to_phase="MEMORY_RETRIEVAL",
        ...     session_number=5,
        ...     turn_number=23,
        ...     duration_ms=150.5
        ... )

    Args:
        from_phase: Previous phase
        to_phase: New phase
        session_number: Session number
        turn_number: Turn number
        duration_ms: Optional duration of previous phase in milliseconds

    Returns:
        None
    """
    context = {
        "from_phase": from_phase,
        "to_phase": to_phase,
        "session": session_number,
        "turn": turn_number,
    }

    if duration_ms is not None:
        context["duration_ms"] = duration_ms

    logger.bind(**context).info(
        f"Phase transition: {from_phase} -> {to_phase}"
    )


def log_memory_operation(
    operation: str,
    agent_id: str,
    session_number: int,
    query: str | None = None,
    result_count: int | None = None,
    **extra_context: Any
) -> None:
    """
    Log memory operations (query, store, corruption).

    Usage:
        >>> log_memory_operation(
        ...     operation="query",
        ...     agent_id="agent_alex",
        ...     session_number=5,
        ...     query="merchant negotiations",
        ...     result_count=3
        ... )

    Args:
        operation: Operation type ("query", "store", "corrupt")
        agent_id: Agent performing operation
        session_number: Session number
        query: Optional query string
        result_count: Optional number of results
        **extra_context: Additional context fields

    Returns:
        None
    """
    context = {
        "operation": operation,
        "agent_id": agent_id,
        "session": session_number,
        **extra_context
    }

    if query:
        context["query"] = query

    if result_count is not None:
        context["result_count"] = result_count

    logger.bind(**context).info(f"Memory operation: {operation}")
