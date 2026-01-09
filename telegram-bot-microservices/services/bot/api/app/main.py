"""
Main entry point for FastAPI service
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import config
from app.api import v1_router
from shared.database import init_db, close_db
from shared.utils import get_logger

logger = get_logger(__name__, config.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown"""
    # Startup
    logger.info(f"Starting API service in {config.environment} mode...")
    logger.info("Database migrations should be run separately before starting services")

    yield

    # Shutdown
    logger.info("Shutting down API service...")
    await close_db()
    logger.info("API service shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Vitte Bot API",
    description="REST API for Vitte Telegram Bot",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(v1_router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Vitte Bot API",
        "version": "1.0.0",
        "status": "running"
    }
