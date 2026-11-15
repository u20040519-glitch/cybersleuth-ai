# =============================================================================
# CYBERSLEUTH AI - Portable PostgreSQL for local development
# =============================================================================
# Supabase is the production target, but the project must also run on a plain
# developer machine. `pgserver` ships a real PostgreSQL 16 build as a Python
# package, so the exact same migrations, triggers and RLS policies run locally
# and in the cloud - no SQLite fallback, no divergent dialect.
# =============================================================================

from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_server = None


def _to_async_url(uri: str) -> str:
    """Convert a libpq URL into the SQLAlchemy asyncpg dialect URL."""
    if uri.startswith("postgresql+asyncpg://"):
        return uri
    if uri.startswith("postgresql://"):
        return "postgresql+asyncpg://" + uri[len("postgresql://") :]
    if uri.startswith("postgres://"):
        return "postgresql+asyncpg://" + uri[len("postgres://") :]
    return uri


def ensure_local_postgres() -> str:
    """Return a ready-to-use PostgreSQL URL, starting the local server if needed.

    Returns the SQLAlchemy async URL. When `DATABASE_URL` is configured the
    application uses that database instead and nothing is started locally.
    """
    global _server

    if settings.DATABASE_URL:
        return _to_async_url(settings.DATABASE_URL)

    with _lock:
        if _server is None:
            import pgserver  # imported lazily: only needed for local dev

            data_dir = Path(settings.LOCAL_PG_DATA_DIR)
            data_dir.mkdir(parents=True, exist_ok=True)
            logger.info("Starting local PostgreSQL server in %s", data_dir)
            _server = pgserver.get_server(str(data_dir))
            logger.info("Local PostgreSQL ready at %s", _server.get_uri())
        return _to_async_url(_server.get_uri())


def local_database_uri() -> Optional[str]:
    """The plain libpq URI of the local server, or None when not running."""
    return _server.get_uri() if _server is not None else None


def stop_local_postgres() -> None:
    """Shut the local server down (used by tests and graceful shutdown)."""
    global _server
    with _lock:
        if _server is not None:
            try:
                _server.cleanup()
            except Exception:  # pragma: no cover - best effort
                logger.exception("Failed to stop local PostgreSQL")
            _server = None
