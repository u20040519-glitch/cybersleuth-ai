# =============================================================================
# PROJECT NEXUS AI - Database Connection
# =============================================================================
# Async SQLAlchemy setup supporting PostgreSQL (production) and SQLite (dev).
# PostgreSQL is required for Row Level Security (RLS).
# =============================================================================

import logging
from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text, event

from app.core.config import settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """SQLAlchemy declarative base."""


# ---------------------------------------------------------------------------
# Engine creation
# ---------------------------------------------------------------------------

def _create_database_engine():
    """Create the async database engine based on DATABASE_URL."""
    database_url = settings.database_url

    if database_url.startswith("sqlite"):
        # SQLite: development only. No RLS support - app-level authorization enforced.
        logger.warning(
            "Using SQLite database. Row Level Security (RLS) is NOT available. "
            "Application-level authorization will be enforced for all data access."
        )
        engine = create_async_engine(
            database_url,
            echo=settings.app_debug,
            pool_pre_ping=True,
        )
    else:
        # PostgreSQL: production. Supports RLS.
        engine = create_async_engine(
            database_url,
            echo=settings.app_debug,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
        )

    return engine


engine = _create_database_engine()
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ---------------------------------------------------------------------------
# Session dependency with RLS context
# ---------------------------------------------------------------------------

async def get_db(
    current_user_id: Optional[str] = None,
    current_user_role: Optional[str] = None,
) -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a database session with RLS context set."""
    async with AsyncSessionLocal() as session:
        try:
            # Set PostgreSQL session variables for Row Level Security
            if settings.database_url.startswith("postgresql"):
                if current_user_id:
                    await session.execute(
                        text("SELECT set_config('app.current_user_id', $1, true)"),
                        [current_user_id],
                    )
                if current_user_role:
                    await session.execute(
                        text("SELECT set_config('app.current_user_role', $1, true)"),
                        [current_user_role],
                    )
            yield session
        finally:
            await session.close()


# ---------------------------------------------------------------------------
# Database initialization
# ---------------------------------------------------------------------------

async def init_db() -> None:
    """Initialize the database: create tables and enable extensions."""
    import app.models  # noqa: F401  ensure all models are registered

    async with engine.begin() as conn:
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)

        # PostgreSQL-specific: enable pgcrypto extension for hashing support
        if settings.database_url.startswith("postgresql"):
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pgcrypto"))
            logger.info("PostgreSQL pgcrypto extension enabled")

    logger.info("Database initialized successfully")


async def close_db() -> None:
    """Dispose of the database engine."""
    await engine.dispose()
    logger.info("Database engine disposed")


# ---------------------------------------------------------------------------
# PostgreSQL Row Level Security helpers
# ---------------------------------------------------------------------------

async def enable_rls_for_table(session: AsyncSession, table_name: str) -> None:
    """Enable Row Level Security on a PostgreSQL table."""
    if not settings.database_url.startswith("postgresql"):
        return
    await session.execute(text(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY"))


async def create_rls_policy(
    session: AsyncSession,
    table_name: str,
    policy_name: str,
    using_clause: str,
    with_check_clause: Optional[str] = None,
) -> None:
    """Create a Row Level Security policy on a table."""
    if not settings.database_url.startswith("postgresql"):
        return
    check_clause = f" WITH CHECK ({with_check_clause})" if with_check_clause else ""
    await session.execute(
        text(
            f"CREATE POLICY {policy_name} ON {table_name} "
            f"FOR ALL USING ({using_clause}){check_clause}"
        )
    )