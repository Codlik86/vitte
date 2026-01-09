"""
Admin panel configuration
"""
import os
from pydantic_settings import BaseSettings


class AdminConfig(BaseSettings):
    """Admin configuration from environment variables"""
    
    # Admin settings
    admin_host: str = os.getenv("ADMIN_HOST", "0.0.0.0")
    admin_port: int = int(os.getenv("ADMIN_PORT", 8080))
    admin_secret_key: str = os.getenv("ADMIN_SECRET_KEY", "change-this-secret-key")
    
    # Database
    database_url: str = os.getenv("DATABASE_URL", "postgresql+asyncpg://vitte_user:password@postgres:5432/vitte_bot")
    
    # Redis
    redis_url: str = os.getenv("REDIS_URL", "redis://redis:6379/0")
    
    # Environment
    environment: str = os.getenv("ENVIRONMENT", "production")
    debug: bool = os.getenv("DEBUG", "False").lower() == "true"
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global config instance
config = AdminConfig()
