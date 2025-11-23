from openai import OpenAI

from ..config import settings

client = OpenAI(api_key=settings.openai_api_key)


async def simple_chat_completion(messages: list[dict], *, max_tokens: int | None = None) -> str:
    """
    Простейшая обёртка для чат-комплишена.
    В следующих этапах будет настроен полноценный pipeline.
    """
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content or ""
