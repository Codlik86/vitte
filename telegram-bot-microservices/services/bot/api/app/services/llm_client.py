"""
LLM Client service for communicating with LLM Gateway

Uses OpenAI-compatible API to send chat completions requests
"""

import httpx
import logging
from typing import Optional

from app.config import config

logger = logging.getLogger(__name__)


class LLMClient:
    """Client for LLM Gateway API"""

    def __init__(self):
        self.base_url = config.llm_gateway_url.rstrip("/")
        self.timeout = 60.0  # LLM responses can be slow

    async def chat_completion(
        self,
        messages: list[dict],
        model: str = "deepseek/deepseek-v3.2",
        temperature: float = 0.8,
        max_tokens: int = 1024,
        stream: bool = False,
        presence_penalty: Optional[float] = None,
        frequency_penalty: Optional[float] = None,
    ) -> Optional[str]:
        """
        Send chat completion request to LLM Gateway.

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model to use (default: deepseek-v3.2)
            temperature: Sampling temperature (0.0 - 2.0)
            max_tokens: Maximum tokens in response
            stream: Whether to stream response (not implemented yet)
            presence_penalty: Penalty for token presence (-2.0 to 2.0, positive = new topics)
            frequency_penalty: Penalty for frequent tokens (-2.0 to 2.0, positive = less repetition)

        Returns:
            Assistant's response text or None if failed
        """
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
        }

        # Добавляем опциональные параметры против повторений (OpenAI-compatible)
        if presence_penalty is not None:
            payload["presence_penalty"] = presence_penalty
        if frequency_penalty is not None:
            payload["frequency_penalty"] = frequency_penalty

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/v1/chat/completions",
                    json=payload,
                    timeout=self.timeout,
                )

                if response.status_code != 200:
                    logger.error(
                        f"LLM Gateway error: {response.status_code} - {response.text}"
                    )
                    return None

                data = response.json()
                choices = data.get("choices", [])

                if not choices:
                    logger.error("LLM Gateway returned empty choices")
                    return None

                return choices[0].get("message", {}).get("content")

        except httpx.TimeoutException:
            logger.error("LLM Gateway request timed out")
            return None
        except httpx.RequestError as e:
            logger.error(f"LLM Gateway request error: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error calling LLM Gateway: {e}")
            return None

    async def health_check(self) -> bool:
        """Check if LLM Gateway is healthy."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/v1/health",
                    timeout=5.0,
                )
                return response.status_code == 200
        except Exception:
            return False


# Global client instance
llm_client = LLMClient()
