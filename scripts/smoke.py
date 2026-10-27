"""Bounded HTTP readiness and functional checks shared by local and container validation."""

import argparse
import time
from typing import Any

import httpx


def wait_ready(client: httpx.Client, timeout: float) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            response = client.get("/health/ready")
            if response.status_code == 200 and response.json().get("status") == "ready":
                return
        except (httpx.HTTPError, ValueError):
            pass
        time.sleep(min(0.5, max(0, deadline - time.monotonic())))
    raise TimeoutError(f"Service did not become ready within {timeout:g} seconds.")


def verify(base_url: str, revision: str, environment: str, timeout: float = 45) -> dict[str, Any]:
    with httpx.Client(base_url=base_url, timeout=2, trust_env=False) as client:
        wait_ready(client, timeout)
        live = client.get("/health/live")
        if live.status_code != 200 or live.json()["status"] != "alive":
            raise ValueError("Liveness verification failed.")
        info = client.get("/api/v1/info")
        info.raise_for_status()
        metadata: dict[str, Any] = info.json()
        if metadata["build_id"] != revision or metadata["environment"] != environment:
            raise ValueError(
                "Deployed revision or environment does not match the expected candidate."
            )
        items = client.get("/api/v1/items")
        items.raise_for_status()
        if [item["sku"] for item in items.json()] != ["DEMO-001", "DEMO-002"]:
            raise ValueError("Expected deterministic inventory seed data.")
        payload = {"sku": "SMOKE-001", "name": "Smoke item", "quantity": 1, "unit_price": "1.25"}
        created = client.post("/api/v1/items", json=payload)
        if created.status_code != 201 or created.json() != payload | {"id": 3}:
            raise ValueError("Item creation smoke check failed.")
        if client.post("/api/v1/items", json=payload).status_code != 409:
            raise ValueError("Duplicate SKU was not rejected.")
        if client.post("/api/v1/items", json={"quantity": -1}).status_code != 422:
            raise ValueError("Invalid input was not rejected.")
        if client.get("/api/v1/items").json()[-1] != created.json():
            raise ValueError("Created item is not visible in the inventory.")
        if client.get("/docs").status_code != 200:
            raise ValueError("API documentation endpoint is unavailable.")
        return metadata


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--revision", required=True)
    parser.add_argument("--environment", default="development")
    parser.add_argument("--timeout", type=float, default=45)
    args = parser.parse_args()
    print(verify(args.url, args.revision, args.environment, args.timeout))


if __name__ == "__main__":
    main()
