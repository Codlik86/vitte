import asyncio
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from .api import (
    health_router,
    webhook_router,
    access_router,
    personas_router,
    chat_router,
    payments_router,
    store_router,
    analytics_router,
    features_router,
    events_router,
    bot_control_router,
)
from .api.routes_webhook import cleanup_processed_updates
from .db import engine, Base, async_session_factory
from .logging_config import logger
from . import models  # noqa: F401 ensures models are imported for metadata
from .personas_seed import ensure_default_personas
from .bot import bot, setup_bot_commands
from .services.retention import start_retention_worker
from .services.cleanup import start_cleanup_worker


app = FastAPI(title="Vitte API")
retention_task: asyncio.Task | None = None
cleanup_task: asyncio.Task | None = None

BASE_DIR = Path(__file__).resolve().parent.parent
LANDING_DIR = BASE_DIR / "landing"

if LANDING_DIR.exists():
    app.mount(
        "/vitte",
        StaticFiles(directory=str(LANDING_DIR), html=True),
        name="vitte_landing",
    )

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
    # All raw schema/data tweaks stay within a live connection
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        # Ensure enums exist
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
        await conn.execute(
            text(
                """
                DO $$
                BEGIN
                    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'persona_kind_enum') THEN
                        CREATE TYPE persona_kind_enum AS ENUM (
                            'DEFAULT','CUSTOM','SOFT_EMPATH','SASSY','SMART_COOL','CHAOTIC','THERAPEUTIC','ANIME_TSUNDERE','ANIME_WAIFU_SOFT','WITTY_BOLD','CHAOTIC_FUN'
                        );
                    ELSE
                        BEGIN
                            ALTER TYPE persona_kind_enum ADD VALUE IF NOT EXISTS 'DEFAULT';
                            ALTER TYPE persona_kind_enum ADD VALUE IF NOT EXISTS 'CUSTOM';
                            ALTER TYPE persona_kind_enum ADD VALUE IF NOT EXISTS 'SOFT_EMPATH';
                            ALTER TYPE persona_kind_enum ADD VALUE IF NOT EXISTS 'SASSY';
                            ALTER TYPE persona_kind_enum ADD VALUE IF NOT EXISTS 'SMART_COOL';
                            ALTER TYPE persona_kind_enum ADD VALUE IF NOT EXISTS 'CHAOTIC';
                            ALTER TYPE persona_kind_enum ADD VALUE IF NOT EXISTS 'THERAPEUTIC';
                            ALTER TYPE persona_kind_enum ADD VALUE IF NOT EXISTS 'ANIME_TSUNDERE';
                            ALTER TYPE persona_kind_enum ADD VALUE IF NOT EXISTS 'ANIME_WAIFU_SOFT';
                            ALTER TYPE persona_kind_enum ADD VALUE IF NOT EXISTS 'WITTY_BOLD';
                            ALTER TYPE persona_kind_enum ADD VALUE IF NOT EXISTS 'CHAOTIC_FUN';
                        EXCEPTION WHEN duplicate_object THEN
                            NULL;
                        END;
                    END IF;
                END$$;
                """
            )
        )

        # Schema alignments (users, personas, dialogs) and data backfills
        await conn.execute(
            text(
                """
                ALTER TABLE users
                ADD COLUMN IF NOT EXISTS access_status access_status_enum NOT NULL DEFAULT 'trial_usage'::access_status_enum,
                ADD COLUMN IF NOT EXISTS free_messages_used integer NOT NULL DEFAULT 0,
                ADD COLUMN IF NOT EXISTS active_persona_id integer REFERENCES personas(id) ON DELETE SET NULL,
                ADD COLUMN IF NOT EXISTS paywall_variant varchar(1),
                ADD COLUMN IF NOT EXISTS age_confirmed boolean NOT NULL DEFAULT false,
                ADD COLUMN IF NOT EXISTS is_adult_confirmed boolean NOT NULL DEFAULT false,
                ADD COLUMN IF NOT EXISTS accepted_terms_at timestamp NULL,
                ADD COLUMN IF NOT EXISTS last_surprise_sent_at timestamp NULL,
                ADD COLUMN IF NOT EXISTS bot_reply_counter integer NOT NULL DEFAULT 0,
                ADD COLUMN IF NOT EXISTS last_image_sent_at timestamp NULL,
                ADD COLUMN IF NOT EXISTS updated_at timestamp NULL DEFAULT now();
                """
            )
        )
        await conn.execute(
            text(
                """
                ALTER TABLE personas
                ADD COLUMN IF NOT EXISTS name varchar(100),
                ADD COLUMN IF NOT EXISTS short_title varchar(255) NOT NULL DEFAULT '',
                ADD COLUMN IF NOT EXISTS gender varchar(16) NOT NULL DEFAULT 'female',
                ADD COLUMN IF NOT EXISTS kind persona_kind_enum NOT NULL DEFAULT 'DEFAULT',
                ADD COLUMN IF NOT EXISTS description_short varchar(256) NOT NULL DEFAULT '',
                ADD COLUMN IF NOT EXISTS description_long text NOT NULL DEFAULT '',
                ADD COLUMN IF NOT EXISTS short_description varchar(255),
                ADD COLUMN IF NOT EXISTS long_description text,
                ADD COLUMN IF NOT EXISTS archetype varchar(64),
                ADD COLUMN IF NOT EXISTS system_prompt text,
                ADD COLUMN IF NOT EXISTS is_default boolean DEFAULT true,
                ADD COLUMN IF NOT EXISTS is_custom boolean DEFAULT false,
                ADD COLUMN IF NOT EXISTS is_active boolean DEFAULT true,
                ADD COLUMN IF NOT EXISTS owner_user_id integer REFERENCES users(id) ON DELETE SET NULL,
                ADD COLUMN IF NOT EXISTS created_by_user_id integer REFERENCES users(id) ON DELETE SET NULL,
                ADD COLUMN IF NOT EXISTS created_at timestamp DEFAULT now(),
                ADD COLUMN IF NOT EXISTS short_lore text,
                ADD COLUMN IF NOT EXISTS background text,
                ADD COLUMN IF NOT EXISTS legend_full text,
                ADD COLUMN IF NOT EXISTS emotional_style text,
                ADD COLUMN IF NOT EXISTS relationship_style text,
                ADD COLUMN IF NOT EXISTS emotions_full text,
                ADD COLUMN IF NOT EXISTS hooks jsonb DEFAULT '[]'::jsonb,
                ADD COLUMN IF NOT EXISTS triggers_positive jsonb DEFAULT '[]'::jsonb,
                ADD COLUMN IF NOT EXISTS triggers_negative jsonb DEFAULT '[]'::jsonb;
                """
            )
        )
        await conn.execute(
            text(
                """
                ALTER TABLE dialogs
                ADD COLUMN IF NOT EXISTS last_followup_sent_at timestamp NULL,
                ADD COLUMN IF NOT EXISTS remind_1h_sent boolean NULL DEFAULT false,
                ADD COLUMN IF NOT EXISTS remind_1d_sent boolean NULL DEFAULT false,
                ADD COLUMN IF NOT EXISTS remind_7d_sent boolean NULL DEFAULT false,
                ADD COLUMN IF NOT EXISTS last_reminder_sent_at timestamp NULL;
                """
            )
        )
        await conn.execute(
            text(
                """
                UPDATE personas
                SET short_title = COALESCE(short_title, short_description, name, '')
                WHERE short_title IS NULL;
                """
            )
        )
        await conn.execute(
            text(
                """
                UPDATE personas
                SET gender = COALESCE(gender, 'female')
                WHERE gender IS NULL;
                """
            )
        )
        await conn.execute(
            text(
                """
                UPDATE personas
                SET kind = COALESCE(kind, 'DEFAULT'::persona_kind_enum)
                WHERE kind IS NULL;
                """
            )
        )
        await conn.execute(
            text(
                """
                UPDATE personas
                SET description_short = COALESCE(description_short, short_title, short_description, name, ''),
                    description_long = COALESCE(description_long, long_description, legend_full, short_lore, short_description, '')
                WHERE description_short = '' OR description_long = '';
                """
            )
        )

    # Ensure default personas are synced from code on each startup (separate session)
    async with async_session_factory() as session:
        await ensure_default_personas(session)
    logger.info("Default personas ensured.")
    await setup_bot_commands(bot)
    logger.info("Bot commands set up.")
    logger.info("DB tables ensured.")
    global retention_task
    retention_task = await start_retention_worker()
    global cleanup_task
    cleanup_task = await start_cleanup_worker()
    try:
        await cleanup_processed_updates()
        logger.info("Processed updates cleanup executed on startup.")
    except Exception:
        logger.exception("Processed updates cleanup failed")


@app.get("/", include_in_schema=False)
async def root():
    return {"service": "vitte-backend", "status": "ok"}


app.include_router(health_router)
app.include_router(webhook_router)
app.include_router(access_router)
app.include_router(personas_router)
app.include_router(chat_router)
app.include_router(payments_router)
app.include_router(store_router)
app.include_router(analytics_router)
app.include_router(features_router)
app.include_router(events_router)
app.include_router(bot_control_router)
