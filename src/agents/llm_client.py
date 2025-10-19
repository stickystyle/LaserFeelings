# ABOUTME: Shared LLM client wrapper with retry logic and error handling.
# ABOUTME: Provides async interface to OpenAI GPT-4o with exponential backoff.

from typing import Any

from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from src.agents.exceptions import LLMCallFailed


class LLMClient:
    """
    Shared LLM client wrapper for consistent OpenAI API interactions.

    Provides async interface with automatic retries and error handling.
    """

    def __init__(self, client: AsyncOpenAI, model: str = "gpt-4o"):
        """
        Initialize LLM client wrapper.

        Args:
            client: AsyncOpenAI client instance
            model: OpenAI model to use (default: gpt-4o)
        """
        self.client = client
        self.model = model

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def call(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        response_format: dict[str, str] | None = None,
        timeout: float = 20.0,
    ) -> str:
        """
        Call OpenAI LLM with retry logic.

        Args:
            system_prompt: System message defining agent role/behavior
            user_prompt: User message with specific task
            temperature: LLM temperature for response variation (default: 0.7)
            response_format: Optional response format (e.g., {"type": "json_object"})
            timeout: Request timeout in seconds (default: 20.0)

        Returns:
            LLM response content

        Raises:
            LLMCallFailed: When all retry attempts fail
        """
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]

            kwargs: dict[str, Any] = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "timeout": timeout,
            }

            if response_format:
                kwargs["response_format"] = response_format

            response = await self.client.chat.completions.create(**kwargs)
            return response.choices[0].message.content or ""

        except Exception as e:
            raise LLMCallFailed(f"OpenAI API call failed: {e}") from e
