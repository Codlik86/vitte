"""
Main entry point for Admin Panel
"""
from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.config import config
from app.routes import dashboard_router, users_router
from app.routes.health import router as health_router
from app.routes.analytics import router as analytics_router
from shared.database import init_db, close_db
from shared.utils import get_logger

logger = get_logger(__name__, config.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown"""
    # Startup
    logger.info(f"Starting Admin Panel in {config.environment} mode...")
    logger.info("Database migrations should be run separately before starting services")

    yield

    # Shutdown
    logger.info("Shutting down Admin Panel...")
    await close_db()
    logger.info("Admin Panel shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Vitte Bot Admin Panel",
    description="Admin panel for managing Vitte Telegram Bot",
    version="1.0.0",
    lifespan=lifespan
)

# Include routers
app.include_router(health_router, tags=["health"])
app.include_router(dashboard_router, tags=["dashboard"])
app.include_router(users_router, tags=["users"])
app.include_router(analytics_router, tags=["analytics"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Vitte Bot Admin Panel",
        "version": "1.0.0",
        "status": "running"
    }
