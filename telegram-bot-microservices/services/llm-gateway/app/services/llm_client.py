"""
LLM Client with retry logic and streaming support
"""
import asyncio
import time
from typing import List, AsyncIterator, Optional
from openai import AsyncOpenAI, APIError, APITimeoutError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)
import logging

from app.config import settings
from app.schemas.chat import Message

logger = logging.getLogger(__name__)


class LLMClient:
    """DeepSeek client via ProxyAPI with retry and streaming"""

    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.proxyapi_api_key,
            base_url=settings.openrouter_base_url,
            timeout=settings.llm_timeout,
            max_retries=0  # We handle retries manually with tenacity
        )
        self.default_model = settings.vitte_llm_model
        self.strong_model = settings.vitte_llm_model_strong

    @retry(
        stop=stop_after_attempt(settings.llm_max_retries),
        wait=wait_exponential(
            multiplier=settings.llm_backoff_factor,
            min=2,
            max=10
        ),
        retry=retry_if_exception_type((APITimeoutError, APIError)),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    async def complete(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Complete chat with retry logic

        Args:
            messages: List of chat messages
            model: Model to use (default: deepseek-v3.2)
            temperature: Sampling temperature
            max_tokens: Max tokens in response

        Returns:
            str: Assistant's response

        Raises:
            APIError: If all retries failed
        """
        try:
            response = await self.client.chat.completions.create(
                model=model or self.default_model,
                messages=[m.model_dump() for m in messages],
                temperature=temperature,
                max_tokens=max_tokens
            )

            content = response.choices[0].message.content
            logger.info(
                f"LLM completion success: model={model or self.default_model}, "
                f"tokens={response.usage.total_tokens if response.usage else 'N/A'}"
            )
            return content

        except (APITimeoutError, APIError) as e:
            logger.error(f"LLM API error: {e}")
            raise

    async def complete_stream(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> AsyncIterator[str]:
        """
        Complete chat with streaming

        Args:
            messages: List of chat messages
            model: Model to use
            temperature: Sampling temperature
            max_tokens: Max tokens in response

        Yields:
            str: Text chunks as they arrive

        Note:
            Streaming does NOT use retry logic - if it fails, it fails immediately
        """
        try:
            stream = await self.client.chat.completions.create(
                model=model or self.default_model,
                messages=[m.model_dump() for m in messages],
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True
            )

            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

            logger.info(f"LLM stream completed: model={model or self.default_model}")

        except (APITimeoutError, APIError) as e:
            logger.error(f"LLM stream error: {e}")
            raise

    async def check_health(self) -> bool:
        """
        Health check - try simple completion

        Returns:
            bool: True if LLM is responsive
        """
        try:
            test_messages = [
                Message(role="user", content="Hi")
            ]
            await asyncio.wait_for(
                self.complete(test_messages, max_tokens=5),
                timeout=5.0
            )
            return True
        except Exception as e:
            logger.warning(f"LLM health check failed: {e}")
            return False


# Singleton instance
llm_client = LLMClient()
