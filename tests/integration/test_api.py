import pytest
from fastapi.testclient import TestClient

from pipeline_demo_api.config import Settings
from pipeline_demo_api.main import create_app
from pipeline_demo_api.store import ItemStore

pytestmark = pytest.mark.integration


def test_health_and_metadata(client: TestClient, store: ItemStore) -> None:
    assert client.get("/health/live").json()["status"] == "alive"
    ready = client.get("/health/ready")
    assert ready.status_code == 200
    assert ready.json() == {"status": "ready", "dependencies": {"inventory_store": "ready"}}
    assert client.get("/api/v1/info").json() == {
        "name": "pipeline-demo-api",
        "version": "0.1.0",
        "environment": "test",
        "build_id": "a" * 40,
    }
    store.close()
    assert client.get("/health/ready").status_code == 503
    assert client.get("/health/live").status_code == 200
    assert client.get("/api/v1/items").status_code == 503


def test_creation_listing_and_conflict(client: TestClient) -> None:
    assert len(client.get("/api/v1/items").json()) == 2
    payload = {"sku": "TEST-001", "name": "Adapter", "quantity": 2, "unit_price": "12.50"}
    created = client.post("/api/v1/items", json=payload)
    assert created.status_code == 201
    assert created.json() == payload | {"id": 3}
    assert client.get("/api/v1/items").json()[-1] == created.json()
    duplicate = client.post("/api/v1/items", json=payload)
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "duplicate_sku"


def test_validation_does_not_echo_request_input(client: TestClient) -> None:
    response = client.post("/api/v1/items", json={"password": "synthetic-private-value"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert "synthetic-private-value" not in response.text


def test_docs_and_http_errors(client: TestClient) -> None:
    assert client.get("/docs").status_code == 200
    assert "/api/v1/items" in client.get("/openapi.json").json()["paths"]
    assert client.get("/missing").json()["error"]["code"] == "http_error"
    assert client.delete("/api/v1/items").status_code == 405


def test_lifespan_closes_store(store: ItemStore) -> None:
    with TestClient(create_app(Settings(environment="test"), store)):
        assert store.ready
    assert not store.ready


def test_unexpected_error_is_sanitized(monkeypatch: pytest.MonkeyPatch, store: ItemStore) -> None:
    def broken() -> list[object]:
        raise RuntimeError("synthetic-sensitive-internal-detail")

    monkeypatch.setattr(store, "list_items", broken)
    with TestClient(
        create_app(Settings(environment="test"), store), raise_server_exceptions=False
    ) as client:
        response = client.get("/api/v1/items")
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_error"
    assert "synthetic-sensitive-internal-detail" not in response.text
