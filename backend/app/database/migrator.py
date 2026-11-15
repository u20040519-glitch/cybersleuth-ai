# =============================================================================
# CYBERSLEUTH AI - Migration runner
# =============================================================================
# The SQL files in `supabase/migrations/` are the single source of truth for the
# schema. They are applied in filename order and recorded in
# `public.schema_migrations`, so re-running is safe and a partially applied
# database resumes where it stopped.
#
# The same files are used by `supabase db push` on a hosted project, so local
# development and the cloud deployment always share one schema.
# =============================================================================

from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Tuple

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

logger = logging.getLogger(__name__)

MIGRATIONS_DIR = Path(__file__).resolve().parents[3] / "supabase" / "migrations"

TRACKING_TABLE = """
CREATE TABLE IF NOT EXISTS public.schema_migrations (
    version     text PRIMARY KEY,
    applied_at  timestamptz NOT NULL DEFAULT now()
)
"""


def migration_files() -> List[Path]:
    """Every migration file, in apply order."""
    if not MIGRATIONS_DIR.exists():
        return []
    return sorted(p for p in MIGRATIONS_DIR.glob("*.sql") if p.is_file())


async def applied_versions(connection: AsyncConnection) -> set[str]:
    await connection.execute(text(TRACKING_TABLE))
    rows = await connection.execute(text("SELECT version FROM public.schema_migrations"))
    return {row[0] for row in rows}


async def _execute_script(connection: AsyncConnection, sql: str) -> None:
    """Execute a migration file.

    Migration files contain several statements, including `DO $$ ... $$`
    blocks, so they are sent through the driver's simple query protocol rather
    than as a single prepared statement.
    """
    raw = await connection.get_raw_connection()
    driver = raw.driver_connection
    await driver.execute(sql)


async def run_migrations(engine: AsyncEngine, directory: Path | None = None) -> List[Tuple[str, bool]]:
    """Apply every pending migration. Returns [(version, applied)]."""
    directory = directory or MIGRATIONS_DIR
    files = sorted(p for p in directory.glob("*.sql") if p.is_file())

    applied: List[Tuple[str, bool]] = []

    async with engine.begin() as connection:
        await connection.execute(text(TRACKING_TABLE))
        rows = await connection.execute(text("SELECT version FROM public.schema_migrations"))
        done = {row[0] for row in rows}

        for path in files:
            version = path.stem
            if version in done:
                applied.append((version, False))
                continue

            logger.info("Applying migration %s", version)
            sql = path.read_text(encoding="utf-8")
            await _execute_script(connection, sql)
            await connection.execute(
                text("INSERT INTO public.schema_migrations (version) VALUES (:v)"),
                {"v": version},
            )
            applied.append((version, True))

    newly = [v for v, did in applied if did]
    if newly:
        logger.info("Applied %d migration(s): %s", len(newly), ", ".join(newly))
    else:
        logger.info("Database schema is already up to date")
    return applied


async def reset_schema(engine: AsyncEngine) -> None:
    """Drop and recreate the public schema. Used by the test suite."""
    async with engine.begin() as connection:
        await connection.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        await connection.execute(text("DROP SCHEMA IF EXISTS auth CASCADE"))
    await run_migrations(engine)
