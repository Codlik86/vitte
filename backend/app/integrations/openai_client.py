from openai import OpenAI

from ..config import settings
from ..logging_config import logger

client = OpenAI(api_key=settings.openai_api_key)


async def simple_chat_completion(messages: list[dict], *, max_tokens: int | None = None) -> str:
    """
    Простейшая обёртка для чат-комплишена.
    В следующих этапах будет настроен полноценный pipeline.
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content or ""
    except Exception as exc:  # noqa: BLE001 - логируем любые ошибки клиента
        logger.error("LLM completion failed: %s", exc)
        raise
