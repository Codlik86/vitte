#!/usr/bin/env python
"""
Run Alembic database migrations

This script runs pending Alembic migrations.
Should be executed before starting the application services.
"""
import os
import sys
from pathlib import Path

# Add parent directory to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from alembic.config import Config
from alembic import command


def run_migrations():
    """Run all pending migrations"""
    # Get database URL from environment
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL environment variable is not set")
        sys.exit(1)

    print(f"Running migrations for database: {database_url.split('@')[1] if '@' in database_url else 'unknown'}")

    # Create Alembic config
    alembic_ini_path = project_root / "alembic.ini"
    alembic_cfg = Config(str(alembic_ini_path))

    # Override database URL from environment
    alembic_cfg.set_main_option("sqlalchemy.url", database_url)

    try:
        # Run migrations to head
        print("Applying migrations...")
        command.upgrade(alembic_cfg, "head")
        print("✅ Migrations completed successfully")
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    run_migrations()
