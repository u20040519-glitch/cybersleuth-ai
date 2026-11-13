# =============================================================================
# PROJECT NEXUS AI - Operations Tests
# =============================================================================
# Tests for backup creation, backup verification, restoration testing,
# error monitoring, health checks.
# =============================================================================

import sys
from pathlib import Path

import pytest
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from httpx import AsyncClient, ASGITransport
from app.main import app
from scripts.backup_db import create_backup, verify_backup, list_backups, cleanup_old_backups, _load_manifest


@pytest.mark.asyncio
async def test_health_check():
    """Test health check endpoint returns healthy status without internals."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "PROJECT NEXUS AI"
        assert "version" in data
        assert "environment" in data
        # Should not expose internal infrastructure details
        assert "database" not in str(data).lower()
        assert "password" not in str(data).lower()
        assert "secret" not in str(data).lower()


@pytest.mark.asyncio
async def test_backup_creation():
    """Test database backup creation."""
    try:
        entry = create_backup()
        assert entry is not None
        assert "filename" in entry
        assert "sha256" in entry
        assert "timestamp" in entry
        assert "file_size_bytes" in entry
        print(f"Backup created: {entry['filename']}")
    except Exception as exc:
        pytest.fail(f"Backup creation failed: {exc}")


@pytest.mark.asyncio
async def test_backup_verification():
    """Test backup file verification."""
    manifest = _load_manifest()
    if not manifest:
        # Create a backup first
        entry = create_backup()
        filename = entry["filename"]
    else:
        filename = manifest[-1]["filename"]

    # Verify the backup
    result = verify_backup(filename)
    assert result is True

    # Verify manifest is updated
    manifest = _load_manifest()
    entry = next((e for e in manifest if e.get("filename") == filename), None)
    assert entry is not None
    assert entry.get("verified") is True


@pytest.mark.asyncio
async def test_backup_list():
    """Test backup listing."""
    try:
        list_backups()  # Should not raise
    except Exception as exc:
        pytest.fail(f"Backup listing failed: {exc}")


@pytest.mark.asyncio
async def test_backup_cleanup():
    """Test backup retention cleanup."""
    try:
        removed = cleanup_old_backups()
        assert isinstance(removed, int)
        assert removed >= 0
    except Exception as exc:
        pytest.fail(f"Backup cleanup failed: {exc}")


@pytest.mark.asyncio
async def test_error_monitoring_health():
    """Test that error monitoring endpoints work (health check)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200

        # Test that invalid routes return proper error pages (not stack traces)
        response = await client.get("/nonexistent-endpoint")
        assert response.status_code == 404
        body = response.json()
        # Should not expose internals
        assert "traceback" not in str(body).lower()
        assert "stack" not in str(body).lower()