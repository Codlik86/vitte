from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

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
        # Ensure enum and new columns exist even on existing databases
        await conn.execute(
            text(
                """
                DO $$
                BEGIN
                    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'access_status_enum') THEN
                        CREATE TYPE access_status_enum AS ENUM ('no_access', 'trial_usage', 'subscription_active');
                    END IF;
                    -- ensure all values exist in case type was created earlier without them
                    BEGIN
                        ALTER TYPE access_status_enum ADD VALUE IF NOT EXISTS 'no_access';
                        ALTER TYPE access_status_enum ADD VALUE IF NOT EXISTS 'trial_usage';
                        ALTER TYPE access_status_enum ADD VALUE IF NOT EXISTS 'subscription_active';
                    EXCEPTION WHEN duplicate_object THEN
                        NULL;
                    END;
                END$$;
                """
            )
        )
        await conn.execute(
            text(
                """
                ALTER TABLE users
                ADD COLUMN IF NOT EXISTS access_status access_status_enum NOT NULL DEFAULT 'trial_usage'::access_status_enum,
                ADD COLUMN IF NOT EXISTS free_messages_used integer NOT NULL DEFAULT 0;
                """
            )
        )
    logger.info("DB tables ensured.")


@app.get("/", include_in_schema=False)
async def root():
    return {"service": "vitte-backend", "status": "ok"}


app.include_router(health_router)
app.include_router(webhook_router)
app.include_router(access_router)
