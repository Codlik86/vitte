"""
API configuration
"""
import os
from pydantic_settings import BaseSettings


class APIConfig(BaseSettings):
    """API configuration from environment variables"""

    # API settings
    api_host: str = os.getenv("API_HOST", "0.0.0.0")
    api_port: int = int(os.getenv("API_PORT", 8000))
    api_workers: int = int(os.getenv("API_WORKERS", 4))

    # Bot token for invoice creation
    bot_token: str = os.getenv("BOT_TOKEN", "")

    # CryptoPay token
    cryptopay_token: str = os.getenv("CRYPTOPAY_TOKEN", "")

    # Database
    database_url: str = os.getenv("DATABASE_URL", "postgresql+asyncpg://vitte_user:password@postgres:5432/vitte_bot")
    
    # Redis
    redis_url: str = os.getenv("REDIS_URL", "redis://redis:6379/0")

    # LLM Gateway
    llm_gateway_url: str = os.getenv("LLM_GATEWAY_URL", "http://llm-gateway:8001")

    # OpenRouter (for embeddings)
    openrouter_api_key: str = os.getenv("OPENROUTER_API_KEY", "")
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "openai/text-embedding-3-small")

    # Qdrant
    qdrant_url: str = os.getenv("QDRANT_URL", "http://qdrant:6333")
    qdrant_collection: str = os.getenv("QDRANT_COLLECTION", "vitte_memories")
    
    # CORS
    cors_origins: str = os.getenv("CORS_ORIGINS", "http://localhost:3000")
    
    # Environment
    environment: str = os.getenv("ENVIRONMENT", "production")
    debug: bool = os.getenv("DEBUG", "False").lower() == "true"
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    
    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins from comma-separated string"""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global config instance
config = APIConfig()
