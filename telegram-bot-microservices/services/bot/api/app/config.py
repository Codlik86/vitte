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
    
    # Database
    database_url: str = os.getenv("DATABASE_URL", "postgresql+asyncpg://vitte_user:password@postgres:5432/vitte_bot")
    
    # Redis
    redis_url: str = os.getenv("REDIS_URL", "redis://redis:6379/0")
    
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
