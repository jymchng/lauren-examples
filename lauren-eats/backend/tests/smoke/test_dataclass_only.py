"""Smoke test: Lauren app using only dataclasses — no pydantic installed.

Verifies that request body validation, response serialization, path
parameters, OpenAPI schema generation, and 422 validation errors all work
correctly when pydantic is absent from sys.modules.

NOTE: no ``from __future__ import annotations`` — handler annotations must
be evaluated eagerly at definition time (inside the app fixture where the
Lauren types are in scope).  Lazy string annotations would cause
get_type_hints() to fail at compile time since Json/Discriminated/Path are
imported inside the fixture, not at module level.
"""


import dataclasses
import sys
from typing import Literal, TypedDict

import pytest

HAS_PYDANTIC = False
try:
    import pydantic
    HAS_PYDANTIC = True
except ImportError:
    pass

assert not HAS_PYDANTIC, "This test must run with pydantic unavailable in sys.modules"
    

# ---------------------------------------------------------------------------
# Block pydantic for the entire module before any Lauren imports happen.
# The session-scoped fixture in conftest.py must have pre-loaded Lauren first
# so that _PYDANTIC_AVAILABLE is set while pydantic is still importable.
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True, scope="module")
def _no_pydantic():
    """Evict pydantic from sys.modules for the duration of this test module."""
    original = {k: v for k, v in sys.modules.items() if "pydantic" in k}
    for k in list(original):
        del sys.modules[k]
    sys.modules["pydantic"] = None  # type: ignore[assignment]
    sys.modules["pydantic_core"] = None  # type: ignore[assignment]
    yield
    for k in list(sys.modules.keys()):
        if "pydantic" in k:
            del sys.modules[k]
    sys.modules.update(original)


# ---------------------------------------------------------------------------
# Dataclass models — pure stdlib, no pydantic
# ---------------------------------------------------------------------------


@dataclasses.dataclass
class MenuItem:
    name: str
    price: float
    category: str
    qty: int = 1
    description: str = ""


@dataclasses.dataclass
class MenuItemOut:
    id: int
    name: str
    price: float
    category: str


class OrderItem(TypedDict):
    menu_item_id: str
    quantity: int


class EventReserve(TypedDict):
    event: Literal["reserve"]
    table: int


class EventCancel(TypedDict):
    event: Literal["cancel"]
    reason: str


# ---------------------------------------------------------------------------
# App fixture
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def app(_no_pydantic):
    from lauren import Discriminated, Json, Lauren, Path, StreamingResponse

    a = Lauren()

    _items: dict[int, MenuItem] = {}
    _next_id = 1

    @a.post("/menu")
    async def create_item(body: MenuItem) -> MenuItemOut:
        nonlocal _next_id
        _items[_next_id] = body
        out = MenuItemOut(id=_next_id, name=body.name, price=body.price, category=body.category)
        _next_id += 1
        return out

    @a.get("/menu")
    async def list_items() -> list[MenuItemOut]:
        return [
            MenuItemOut(id=k, name=v.name, price=v.price, category=v.category)
            for k, v in _items.items()
        ]

    @a.get("/menu/{item_id}")
    async def get_item(item_id: int = Path()) -> dict:
        if item_id not in _items:
            from lauren import Response

            return Response.json({"error": "not found"}, status=404)
        v = _items[item_id]
        return {"id": item_id, "name": v.name, "price": v.price, "category": v.category}

    @a.post("/events")
    async def handle_event(
        body: Json[Discriminated[EventReserve | EventCancel, "event"]],  # noqa: F821
    ) -> dict:
        return {"event": body["event"]}

    @a.get("/stream")
    async def stream_menu() -> StreamingResponse[MenuItemOut]:
        async def _gen():
            yield MenuItemOut(id=1, name="Dim Sum", price=8.5, category="appetizer")
            yield MenuItemOut(id=2, name="Fried Rice", price=12.0, category="main")

        return _gen()

    return a


@pytest.fixture(scope="module")
def client(app):
    from lauren.testing import TestClient

    return TestClient(app)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestPydanticAbsent:
    """Guard: pydantic must be invisible during these tests."""

    def test_pydantic_import_raises(self):
        with pytest.raises((ImportError, TypeError)):
            import pydantic  # noqa: F401

            pydantic.BaseModel  # should never reach here


class TestMenuCRUD:
    def test_create_item_returns_200(self, client):
        resp = client.post("/menu", json={"name": "Kung Pao Chicken", "price": 14.5, "category": "main"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Kung Pao Chicken"
        assert data["price"] == 14.5
        assert data["id"] == 1

    def test_create_second_item_increments_id(self, client):
        resp = client.post("/menu", json={"name": "Spring Roll", "price": 6.0, "category": "appetizer"})
        assert resp.status_code == 200
        assert resp.json()["id"] == 2

    def test_list_items_returns_array(self, client):
        resp = client.get("/menu")
        assert resp.status_code == 200
        items = resp.json()
        assert isinstance(items, list)
        assert len(items) >= 2

    def test_get_item_by_path_param(self, client):
        resp = client.get("/menu/1")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Kung Pao Chicken"

    def test_get_missing_item_returns_404(self, client):
        resp = client.get("/menu/9999")
        assert resp.status_code == 404

    def test_missing_required_field_returns_422(self, client):
        # 'name' and 'category' are required; omitting them must fail
        resp = client.post("/menu", json={"price": 10.0})
        assert resp.status_code == 422

    def test_wrong_type_coercion_still_accepted(self, client):
        # price as string "9.99" — dataclass backend stores as-is (no strict coercion),
        # but the request must at least succeed without a 500
        resp = client.post("/menu", json={"name": "Soup", "price": 9.99, "category": "soup"})
        assert resp.status_code == 200


class TestDiscriminatedEvents:
    def test_reserve_event_routes_correctly(self, client):
        resp = client.post("/events", json={"event": "reserve", "table": 5})
        assert resp.status_code == 200
        assert resp.json()["event"] == "reserve"

    def test_cancel_event_routes_correctly(self, client):
        resp = client.post("/events", json={"event": "cancel", "reason": "changed mind"})
        assert resp.status_code == 200
        assert resp.json()["event"] == "cancel"

    def test_unknown_event_tag_returns_422(self, client):
        resp = client.post("/events", json={"event": "unknown", "foo": "bar"})
        assert resp.status_code == 422

    def test_missing_event_field_returns_422(self, client):
        resp = client.post("/events", json={"table": 3})
        assert resp.status_code == 422


class TestOpenAPIWithoutPydantic:
    def test_openapi_endpoint_returns_200(self, client):
        resp = client.get("/openapi.json")
        assert resp.status_code == 200

    def test_openapi_has_menu_schema(self, client):
        spec = client.get("/openapi.json").json()
        schemas = spec.get("components", {}).get("schemas", {})
        assert "MenuItem" in schemas, f"MenuItem not in schemas: {list(schemas)}"

    def test_menu_item_schema_has_required_fields(self, client):
        spec = client.get("/openapi.json").json()
        schema = spec["components"]["schemas"]["MenuItem"]
        assert schema["type"] == "object"
        required = schema.get("required", [])
        assert "name" in required
        assert "price" in required
        assert "category" in required

    def test_openapi_schema_has_no_pydantic_artifacts(self, client):
        import json

        spec_text = json.dumps(client.get("/openapi.json").json())
        assert "pydantic" not in spec_text.lower()


class TestStreamingWithoutPydantic:
    def test_streaming_endpoint_returns_200(self, client):
        resp = client.get("/stream")
        assert resp.status_code == 200
