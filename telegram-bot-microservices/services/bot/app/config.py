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
