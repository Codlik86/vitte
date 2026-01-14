from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    env: str = "dev"

    telegram_bot_token: str
    telegram_bot_username: str
    telegram_webhook_secret: str

    backend_host: str = "0.0.0.0"
    backend_port: int = 8000

    database_url: str

    qdrant_url: str | None = None
    qdrant_api_key: str | None = None

    openai_api_key: str

    yookassa_shop_id: str | None = None
    yookassa_secret_key: str | None = None

    stars_provider_token: str | None = None

    free_messages_limit: int = 15

    miniapp_url: str = "https://vitte-pi.vercel.app"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


def get_settings() -> Settings:
    return Settings()


settings = get_settings()
