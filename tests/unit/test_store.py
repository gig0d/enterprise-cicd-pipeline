from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

import pytest
from pydantic import ValidationError

from pipeline_demo_api.models import ItemCreate
from pipeline_demo_api.store import ItemStore, StoreError

pytestmark = pytest.mark.unit


def item(sku: str = "TEST-001") -> ItemCreate:
    return ItemCreate(sku=sku, name=" Demo item ", quantity=2, unit_price=Decimal("12.50"))


def test_store_lifecycle_and_deterministic_seed(store: ItemStore) -> None:
    assert not store.ready
    with pytest.raises(StoreError, match="not ready"):
        store.list_items()
    with pytest.raises(StoreError, match="not ready"):
        store.create(item())
    store.initialize()
    assert store.ready
    assert [entry.sku for entry in store.list_items()] == ["DEMO-001", "DEMO-002"]
    snapshot = store.list_items()
    snapshot.clear()
    assert len(store.list_items()) == 2
    created = store.create(item())
    assert created.id == 3
    assert created.name == "Demo item"
    store.close()
    assert not store.ready
    store.initialize()
    assert len(store.list_items()) == 2


def test_duplicate_sku_is_conflict(store: ItemStore) -> None:
    store.initialize()
    store.create(item())
    with pytest.raises(StoreError) as error:
        store.create(item())
    assert error.value.status_code == 409
    assert error.value.code == "duplicate_sku"


def test_concurrent_creates_have_unique_identifiers(store: ItemStore) -> None:
    store.initialize()
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda index: store.create(item(f"TEST-{index:03}")), range(32)))
    assert {entry.id for entry in results} == set(range(3, 35))
    assert len(store.list_items()) == 34


@pytest.mark.parametrize(
    "changes",
    [
        {"sku": "bad sku"},
        {"name": "   "},
        {"quantity": -1},
        {"quantity": True},
        {"quantity": 1.5},
        {"unit_price": "1.001"},
        {"unit_price": "NaN"},
        {"unit_price": "-1"},
        {"extra": "unexpected"},
    ],
)
def test_invalid_inventory_data_is_rejected(changes: dict[str, object]) -> None:
    data = {"sku": "TEST-001", "name": "Test", "quantity": 2, "unit_price": "12.50"}
    with pytest.raises(ValidationError):
        ItemCreate.model_validate(data | changes)
