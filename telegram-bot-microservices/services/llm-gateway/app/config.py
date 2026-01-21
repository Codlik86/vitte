"""
LLM Gateway Configuration
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """LLM Gateway settings"""

    # Service
    service_name: str = "llm-gateway"
    host: str = "0.0.0.0"
    port: int = 8001

    # DeepSeek via ProxyAPI
    proxyapi_api_key: str
    openrouter_base_url: str = "https://api.proxyapi.ru/openrouter/v1"
    vitte_llm_model: str = "deepseek/deepseek-v3.2"
    vitte_llm_model_strong: str = "deepseek/deepseek-v3.2"

    # LLM Client settings
    llm_timeout: int = 60  # seconds
    llm_max_retries: int = 3
    llm_backoff_factor: float = 2.0

    # Redis cache
    redis_url: str = "redis://redis:6379/1"
    cache_ttl: int = 3600  # 1 hour for identical prompts
    cache_enabled: bool = True

    # Rate limiting
    rate_limit_requests_per_minute: int = 100
    rate_limit_enabled: bool = True

    # Circuit breaker
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_timeout: int = 60  # seconds
    circuit_breaker_enabled: bool = True

    # Streaming
    streaming_chunk_size: int = 50  # tokens per chunk
    streaming_enabled: bool = True

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
