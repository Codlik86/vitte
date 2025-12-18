from pydantic_settings import BaseSettings, SettingsConfigDict

OPENROUTER_BASE_URL = "https://api.proxyapi.ru/openrouter/v1"
DEFAULT_VITTE_MODEL = "deepseek/deepseek-v3.2"


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

    proxyapi_api_key: str
    openrouter_base_url: str = OPENROUTER_BASE_URL
    vitte_llm_model: str = DEFAULT_VITTE_MODEL
    vitte_llm_model_strong: str = DEFAULT_VITTE_MODEL

    yookassa_shop_id: str | None = None
    yookassa_secret_key: str | None = None

    free_messages_limit: int = 15

    miniapp_url: str = "https://vitte-pi.vercel.app"

    comfyui_base_url: str | None = None
    comfyui_timeout_seconds: int = 120
    comfyui_concurrency: int = 2
    comfyui_workflow_name: str | None = None
    comfyui_default_checkpoint: str | None = "models/checkpoints/huslyorealismxl_v2.safetensors"
    comfyui_default_diffusion_model: str | None = "models/diffusion_models/z_image_turbo_bf16.safetensors"
    comfyui_default_text_encoder: str | None = "models/text_encoders/qwen_3_4b.safetensors"
    comfyui_default_vae: str | None = "models/vae/ae.safetensors"
    comfyui_healthcheck_enabled: bool = False

    image_every_n_bot_replies: int = 3
    image_cooldown_seconds: int = 120
    image_enabled: bool = True

    vitte_rel_test_mode: bool = False
    vitte_rel_test_mode_behavior: str = "ZERO"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


def get_settings() -> Settings:
    return Settings()


settings = get_settings()
