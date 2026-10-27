"""Process-local, thread-safe store. Each process starts from the same seed data."""

from threading import Lock

from pipeline_demo_api.models import Item, ItemCreate


class StoreError(Exception):
    def __init__(self, code: str, message: str, status_code: int) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


class ItemStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self._ready = False
        self._items: dict[str, Item] = {}

    def initialize(self) -> None:
        with self._lock:
            self._items = {
                "DEMO-001": Item(
                    id=1, sku="DEMO-001", name="USB-C adapter", quantity=12, unit_price="19.90"
                ),
                "DEMO-002": Item(
                    id=2, sku="DEMO-002", name="Ethernet cable", quantity=25, unit_price="7.50"
                ),
            }
            self._ready = True

    @property
    def ready(self) -> bool:
        with self._lock:
            return self._ready

    def close(self) -> None:
        with self._lock:
            self._ready = False

    def _require_ready(self) -> None:
        if not self._ready:
            raise StoreError("store_unavailable", "The inventory store is not ready.", 503)

    def list_items(self) -> list[Item]:
        with self._lock:
            self._require_ready()
            return sorted(self._items.values(), key=lambda item: item.id)

    def create(self, data: ItemCreate) -> Item:
        with self._lock:
            self._require_ready()
            if data.sku in self._items:
                raise StoreError("duplicate_sku", "An item with this SKU already exists.", 409)
            item = Item(id=len(self._items) + 1, **data.model_dump())
            self._items[item.sku] = item
            return item
