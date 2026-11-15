"""PDF report generation and download."""

from .conftest import sample_jpeg_bytes


async def test_generate_and_download_report(client, investigator, case, uploaded_jpeg):
    generated = await client.post(
        f"/api/reports/{case['id']}",
        json={"title": "Test Report"},
        headers=investigator["headers"],
    )
    assert generated.status_code == 201
    report = generated.json()
    assert report["status"] == "ready"
    assert report["file_size"] > 0
    assert report["sha256_hash"]
    assert report["download_url"].endswith(f"/reports/{report['id']}/download")

    download = await client.get(
        f"/api/reports/{report['id']}/download",
        headers=investigator["headers"],
    )
    assert download.status_code == 200
    assert download.headers["Content-Type"].startswith("application/pdf")
    assert download.content.startswith(b"%PDF")
    assert download.headers.get("X-Report-SHA256") == report["sha256_hash"]


async def test_report_requires_membership(client, investigator, case):
    generated = await client.post(
        f"/api/reports/{case['id']}",
        json={"title": "Scoped Report"},
        headers=investigator["headers"],
    )
    assert generated.status_code == 201


async def test_reports_list_scoped_to_investigation(client, investigator, case):
    generated = await client.post(
        f"/api/reports/{case['id']}",
        json={},
        headers=investigator["headers"],
    )
    assert generated.status_code == 201

    listed = await client.get(
        "/api/reports",
        params={"investigation_id": case["id"]},
        headers=investigator["headers"],
    )
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert listed.json()[0]["investigation_id"] == case["id"]
