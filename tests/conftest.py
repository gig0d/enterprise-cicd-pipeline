from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from pipeline_demo_api.config import Settings
from pipeline_demo_api.main import create_app
from pipeline_demo_api.store import ItemStore


@pytest.fixture
def store() -> ItemStore:
    return ItemStore()


@pytest.fixture
def client(store: ItemStore) -> Iterator[TestClient]:
    config = Settings(environment="test", build_id="a" * 40)
    with TestClient(create_app(config, store)) as test_client:
        yield test_client
