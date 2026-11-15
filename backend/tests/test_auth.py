"""Authentication, token handling and rate limiting."""

from app.core.ratelimit import reset_limiters

from .conftest import auth_headers, login_user, register_user


async def test_register_success_returns_tokens(client):
    body = await register_user(client, "new@example.com")
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["user"]["email"] == "new@example.com"
    assert body["user"]["role"] == "investigator"


async def test_register_rejects_confirm_mismatch(client):
    response = await client.post(
        "/api/auth/register",
        json={
            "full_name": "Mismatch User",
            "email": "mismatch@example.com",
            "password": "LongEnough!1",
            "confirm_password": "Different!1",
            "role": "investigator",
        },
    )
    assert response.status_code == 422


async def test_register_rejects_invalid_email(client):
    response = await client.post(
        "/api/auth/register",
        json={
            "full_name": "Bad Email",
            "email": "not-an-email",
            "password": "LongEnough!1",
            "confirm_password": "LongEnough!1",
            "role": "investigator",
        },
    )
    assert response.status_code == 422


async def test_register_duplicate_email_conflict(client):
    await register_user(client, "dupe@example.com")
    response = await client.post(
        "/api/auth/register",
        json={
            "full_name": "Second Account",
            "email": "dupe@example.com",
            "password": "OtherPass!1",
            "confirm_password": "OtherPass!1",
            "role": "investigator",
        },
    )
    assert response.status_code == 409


async def test_login_success(client):
    await register_user(client, "login@example.com", password="Correct!2026")
    body = await login_user(client, "login@example.com", "Correct!2026")
    assert body["access_token"]


async def test_login_wrong_password(client):
    await register_user(client, "wrongpw@example.com", password="Correct!2026")
    response = await client.post(
        "/api/auth/login",
        json={"email": "wrongpw@example.com", "password": "Wrong!2026"},
    )
    assert response.status_code == 401


async def test_me_requires_token(client):
    response = await client.get("/api/auth/me")
    assert response.status_code == 401


async def test_me_returns_profile(client):
    payload = await register_user(client, "me@example.com", role="supervisor")
    response = await client.get("/api/auth/me", headers=auth_headers(payload["access_token"]))
    assert response.status_code == 200
    assert response.json()["email"] == "me@example.com"
    assert response.json()["role"] == "supervisor"


async def test_refresh_issues_new_access_token(client):
    payload = await register_user(client, "refresh@example.com")
    response = await client.post("/api/auth/refresh", json={"refresh_token": payload["refresh_token"]})
    assert response.status_code == 200
    assert response.json()["access_token"]


async def test_refresh_rejects_access_token(client):
    payload = await register_user(client, "swap@example.com")
    response = await client.post("/api/auth/refresh", json={"refresh_token": payload["access_token"]})
    assert response.status_code == 401


async def test_logout_records_audit_event(client):
    payload = await register_user(client, "logout@example.com")
    response = await client.post("/api/auth/logout", headers=auth_headers(payload["access_token"]))
    assert response.status_code == 200


async def test_login_rate_limited_after_burst(client):
    reset_limiters()
    await register_user(client, "burst@example.com", password="Correct!2026")
    last = None
    for _ in range(11):
        last = await client.post(
            "/api/auth/login",
            json={"email": "burst@example.com", "password": "Wrong!2026"},
        )
    assert last is not None
    assert last.status_code == 429
    assert last.headers.get("Retry-After")
