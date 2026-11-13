# =============================================================================
# PROJECT NEXUS AI - Security Tests
# =============================================================================
# Tests for rate limiting, invalid file uploads, unauthorized API requests,
# secret exposure checks, input validation, XSS prevention, SQL injection prevention.
# =============================================================================

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_invalid_file_upload():
    """Test invalid file types are rejected."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Register and verify user
        await client.post("/api/auth/register", json={
            "full_name": "Security User",
            "email": "secuser@nexus.ai",
            "password": "SecurePass123!",
            "confirm_password": "SecurePass123!",
            "accept_terms": True,
            "accept_privacy": True,
        })

        from app.db.database import AsyncSessionLocal
        from app.models import User
        from sqlalchemy import select as sa_select

        async with AsyncSessionLocal() as db:
            result = await db.execute(sa_select(User).where(User.email == "secuser@nexus.ai"))
            user = result.scalar_one_or_none()
            if user:
                user.is_verified = True
                user.email_verification_token_hash = None
                user.email_verification_token_expires = None
                await db.commit()

        await client.post("/api/auth/login", json={
            "email": "secuser@nexus.ai",
            "password": "SecurePass123!",
        })

        # Create a case
        response = await client.post("/api/cases", json={
            "case_number": "CASE-SEC-001",
            "title": "Security Case",
        })
        assert response.status_code == 201
        case_id = response.json()["id"]

        # Try to upload an executable file (should be rejected)
        response = await client.post(
            f"/evidence/upload?case_id={case_id}",
            files={"file": ("malware.exe", b"MZ\x90\x00 executable", "application/x-msdownload")}
        )
        assert response.status_code == 400


@pytest.mark.asyncio
async def test_file_size_exceeded():
    """Test files exceeding size limit are rejected."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post("/api/auth/register", json={
            "full_name": "Size User",
            "email": "sizeuser@nexus.ai",
            "password": "SecurePass123!",
            "confirm_password": "SecurePass123!",
            "accept_terms": True,
            "accept_privacy": True,
        })

        from app.db.database import AsyncSessionLocal
        from app.models import User
        from sqlalchemy import select as sa_select

        async with AsyncSessionLocal() as db:
            result = await db.execute(sa_select(User).where(User.email == "sizeuser@nexus.ai"))
            user = result.scalar_one_or_none()
            if user:
                user.is_verified = True
                user.email_verification_token_hash = None
                user.email_verification_token_expires = None
                await db.commit()

        await client.post("/api/auth/login", json={
            "email": "sizeuser@nexus.ai",
            "password": "SecurePass123!",
        })

        response = await client.post("/api/cases", json={
            "case_number": "CASE-SIZE-001",
            "title": "Size Case",
        })
        assert response.status_code == 201
        case_id = response.json()["id"]

        # Try to upload a file larger than 100 MB (create a 101 MB file)
        large_content = b"0" * (101 * 1024 * 1024)  # 101 MB
        response = await client.post(
            f"/evidence/upload?case_id={case_id}",
            files={"file": ("large.txt", large_content, "text/plain")}
        )
        assert response.status_code == 413  # Request Entity Too Large


@pytest.mark.asyncio
async def test_sql_injection_prevention():
    """Test SQL injection attempts are blocked."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post("/api/auth/register", json={
            "full_name": "SQL User",
            "email": "sqluser@nexus.ai",
            "password": "SecurePass123!",
            "confirm_password": "SecurePass123!",
            "accept_terms": True,
            "accept_privacy": True,
        })

        from app.db.database import AsyncSessionLocal
        from app.models import User
        from sqlalchemy import select as sa_select

        async with AsyncSessionLocal() as db:
            result = await db.execute(sa_select(User).where(User.email == "sqluser@nexus.ai"))
            user = result.scalar_one_or_none()
            if user:
                user.is_verified = True
                user.email_verification_token_hash = None
                user.email_verification_token_expires = None
                await db.commit()

        await client.post("/api/auth/login", json={
            "email": "sqluser@nexus.ai",
            "password": "SecurePass123!",
        })

        # Try SQL injection in case number
        response = await client.post("/api/cases", json={
            "case_number": "CASE-001'; DROP TABLE cases; --",
            "title": "SQL Injection Test",
        })
        # Should either create with sanitized name or reject - not crash
        assert response.status_code in (201, 400, 422)

        # Verify cases table still exists
        response = await client.get("/api/cases")
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_xss_prevention():
    """Test XSS attempts in user input are handled."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post("/api/auth/register", json={
            "full_name": "XSS User",
            "email": "xssuser@nexus.ai",
            "password": "SecurePass123!",
            "confirm_password": "SecurePass123!",
            "accept_terms": True,
            "accept_privacy": True,
        })

        from app.db.database import AsyncSessionLocal
        from app.models import User
        from sqlalchemy import select as sa_select

        async with AsyncSessionLocal() as db:
            result = await db.execute(sa_select(User).where(User.email == "xssuser@nexus.ai"))
            user = result.scalar_one_or_none()
            if user:
                user.is_verified = True
                user.email_verification_token_hash = None
                user.email_verification_token_expires = None
                await db.commit()

        await client.post("/api/auth/login", json={
            "email": "xssuser@nexus.ai",
            "password": "SecurePass123!",
        })

        # Try XSS in case title
        xss_title = "<script>alert('xss')</script>"
        response = await client.post("/api/cases", json={
            "case_number": "CASE-XSS-001",
            "title": xss_title,
        })
        assert response.status_code in (201, 400)

        # If created, verify the script tag is stored as-is (not executed)
        if response.status_code == 201:
            case_id = response.json()["id"]
            response = await client.get(f"/api/cases/{case_id}")
            assert response.status_code == 200
            # The title should be returned as stored - frontend should escape on display
            assert "<script>" in response.json()["title"]


@pytest.mark.asyncio
async def test_unauthorized_api_requests():
    """Test unauthorized requests to protected endpoints return 401."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        endpoints = [
            ("GET", "/api/auth/me"),
            ("GET", "/api/cases"),
            ("POST", "/api/cases"),
            ("GET", "/api/consent"),
            ("GET", "/api/echo/cases/00000000-0000-0000-0000-000000000000/gaps"),
        ]
        for method, path in endpoints:
            if method == "GET":
                response = await client.get(path)
            else:
                response = await client.post(path, json={})
            assert response.status_code == 401, f"{method} {path} should return 401"


@pytest.mark.asyncio
async def test_no_secret_exposure_in_errors():
    """Test error messages don't expose secrets or internals."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Trigger an error
        response = await client.get("/api/cases/nonexistent-uuid")
        assert response.status_code in (400, 404, 422)
        body = response.json()
        # Should not contain database connection strings, stack traces, etc.
        assert "DATABASE_URL" not in str(body)
        assert "postgresql" not in str(body).lower()
        assert "stack" not in str(body).lower()
        assert "traceback" not in str(body).lower()
        assert "secret" not in str(body).lower()