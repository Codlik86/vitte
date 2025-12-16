from openai import OpenAI

from ..config import settings, OPENROUTER_BASE_URL
from ..logging_config import logger

# LLM client via ProxyAPI + OpenRouter targeting DeepSeek models.
llm_client = OpenAI(
    api_key=settings.proxyapi_api_key,
    base_url=settings.openrouter_base_url or OPENROUTER_BASE_URL,
    timeout=30,
    max_retries=1,
)


async def simple_chat_completion(
    messages: list[dict],
    *,
    max_tokens: int | None = None,
    temperature: float | None = None,
    model: str | None = None,
) -> str:
    """
    Minimal chat-completions wrapper for Vitte.
    """
    try:
        response = llm_client.chat.completions.create(
            model=model or settings.vitte_llm_model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return response.choices[0].message.content or ""
    except Exception as exc:  # noqa: BLE001 - log any client errors
        logger.error("LLM completion failed: %s", exc)
        raise
