# =============================================================================
# CYBERSLEUTH AI - Database bootstrap
# =============================================================================
# Brings the database to a usable state on start-up:
#
#   1. resolve the admin connection (DATABASE_URL, or the embedded local server)
#   2. apply every pending migration from `supabase/migrations/`
#   3. provision the restricted application role and its password
#   4. hand the runtime URL back so the API connects as that role
#
# The API therefore never runs as a superuser, so the Row Level Security
# policies in `supabase/migrations/008_rls_policies.sql` are enforced by
# PostgreSQL itself.
#
# Production:
#   DATABASE_URL       - privileged connection used ONLY for migrations
#   APP_DATABASE_URL   - restricted connection the API uses at runtime
#   APP_DB_PASSWORD    - password set on the cybersleuth_app role by migrations
#
# Local development:
#   leave both unset; an embedded PostgreSQL is created under .pgdata and the
#   cybersleuth_app role gets APP_DB_PASSWORD (a development-only default).
# =============================================================================

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings
from app.core.database import set_runtime_url

logger = logging.getLogger(__name__)


async def bootstrap_database() -> str:
    """Prepare the database and return the URL the API should connect with."""
    if settings.DATABASE_URL:
        admin_url = settings.DATABASE_URL
        logger.info("Using DATABASE_URL for migrations")
    else:
        from app.database.local_postgres import ensure_local_postgres

        admin_url = ensure_local_postgres()

    # Migrations need privileges the application role does not have, so they
    # run on a separate connection.
    admin_engine = create_async_engine(admin_url, echo=False, future=True)
    try:
        from app.database.migrator import run_migrations

        await run_migrations(admin_engine)

        await _provision_app_role(admin_engine)
    finally:
        await admin_engine.dispose()

    runtime_url = settings.APP_DATABASE_URL or _app_role_url(admin_url)
    set_runtime_url(runtime_url)
    logger.info("Application database role ready (%s)", settings.APP_DB_USER)
    return runtime_url


def _quote_literal(value: str) -> str:
    """Single-quote a string literal for safe interpolation into SQL."""
    return "'" + value.replace("'", "''") + "'"


def _quote_identifier(value: str) -> str:
    """Double-quote an identifier for safe interpolation into SQL."""
    return '"' + value.replace('"', '""') + '"'


async def _provision_app_role(admin_engine) -> None:
    """Create the restricted role and give it a password."""
    role = _quote_identifier(settings.APP_DB_USER)
    password = _quote_literal(settings.APP_DB_PASSWORD)
    async with admin_engine.begin() as connection:
        exists = await connection.scalar(
            text("SELECT 1 FROM pg_roles WHERE rolname = :name"),
            {"name": settings.APP_DB_USER},
        )
        if not exists:
            await connection.execute(
                text(
                    f"CREATE ROLE {role} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT"
                )
            )
        await connection.execute(
            text(f"ALTER ROLE {role} WITH LOGIN PASSWORD {password}")
        )


def _app_role_url(admin_url: str) -> str:
    """Rewrite the admin URL so it points at the restricted application role."""
    if not admin_url.startswith("postgresql+asyncpg://"):
        admin_url = "postgresql+asyncpg://" + admin_url[len("postgresql://") :]

    scheme, _, remainder = admin_url.partition("://")
    host_part = remainder.split("@", 1)[-1]

    return (
        f"{scheme}://{settings.APP_DB_USER}:{settings.APP_DB_PASSWORD}@{host_part}"
    )
