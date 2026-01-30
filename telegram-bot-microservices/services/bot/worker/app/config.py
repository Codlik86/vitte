"""
Worker configuration
"""
import os
from pydantic_settings import BaseSettings


class WorkerConfig(BaseSettings):
    """Worker configuration from environment variables"""
    
    # Database
    database_url: str = os.getenv("DATABASE_URL", "postgresql+asyncpg://vitte_user:password@postgres:5432/vitte_bot")
    
    # Redis
    redis_url: str = os.getenv("REDIS_URL", "redis://redis:6379/0")
    
    # Celery
    celery_broker_url: str = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/1")
    celery_result_backend: str = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/2")
    celery_worker_concurrency: int = int(os.getenv("CELERY_WORKER_CONCURRENCY", 4))
    celery_task_time_limit: int = int(os.getenv("CELERY_TASK_TIME_LIMIT", 600))
    celery_task_soft_time_limit: int = int(os.getenv("CELERY_TASK_SOFT_TIME_LIMIT", 300))
    
    # Environment
    environment: str = os.getenv("ENVIRONMENT", "production")
    debug: bool = os.getenv("DEBUG", "False").lower() == "true"
    log_level: str = os.getenv("WORKER_LOG_LEVEL", "INFO")
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global config instance
config = WorkerConfig()
