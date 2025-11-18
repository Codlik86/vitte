from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import health_router, webhook_router, access_router
from .db import engine, Base
from .logging_config import logger
from . import models  # noqa: F401 ensures models are imported for metadata


app = FastAPI(title="Vitte Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # позже сузим
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup():
    logger.info("Starting Vitte backend...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("DB tables ensured.")


@app.get("/", include_in_schema=False)
async def root():
    return {"service": "vitte-backend", "status": "ok"}


app.include_router(health_router)
app.include_router(webhook_router)
app.include_router(access_router)
