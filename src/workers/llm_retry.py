# ABOUTME: Exponential backoff retry decorator for LLM API calls in RQ workers.
# ABOUTME: Handles transient failures with 5 retries and structured logging.

from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

from loguru import logger
from openai import APIError, APITimeoutError, RateLimitError
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

# Type variable for generic function decoration
F = TypeVar("F", bound=Callable[..., Any])


def llm_retry(func: F) -> F:
    """
    Retry decorator for LLM API calls with exponential backoff.

    Retries on OpenAI API errors with exponential backoff:
    - 5 retry attempts
    - Wait: 1s min, 60s max, exponential multiplier=1
    - Retries on: APIError, APITimeoutError, RateLimitError
    - Logs each retry attempt with structured logging

    Usage:
        @llm_retry
        async def call_openai_api(...):
            # Your LLM call here
            pass

    Args:
        func: Async function to wrap with retry logic

    Returns:
        Wrapped function with retry behavior
    """
    # Apply tenacity retry decorator with OpenAI-specific exceptions
    retrying_decorator = retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=1, max=60),
        retry=retry_if_exception_type((APIError, APITimeoutError, RateLimitError)),
        before_sleep=before_sleep_log(logger, "WARNING"),
        reraise=True,
    )

    @wraps(func)
    async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
        """Async wrapper that applies retry logic."""
        @retrying_decorator
        async def _retry_call() -> Any:
            try:
                return await func(*args, **kwargs)
            except (APIError, APITimeoutError, RateLimitError) as e:
                logger.warning(
                    f"LLM API call failed in {func.__name__}: {type(e).__name__}: {e}"
                )
                raise
            except Exception as e:
                # Non-retryable errors - log and raise immediately
                logger.error(
                    f"Non-retryable error in {func.__name__}: {type(e).__name__}: {e}"
                )
                raise

        return await _retry_call()

    @wraps(func)
    def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
        """Sync wrapper that applies retry logic."""
        @retrying_decorator
        def _retry_call() -> Any:
            try:
                return func(*args, **kwargs)
            except (APIError, APITimeoutError, RateLimitError) as e:
                logger.warning(
                    f"LLM API call failed in {func.__name__}: {type(e).__name__}: {e}"
                )
                raise
            except Exception as e:
                # Non-retryable errors - log and raise immediately
                logger.error(
                    f"Non-retryable error in {func.__name__}: {type(e).__name__}: {e}"
                )
                raise

        return _retry_call()

    # Return appropriate wrapper based on whether function is async
    import inspect
    if inspect.iscoroutinefunction(func):
        return async_wrapper  # type: ignore
    else:
        return sync_wrapper  # type: ignore
