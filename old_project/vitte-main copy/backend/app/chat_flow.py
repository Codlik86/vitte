from .services.chat_flow import (  # noqa: F401,F403
    ChatResult,
    GreetingResult,
    generate_chat_reply,
    generate_greeting_reply,
)

# Проксирующий модуль, чтобы py_compile и импорты, ожидающие app.chat_flow, не падали.
