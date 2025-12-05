from openai import OpenAI

from ..config import settings, OPENROUTER_BASE_URL
from ..logging_config import logger

openrouter_client = OpenAI(
    api_key=settings.proxyapi_api_key,
    base_url=settings.openrouter_base_url or OPENROUTER_BASE_URL,
)
# Legacy client: не используется в Vitte, оставлен для совместимости.
legacy_openai_client = OpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None


async def simple_chat_completion(
    messages: list[dict],
    *,
    max_tokens: int | None = None,
    temperature: float | None = None,
    model: str | None = None,
) -> str:
    """
    Простейшая обёртка для чат-комплишена.
    В следующих этапах будет настроен полноценный pipeline.
    """
    try:
        response = openrouter_client.chat.completions.create(
            model=model or settings.vitte_llm_model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return response.choices[0].message.content or ""
    except Exception as exc:  # noqa: BLE001 - логируем любые ошибки клиента
        logger.error("LLM completion failed: %s", exc)
        raise
