from openai import OpenAI

from ..config import settings

client = OpenAI(api_key=settings.openai_api_key)


async def simple_chat_completion(messages: list[dict]) -> str:
    """
    Простейшая обёртка для чат-комплишена.
    В следующих этапах будет настроен полноценный pipeline.
    """
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
    )
    return response.choices[0].message.content or ""
