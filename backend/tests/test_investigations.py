"""Investigation CRUD and row-level access control."""

from .conftest import auth_headers, register_user


async def test_create_investigation(client, investigator):
    response = await client.post(
        "/api/investigations",
        json={
            "case_id": "CASE-CREATE-1",
            "title": "Created in test",
            "category": "fraud",
            "priority": "low",
            "status": "draft",
        },
        headers=investigator["headers"],
    )
    assert response.status_code == 201
    body = response.json()
    assert body["case_id"] == "CASE-CREATE-1"
    assert body["status"] == "draft"
    assert body["evidence_count"] == 0


async def test_duplicate_case_id_conflict(client, investigator):
    payload = {
        "case_id": "CASE-DUPE-1",
        "title": "First",
        "category": "fraud",
        "priority": "low",
        "status": "draft",
    }
    first = await client.post("/api/investigations", json=payload, headers=investigator["headers"])
    assert first.status_code == 201
    second = await client.post(
        "/api/investigations",
        json={**payload, "title": "Second"},
        headers=investigator["headers"],
    )
    assert second.status_code == 409


async def test_owner_can_read_back(client, investigator, case):
    response = await client.get(f"/api/investigations/{case['id']}", headers=investigator["headers"])
    assert response.status_code == 200
    assert response.json()["case_id"] == "CASE-TEST-001"


async def test_other_investigator_gets_404(client, investigator, case):
    other = await register_user(client, "other@example.com", full_name="Other Investigator")
    response = await client.get(
        f"/api/investigations/{case['id']}",
        headers=auth_headers(other["access_token"]),
    )
    # RLS hides the row, and the route reports 404 without disclosing existence.
    assert response.status_code == 404


async def test_supervisor_without_membership_gets_404(client, supervisor, case):
    response = await client.get(f"/api/investigations/{case['id']}", headers=supervisor["headers"])
    assert response.status_code == 404


async def test_unauthenticated_gets_401(client, case):
    response = await client.get(f"/api/investigations/{case['id']}")
    assert response.status_code == 401


async def test_investigation_status_update(client, investigator, case):
    response = await client.patch(
        f"/api/investigations/{case['id']}",
        json={"status": "closed"},
        headers=investigator["headers"],
    )
    assert response.status_code == 200
    assert response.json()["status"] == "closed"
