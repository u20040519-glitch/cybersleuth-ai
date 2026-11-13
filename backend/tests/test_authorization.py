# =============================================================================
# PROJECT NEXUS AI - Authorization Tests
# =============================================================================
# Tests for Row Level Security, case access isolation, evidence access isolation,
# report access isolation. Verifies User A cannot access User B's data.
# =============================================================================

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


async def _register_and_verify(client: AsyncClient, email: str, full_name: str = "Test User"):
    """Helper to register and verify a user."""
    await client.post("/api/auth/register", json={
        "full_name": full_name,
        "email": email,
        "password": "SecurePass123!",
        "confirm_password": "SecurePass123!",
        "accept_terms": True,
        "accept_privacy": True,
    })

    # Manually verify in DB
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


async def _login(client: AsyncClient, email: str, password: str = "SecurePass123!"):
    """Helper to login and return cookies."""
    response = await client.post("/api/auth/login", json={
        "email": email,
        "password": password,
    })
    assert response.status_code == 200
    return response.cookies


@pytest.mark.asyncio
async def test_user_cannot_access_other_users_cases():
    """Test User A cannot read User B's cases (RLS enforcement)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client_a:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client_b:
            # Register and login User A
            await _register_and_verify(client_a, "usera@nexus.ai", "User A")
            await _login(client_a, "usera@nexus.ai")

            # Register and login User B
            await _register_and_verify(client_b, "userb@nexus.ai", "User B")
            await _login(client_b, "userb@nexus.ai")

            # User A creates a case
            response = await client_a.post("/api/cases", json={
                "case_number": "CASE-A-001",
                "title": "User A Case",
                "description": "Private case of User A",
            })
            assert response.status_code == 201
            case_a_id = response.json()["id"]

            # User B tries to list cases - should not see User A's case
            response = await client_b.get("/api/cases")
            assert response.status_code == 200
            cases = response.json()
            case_ids = [c["id"] for c in cases]
            assert case_a_id not in case_ids, "User B should not see User A's case"

            # User B tries to access User A's case directly
            response = await client_b.get(f"/api/cases/{case_a_id}")
            assert response.status_code == 403, "User B should be forbidden from accessing User A's case"


@pytest.mark.asyncio
async def test_user_cannot_access_other_users_evidence():
    """Test User A cannot access User B's evidence files."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client_a:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client_b:
            # Register and login both users
            await _register_and_verify(client_a, "evidencea@nexus.ai", "Evidence User A")
            await _login(client_a, "evidencea@nexus.ai")

            await _register_and_verify(client_b, "evidenceb@nexus.ai", "Evidence User B")
            await _login(client_b, "evidenceb@nexus.ai")

            # User A creates a case
            response = await client_a.post("/api/cases", json={
                "case_number": "CASE-EVID-A-001",
                "title": "Evidence Case A",
                "description": "Case with evidence",
            })
            assert response.status_code == 201
            case_a_id = response.json()["id"]

            # User A uploads evidence
            response = await client_a.post(
                f"/evidence/upload?case_id={case_a_id}",
                files={"file": ("secret.txt", b"secret evidence content", "text/plain")}
            )
            assert response.status_code == 201

            # User B tries to list evidence for User A's case
            response = await client_b.get(f"/evidence/case/{case_a_id}")
            assert response.status_code == 403, "User B should not access User A's evidence"


@pytest.mark.asyncio
async def test_user_cannot_access_other_users_reports():
    """Test User A cannot read User B's investigation reports."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client_a:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client_b:
            await _register_and_verify(client_a, "reporta@nexus.ai", "Report User A")
            await _login(client_a, "reporta@nexus.ai")

            await _register_and_verify(client_b, "reportb@nexus.ai", "Report User B")
            await _login(client_b, "reportb@nexus.ai")

            # User A creates a case and report
            response = await client_a.post("/api/cases", json={
                "case_number": "CASE-REP-A-001",
                "title": "Report Case A",
                "description": "Case for report test",
            })
            assert response.status_code == 201
            case_a_id = response.json()["id"]

            response = await client_a.post(
                f"/reports/cases/{case_a_id}",
                params={"report_title": "Secret Report", "report_content": "Confidential findings"}
            )
            assert response.status_code == 201

            # User B tries to list reports for User A's case
            response = await client_b.get(f"/reports/cases/{case_a_id}")
            assert response.status_code == 403, "User B should not access User A's reports"


@pytest.mark.asyncio
async def test_user_cannot_delete_other_users_reports():
    """Test User A cannot delete User B's reports."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client_a:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client_b:
            await _register_and_verify(client_a, "delreporta@nexus.ai", "Del User A")
            await _login(client_a, "delreporta@nexus.ai")

            await _register_and_verify(client_b, "delreportb@nexus.ai", "Del User B")
            await _login(client_b, "delreportb@nexus.ai")

            # User A creates a case and report
            response = await client_a.post("/api/cases", json={
                "case_number": "CASE-DEL-A-001",
                "title": "Delete Report Case A",
            })
            assert response.status_code == 201
            case_a_id = response.json()["id"]

            response = await client_a.post(
                f"/reports/cases/{case_a_id}",
                params={"report_title": "Target Report", "report_content": "To be protected"}
            )
            assert response.status_code == 201
            report_id = response.json()["id"]

            # User B tries to access/delete User A's report
            response = await client_b.get(f"/reports/cases/{case_a_id}")
            assert response.status_code == 403


@pytest.mark.asyncio
async def test_case_owner_can_access_own_case():
    """Test case owner can access their own case."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await _register_and_verify(client, "owner@nexus.ai", "Owner")
        await _login(client, "owner@nexus.ai")

        response = await client.post("/api/cases", json={
            "case_number": "CASE-OWN-001",
            "title": "Owner Case",
            "description": "Owned by the user",
        })
        assert response.status_code == 201
        case_id = response.json()["id"]

        # Owner can access their case
        response = await client.get(f"/api/cases/{case_id}")
        assert response.status_code == 200
        assert response.json()["title"] == "Owner Case"


@pytest.mark.asyncio
async def test_unauthorized_user_cannot_access_protected_routes():
    """Test unauthenticated requests are rejected."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/auth/me")
        assert response.status_code == 401

        response = await client.get("/api/cases")
        assert response.status_code == 401

        response = await client.post("/api/cases", json={
            "case_number": "CASE-UN-001",
            "title": "Unauthorized",
        })
        assert response.status_code == 401