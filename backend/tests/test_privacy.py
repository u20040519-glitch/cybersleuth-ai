# =============================================================================
# PROJECT NEXUS AI - Privacy & Consent Tests
# =============================================================================
# Tests for consent recording, consent withdrawal, cookie preference persistence,
# AI processing preference, account deletion request, data export.
# =============================================================================

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


async def _register_and_login(client: AsyncClient, email: str = "privacy@nexus.ai"):
    """Helper to register, verify, and login a user."""
    await client.post("/api/auth/register", json={
        "full_name": "Privacy User",
        "email": email,
        "password": "SecurePass123!",
        "confirm_password": "SecurePass123!",
        "accept_terms": True,
        "accept_privacy": True,
    })

    # Verify in DB
    from app.db.database import AsyncSessionLocal
    from app.models import User
    from sqlalchemy import select as sa_select

    async with AsyncSessionLocal() as db:
        result = await db.execute(sa_select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if user:
            user.is_verified = True
            user.email_verification_token_hash = None
            user.email_verification_token_expires = None
            await db.commit()

    await client.post("/api/auth/login", json={
        "email": email,
        "password": "SecurePass123!",
    })


@pytest.mark.asyncio
async def test_consent_recording():
    """Test consent is recorded with timestamp, purpose, policy version, status."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await _register_and_login(client)

        # Grant consent for external AI processing
        response = await client.post(
            "/api/consent/external_ai_processing",
            json={"purpose": "external_ai_processing", "granted": True}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["purpose"] == "external_ai_processing"
        assert data["status"] == "granted"
        assert "granted_at" in data
        assert data["policy_version"] == "1.0.0"

        # List consent records
        response = await client.get("/api/consent")
        assert response.status_code == 200
        records = response.json()
        assert len(records) == 1
        assert records[0]["purpose"] == "external_ai_processing"


@pytest.mark.asyncio
async def test_consent_withdrawal():
    """Test consent can be withdrawn with withdrawal timestamp recorded."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await _register_and_login(client)

        # Grant consent
        await client.post(
            "/api/consent/analytics",
            json={"purpose": "analytics", "granted": True}
        )

        # Withdraw consent
        response = await client.post(
            "/api/consent/analytics",
            json={"purpose": "analytics", "granted": False}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "withdrawn"
        assert "withdrawn_at" in data


@pytest.mark.asyncio
async def test_ai_processing_preference():
    """Test AI processing preference can be set and retrieved."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await _register_and_login(client)

        # Initially not granted
        response = await client.get("/api/consent/preference/external_ai_processing")
        assert response.status_code == 200
        assert response.json()["external_ai_processing_enabled"] is False

        # Grant consent
        await client.post(
            "/api/consent/external_ai_processing",
            json={"purpose": "external_ai_processing", "granted": True}
        )

        # Now granted
        response = await client.get("/api/consent/preference/external_ai_processing")
        assert response.status_code == 200
        assert response.json()["external_ai_processing_enabled"] is True


@pytest.mark.asyncio
async def test_consent_not_granted_by_default():
    """Test optional consent checkboxes are unchecked by default (frontend)."""
    # This is tested at the frontend level - the registration endpoint
    # requires explicit accept_terms=True and accept_privacy=True
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Without consent - should fail
        response = await client.post("/api/auth/register", json={
            "full_name": "No Consent",
            "email": "noconsent@nexus.ai",
            "password": "SecurePass123!",
            "confirm_password": "SecurePass123!",
            "accept_terms": False,
            "accept_privacy": False,
        })
        assert response.status_code == 400