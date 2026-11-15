# =============================================================================
# CYBERSLEUTH AI - Test harness
# =============================================================================
# Tests run against a dedicated `cybersleuth_test` database on the same local
# embedded PostgreSQL server used for development. The schema is rebuilt once
# per test session; every table is truncated between tests, so cases are
# isolated and order-independent.
# =============================================================================

from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path

import pytest
import pytest_asyncio

REPO_ROOT = Path(__file__).resolve().parents[2]
TEST_DB = "cybersleuth_test"

# Test uploads must land somewhere disposable. This must happen before any
# app module is imported so the storage backend picks it up.
_tmp_storage = tempfile.mkdtemp(prefix="cybersleuth-test-storage-")
os.environ["UPLOAD_DIRECTORY"] = _tmp_storage
os.environ["STORAGE_BACKEND"] = "local"
os.environ["LOG_LEVEL"] = "WARNING"
os.environ["GEMINI_API_KEY"] = ""  # explanation layer must not be consulted in tests
os.environ["CYBERSLEUTH_TEST"] = "1"  # explanation layer must not be consulted in tests

from app.core import database as database_module  # noqa: E402
from app.core.database import set_runtime_url  # noqa: E402
from app.core.ratelimit import reset_limiters  # noqa: E402
from app.database import migrator  # noqa: E402
from app.database.bootstrap import _app_role_url  # noqa: E402
from app.database.local_postgres import ensure_local_postgres  # noqa: E402

from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402

ADMIN_URL = ensure_local_postgres()
ADMIN_TEST_URL = ADMIN_URL.rsplit("/", 1)[0] + f"/{TEST_DB}"
TEST_RUNTIME_URL = _app_role_url(ADMIN_TEST_URL)

TRUNCATABLE = (
    "public.analysis_results",
    "public.evidence_events",
    "public.chain_of_custody",
    "public.forensic_timelines",
    "public.correlation_results",
    "public.generated_reports",
    "public.evidence",
    "public.investigation_members",
    "public.audit_logs",
    "public.investigations",
    "public.profiles",
    "auth.users",
)


def _rebuild_database() -> None:
    """Drop and recreate the test database, then apply all migrations."""

    async def _go() -> None:
        admin = create_async_engine(ADMIN_URL, isolation_level="AUTOCOMMIT")
        async with admin.connect() as connection:
            await connection.execute(text(f'DROP DATABASE IF EXISTS {TEST_DB} WITH (FORCE)'))
            await connection.execute(text(f"CREATE DATABASE {TEST_DB}"))
        await admin.dispose()
        engine = create_async_engine(ADMIN_TEST_URL)
        try:
            await migrator.run_migrations(engine)
        finally:
            await engine.dispose()

    asyncio.run(_go())


def _truncate_tables() -> None:
    async def _go() -> None:
        admin = create_async_engine(ADMIN_TEST_URL, isolation_level="AUTOCOMMIT")
        async with admin.begin() as connection:
            await connection.execute(
                text(f"TRUNCATE {', '.join(TRUNCATABLE)} RESTART IDENTITY CASCADE")
            )
        await admin.dispose()

    asyncio.run(_go())


_rebuild_database()
set_runtime_url(TEST_RUNTIME_URL)

import httpx  # noqa: E402


@pytest.fixture(autouse=True)
def clean_state():
    reset_limiters()
    _truncate_tables()
    yield
    reset_limiters()


@pytest_asyncio.fixture
async def client():
    from app.main import app

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://cybersleuth.test") as test_client:
        yield test_client


async def register_user(client, email: str, password: str = "TestPass!2026", role: str = "investigator", full_name: str = "Test User") -> dict:
    response = await client.post(
        "/api/auth/register",
        json={
            "full_name": full_name,
            "email": email,
            "password": password,
            "confirm_password": password,
            "role": role,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def login_user(client, email: str, password: str = "TestPass!2026") -> dict:
    response = await client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()


@pytest_asyncio.fixture
async def investigator(client):
    payload = await register_user(client, "investigator@example.com", role="investigator", full_name="Indy Investigator")
    payload["headers"] = auth_headers(payload["access_token"])
    return payload


@pytest_asyncio.fixture
async def supervisor(client):
    payload = await register_user(client, "supervisor@example.com", role="supervisor", full_name="Sara Supervisor")
    payload["headers"] = auth_headers(payload["access_token"])
    return payload


@pytest_asyncio.fixture
async def case(client, investigator):
    response = await client.post(
        "/api/investigations",
        json={
            "case_id": "CASE-TEST-001",
            "title": "Test Investigation",
            "description": "A case created by the test suite",
            "category": "malware",
            "priority": "high",
            "status": "active",
            "notes": None,
        },
        headers=investigator["headers"],
    )
    assert response.status_code == 201, response.text
    body = response.json()
    return body


def sample_jpeg_bytes(width: int = 96, height: int = 96) -> bytes:
    """Generate a small real JPEG with a little noise so it is a valid image."""
    import io

    import numpy as np
    from PIL import Image

    rng = np.random.default_rng(20260611)
    array = rng.integers(120, 180, size=(height, width, 3), dtype=np.uint8)
    image = Image.fromarray(array)
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=90)
    return buffer.getvalue()


def sample_wav_bytes(seconds: float = 0.5, sample_rate: int = 22050) -> bytes:
    import io

    import numpy as np
    import soundfile as sf

    t = np.linspace(0, seconds, int(sample_rate * seconds), endpoint=False)
    audio = 0.5 * np.sin(2 * np.pi * 440 * t)
    buffer = io.BytesIO()
    sf.write(buffer, audio, sample_rate, format="WAV", subtype="PCM_16")
    return buffer.getvalue()


@pytest_asyncio.fixture
async def uploaded_jpeg(client, investigator, case):
    response = await client.post(
        "/api/evidence/upload",
        files={"file": ("sample.jpg", sample_jpeg_bytes(), "image/jpeg")},
        data={"investigation_id": case["id"]},
        headers=investigator["headers"],
    )
    assert response.status_code == 201, response.text
    return response.json()
