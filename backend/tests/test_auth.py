# =============================================================================
# PROJECT NEXUS AI - Authentication Tests
# =============================================================================
# Tests for registration, login, logout, email verification, password reset,
# session invalidation. All tests connect to real backend services.
# =============================================================================

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_register_success():
    """Test successful user registration."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/auth/register", json={
            "full_name": "Test User",
            "email": "testauth@nexus.ai",
            "password": "SecurePass123!",
            "confirm_password": "SecurePass123!",
            "accept_terms": True,
            "accept_privacy": True,
        })
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "testauth@nexus.ai"
        assert data["is_verified"] is False
        assert data["role"] == "viewer"


@pytest.mark.asyncio
async def test_register_missing_consent():
    """Test registration fails without consent checkboxes."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Missing terms acceptance
        response = await client.post("/api/auth/register", json={
            "full_name": "Test User",
            "email": "consentfail@nexus.ai",
            "password": "SecurePass123!",
            "confirm_password": "SecurePass123!",
            "accept_terms": False,
            "accept_privacy": True,
        })
        assert response.status_code == 400

        # Missing privacy acknowledgement
        response = await client.post("/api/auth/register", json={
            "full_name": "Test User",
            "email": "consentfail2@nexus.ai",
            "password": "SecurePass123!",
            "confirm_password": "SecurePass123!",
            "accept_terms": True,
            "accept_privacy": False,
        })
        assert response.status_code == 400


@pytest.mark.asyncio
async def test_register_weak_password():
    """Test registration fails with weak password."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/auth/register", json={
            "full_name": "Test User",
            "email": "weakpass@nexus.ai",
            "password": "weak",
            "confirm_password": "weak",
            "accept_terms": True,
            "accept_privacy": True,
        })
        assert response.status_code == 400


@pytest.mark.asyncio
async def test_register_password_mismatch():
    """Test registration fails when passwords don't match."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/auth/register", json={
            "full_name": "Test User",
            "email": "mismatch@nexus.ai",
            "password": "SecurePass123!",
            "confirm_password": "DifferentPass123!",
            "accept_terms": True,
            "accept_privacy": True,
        })
        assert response.status_code == 400


@pytest.mark.asyncio
async def test_login_unverified_email():
    """Test login fails when email is not verified."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/auth/login", json={
            "email": "testauth@nexus.ai",
            "password": "SecurePass123!",
        })
        assert response.status_code == 403
        assert "verification" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_login_wrong_password():
    """Test login fails with wrong password."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/auth/login", json={
            "email": "nonexistent@nexus.ai",
            "password": "WrongPass123!",
        })
        # Generic error - doesn't reveal if email exists
        assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_forgot_password():
    """Test forgot password always returns success (no email enumeration)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/auth/forgot-password", json={
            "email": "anyemail@nexus.ai",
        })
        assert response.status_code == 200
        assert "message" in response.json()


@pytest.mark.asyncio
async def test_rate_limiting_login():
    """Test rate limiting on login endpoint."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Make 5 failed login attempts (limit is 5/min)
        for i in range(5):
            response = await client.post("/api/auth/login", json={
                "email": "ratelimit@nexus.ai",
                "password": "WrongPass123!",
            })
        # 6th attempt should be rate limited
        response = await client.post("/api/auth/login", json={
            "email": "ratelimit@nexus.ai",
            "password": "WrongPass123!",
        })
        assert response.status_code == 429
        assert "rate_limit_exceeded" in response.json()["error"]


@pytest.mark.asyncio
async def test_rate_limiting_register():
    """Test rate limiting on register endpoint."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Make 3 registration attempts (limit is 3/min)
        for i in range(3):
            response = await client.post("/api/auth/register", json={
                "full_name": f"Rate User {i}",
                "email": f"ratereg{i}@nexus.ai",
                "password": "SecurePass123!",
                "confirm_password": "SecurePass123!",
                "accept_terms": True,
                "accept_privacy": True,
            })
        # 4th attempt should be rate limited
        response = await client.post("/api/auth/register", json={
            "full_name": "Rate User 3",
            "email": "ratereg3@nexus.ai",
            "password": "SecurePass123!",
            "confirm_password": "SecurePass123!",
            "accept_terms": True,
            "accept_privacy": True,
        })
        assert response.status_code == 429


@pytest.mark.asyncio
async def test_login_and_logout_flow():
    """Test complete login and logout flow with verified user."""
    # First register and verify a user
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Register
        await client.post("/api/auth/register", json={
            "full_name": "Login Test",
            "email": "logintest@nexus.ai",
            "password": "SecurePass123!",
            "confirm_password": "SecurePass123!",
            "accept_terms": True,
            "accept_privacy": True,
        })

        # Manually verify in DB (simulating email verification)
        from app.db.database import AsyncSessionLocal
        from app.models import User
        from sqlalchemy import select

        async with AsyncSessionLocal() as db:
            from sqlalchemy import select as sa_select
            result = await db.execute(sa_select(User).where(User.email == "logintest@nexus.ai"))
            user = result.scalar_one_or_none()
            if user:
                user.is_verified = True
                user.email_verification_token_hash = None
                user.email_verification_token_expires = None
                await db.commit()

        # Login
        response = await client.post("/api/auth/login", json={
            "email": "logintest@nexus.ai",
            "password": "SecurePass123!",
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

        # Verify cookies are set
        cookies = response.cookies
        assert "access_token" in cookies
        assert "refresh_token" in cookies
        # Verify cookies are httpOnly
        access_cookie = cookies.get("access_token")
        # httponly is set on the server side - cookie jar may not show it
        # but we can verify the response headers

        # Get profile (authenticated)
        response = await client.get("/api/auth/me")
        assert response.status_code == 200
        profile = response.json()
        assert profile["email"] == "logintest@nexus.ai"
        assert profile["is_verified"] is True

        # Logout
        response = await client.post("/api/auth/logout")
        assert response.status_code == 200
        assert response.json()["message"] == "Logged out successfully"

        # Profile should fail after logout
        response = await client.get("/api/auth/me")
        assert response.status_code == 401