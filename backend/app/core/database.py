# =============================================================================
# CYBERSLEUTH AI - Async SQLAlchemy engine and session management
# =============================================================================

from __future__ import annotations

import logging
import os
from typing import AsyncGenerator, Optional

from sqlalchemy import event, text, NullPool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Session

from app.core.config import settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Declarative base for every CyberSleuth AI table."""


_engine = None
_session_factory = None
_runtime_url: Optional[str] = None


def set_runtime_url(url: str) -> None:
    """Pin the URL the runtime engine connects with.

    The bootstrap sets this to the restricted application role so that RLS is
    enforced. It must be called before the engine is first used.
    """
    global _runtime_url
    _runtime_url = url


def _build_engine():
    from app.database.local_postgres import ensure_local_postgres

    url = _runtime_url or ensure_local_postgres()
    logger.info("Database engine: %s", url.split("@")[-1])
    kwargs = {}
    if os.environ.get("CYBERSLEUTH_TEST") == "1":
        # Test harness gives every test a fresh event loop; a pooled
        # connection bound to a previous loop is unusable there.
        kwargs["poolclass"] = NullPool
    else:
        kwargs.update(pool_size=10, max_overflow=20, pool_pre_ping=True, pool_recycle=1800)
    return create_async_engine(
        url,
        echo=False,
        future=True,
        **kwargs,
    )


def get_engine():
    global _engine
    if _engine is None:
        _engine = _build_engine()
    return _engine


def get_session_factory():
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
    return _session_factory


@event.listens_for(Session, "after_begin")
def _noop_on_begin(session: Session, transaction, connection) -> None:
    """Placeholder hook kept for future session-level concerns."""


async def set_db_identity(
    session: AsyncSession,
    *,
    user_id: Optional[str],
    role: str = "",
    email: str = "",
) -> None:
    """Publish the caller's identity to PostgreSQL for the current transaction.

    RLS policies read the identity from the `app.user_id`, `app.user_role` and
    `app.user_email` settings. They are set with `SET LOCAL` semantics, so they
    are scoped to the transaction and can never leak between pooled
    connections.

    This must be called before any query that is subject to RLS.
    """
    await session.execute(
        text(
            "SELECT set_config('app.user_id', :uid, true), "
            "set_config('app.user_role', :role, true), "
            "set_config('app.user_email', :email, true)"
        ),
        {
            "uid": str(user_id or ""),
            "role": role or "",
            "email": email or "",
        },
    )
    session.info["user_id"] = str(user_id) if user_id else None
    session.info["user_role"] = role
    session.info["user_email"] = email


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding a database session."""
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def dispose_engine() -> None:
    global _engine, _session_factory, _runtime_url
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None
    _runtime_url = None
