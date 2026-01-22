"""
Bot configuration
"""
import os
from pydantic_settings import BaseSettings


class BotConfig(BaseSettings):
    """Bot configuration from environment variables"""
    
    # Bot settings
    bot_token: str = os.getenv("BOT_TOKEN", "")
    admin_ids: str = os.getenv("ADMIN_IDS", "")
    
    # Database
    database_url: str = os.getenv("DATABASE_URL", "postgresql+asyncpg://vitte_user:password@postgres:5432/vitte_bot")
    
    # Redis
    redis_url: str = os.getenv("REDIS_URL", "redis://redis:6379/0")
    
    # Environment
    environment: str = os.getenv("ENVIRONMENT", "production")
    debug: bool = os.getenv("DEBUG", "False").lower() == "true"
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    # Web App
    webapp_url: str = os.getenv("WEBAPP_URL", "")

    # Internal API URL (for calling API service from bot)
    api_url: str = os.getenv("API_URL", "http://api:8000")

    # Rate Limiting
    rate_limit_messages: int = int(os.getenv("RATE_LIMIT_MESSAGES", "10"))  # per minute
    rate_limit_messages_window: int = int(os.getenv("RATE_LIMIT_MESSAGES_WINDOW", "60"))  # seconds
    rate_limit_callbacks: int = int(os.getenv("RATE_LIMIT_CALLBACKS", "20"))  # per minute
    rate_limit_callbacks_window: int = int(os.getenv("RATE_LIMIT_CALLBACKS_WINDOW", "60"))  # seconds
    antiflood_limit: int = int(os.getenv("ANTIFLOOD_LIMIT", "3"))  # per 5 seconds
    antiflood_window: int = int(os.getenv("ANTIFLOOD_WINDOW", "5"))  # seconds

    @property
    def admin_list(self) -> list[int]:
        """Parse admin IDs from comma-separated string"""
        if not self.admin_ids:
            return []
        return [int(admin_id.strip()) for admin_id in self.admin_ids.split(",") if admin_id.strip()]
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global config instance
config = BotConfig()
