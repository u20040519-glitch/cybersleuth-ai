"""Health and platform smoke tests."""


async def test_health_reports_ok(client):
    response = await client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "ok"
    assert body["storage"] == "ok"
    assert "version" in body


async def test_security_headers_present(client):
    response = await client.get("/api/health")
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert response.headers.get("Referrer-Policy") == "no-referrer"


async def test_unknown_route_returns_404(client):
    response = await client.get("/api/definitely-not-a-route")
    assert response.status_code == 404
