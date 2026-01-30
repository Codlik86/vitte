"""
LLM Gateway - FastAPI Application
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.routes import router
from app.services.cache import llm_cache

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    logger.info(f"Starting {settings.service_name}...")
    logger.info(f"LLM Model: {settings.vitte_llm_model}")
    logger.info(f"Cache enabled: {settings.cache_enabled}")
    logger.info(f"Streaming enabled: {settings.streaming_enabled}")
    logger.info(f"Circuit breaker enabled: {settings.circuit_breaker_enabled}")
    logger.info(f"Rate limiting enabled: {settings.rate_limit_enabled}")

    # Connect to Redis
    await llm_cache.connect()

    yield

    # Shutdown
    logger.info(f"Shutting down {settings.service_name}...")
    await llm_cache.disconnect()


# Create FastAPI app
app = FastAPI(
    title="LLM Gateway",
    description="DeepSeek LLM Gateway with caching, retry, and streaming",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(router, prefix="/v1")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": settings.service_name,
        "version": "1.0.0",
        "status": "running"
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=True
    )
