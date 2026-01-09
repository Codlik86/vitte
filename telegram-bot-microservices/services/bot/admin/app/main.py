"""
Main entry point for Admin Panel
"""
from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.config import config
from app.routes import dashboard_router, users_router
from shared.database import init_db, close_db
from shared.utils import get_logger

logger = get_logger(__name__, config.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown"""
    # Startup
    logger.info(f"Starting Admin Panel in {config.environment} mode...")
    try:
        await init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
    
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
app.include_router(dashboard_router, tags=["dashboard"])
app.include_router(users_router, tags=["users"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Vitte Bot Admin Panel",
        "version": "1.0.0",
        "status": "running"
    }
