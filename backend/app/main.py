from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from .api import health_router, webhook_router, access_router, personas_router
from .db import engine, Base
from .logging_config import logger
from . import models  # noqa: F401 ensures models are imported for metadata
from .personas_seed import ensure_default_personas


app = FastAPI(title="Vitte API")

origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://vitte-pi.vercel.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup():
    logger.info("Starting Vitte backend...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Separate transaction to ensure enum exists and has all values
    async with engine.begin() as conn:
        await conn.execute(
            text(
                """
                DO $$
                BEGIN
                    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'access_status_enum') THEN
                        CREATE TYPE access_status_enum AS ENUM ('no_access', 'trial_usage', 'subscription_active');
                    END IF;
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

    # Separate transaction so new enum values are committed before use in defaults
    async with engine.begin() as conn:
        await conn.execute(
            text(
                """
                ALTER TABLE users
                ADD COLUMN IF NOT EXISTS access_status access_status_enum NOT NULL DEFAULT 'trial_usage'::access_status_enum,
                ADD COLUMN IF NOT EXISTS free_messages_used integer NOT NULL DEFAULT 0;
                """
            )
        )
        await conn.execute(
            text(
                """
                ALTER TABLE users
                ADD COLUMN IF NOT EXISTS active_persona_id integer REFERENCES personas(id) ON DELETE SET NULL;
                """
            )
        )
    await ensure_default_personas()
    logger.info("Default personas ensured.")
    logger.info("DB tables ensured.")


@app.get("/", include_in_schema=False)
async def root():
    return {"service": "vitte-backend", "status": "ok"}


app.include_router(health_router)
app.include_router(webhook_router)
app.include_router(access_router)
app.include_router(personas_router)
