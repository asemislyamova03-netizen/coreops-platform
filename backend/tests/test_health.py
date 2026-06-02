def test_health_endpoint(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["app"] == "CoreOps Platform"
    assert data["status"] in ("ok", "degraded")
    assert data["database"] in ("connected", "unavailable")


def test_root(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()
