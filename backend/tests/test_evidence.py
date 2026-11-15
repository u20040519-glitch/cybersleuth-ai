"""Evidence upload, integrity verification and chain of custody."""

import hashlib

from .conftest import sample_jpeg_bytes


async def test_upload_computes_sha256(client, investigator, case, uploaded_jpeg):
    assert uploaded_jpeg["sha256_hash"] == hashlib.sha256(sample_jpeg_bytes()).hexdigest()
    assert uploaded_jpeg["status"] == "uploaded"
    assert uploaded_jpeg["investigation_id"] == case["id"]


async def test_integrity_check_passes(client, investigator, uploaded_jpeg):
    response = await client.post(
        f"/api/evidence/{uploaded_jpeg['id']}/integrity-check",
        headers=investigator["headers"],
    )
    assert response.status_code == 200
    body = response.json()
    assert body["intact"] is True
    assert body["expected_sha256"] == body["actual_sha256"]


async def test_custody_chain_is_valid(client, investigator, uploaded_jpeg):
    response = await client.get(
        f"/api/evidence/{uploaded_jpeg['id']}/custody/verify",
        headers=investigator["headers"],
    )
    assert response.status_code == 200
    assert response.json()["valid"] is True
    assert response.json()["event_count"] >= 1


async def test_custody_event_recorded_on_upload(client, investigator, uploaded_jpeg):
    response = await client.get(
        f"/api/evidence/{uploaded_jpeg['id']}/custody",
        headers=investigator["headers"],
    )
    assert response.status_code == 200
    events = response.json()
    assert any(event["event_type"] == "upload" for event in events)


async def test_disallowed_extension_rejected(client, investigator, case):
    response = await client.post(
        "/api/evidence/upload",
        files={"file": ("payload.exe", b"MZ\x90\x00", "application/octet-stream")},
        data={"investigation_id": case["id"]},
        headers=investigator["headers"],
    )
    assert response.status_code == 400


async def test_upload_requires_authentication(client, case):
    response = await client.post(
        "/api/evidence/upload",
        files={"file": ("sample.jpg", sample_jpeg_bytes(), "image/jpeg")},
        data={"investigation_id": case["id"]},
    )
    assert response.status_code == 401


async def test_evidence_list_scoped_to_investigation(client, investigator, case, uploaded_jpeg):
    response = await client.get(
        "/api/evidence",
        params={"investigation_id": case["id"]},
        headers=investigator["headers"],
    )
    assert response.status_code == 200
    assert [row["id"] for row in response.json()] == [uploaded_jpeg["id"]]


async def test_download_returns_original_bytes(client, investigator, uploaded_jpeg):
    response = await client.get(
        f"/api/evidence/{uploaded_jpeg['id']}/download",
        headers=investigator["headers"],
    )
    assert response.status_code == 200
    assert response.headers.get("X-Evidence-SHA256") == uploaded_jpeg["sha256_hash"]
    assert hashlib.sha256(response.content).hexdigest() == uploaded_jpeg["sha256_hash"]
