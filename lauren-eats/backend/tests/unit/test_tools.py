"""Unit tests for the agent tools.

Each tool is constructed with a :class:`DatabaseService` and called
through its :meth:`run` method with a stub :class:`ToolContext`.  No
LLM transport is involved — these are pure CRUD tests.

The :func:`_app` fixture must be the first reference in the test class
to ensure the app container is wired up before tools are resolved.
"""

from __future__ import annotations

import json
import pytest
from lauren_ai import ToolContext, AgentContext

from app.agents.tools import (
    CheckDietaryInfoTool,
    CheckOrderStatusTool,
    CreateOrderTool,
    CreateReservationTool,
    GetMenuItemDetailsTool,
    HandoffTo,
    SearchMenuTool,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def ctx() -> ToolContext:
    return ToolContext(agent_context=None, tool_use_id="x", turn=1)


async def _seed_category(db, id_="cat-1", name="Mains", slug="mains") -> None:
    await db.execute(
        "INSERT INTO categories (id, name, slug, is_active) VALUES (?, ?, ?, 1)",
        (id_, name, slug),
    )


async def _seed_item(db, id_="item-1", **overrides) -> None:
    defaults = dict(
        id=id_,
        name="Kung Pao Chicken",
        name_zh="宫保鸡丁",
        description="spicy stir-fry",
        price=14.50,
        image="kpc.jpg",
        category_id="cat-1",
        spicy_level=3,
        is_vegetarian=0,
        is_vegan=0,
        is_gluten_free=1,
        is_popular=1,
        is_available=1,
        calories=600,
        preparation_time=15,
        ingredients='["chicken","peanuts"]',
        allergens='["peanut"]',
        tags='["spicy"]',
    )
    defaults.update(overrides)
    await db.execute(
        """INSERT INTO menu_items
           (id, name, name_zh, description, price, image, category_id, spicy_level,
            is_vegetarian, is_vegan, is_gluten_free, is_popular, is_available,
            calories, preparation_time, ingredients, allergens, tags)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        tuple(defaults.values()),
    )


# ---------------------------------------------------------------------------
# SearchMenuTool
# ---------------------------------------------------------------------------


class TestSearchMenuTool:
    async def test_no_args(self, clean_db, ctx, app):
        t = await _resolve(SearchMenuTool, app)
        r = await t.run(ctx)
        assert "error" not in r
        assert r["count"] == 0
        assert "message" in r

    async def test_query(self, clean_db, ctx, app):
        await _seed_category(clean_db)
        await _seed_item(clean_db, "item-1", name="Kung Pao")
        await _seed_item(clean_db, "item-2", name="Fried Rice")
        t = await _resolve(SearchMenuTool, app)
        r = await t.run(ctx, query="Kung")
        assert r["count"] == 1
        assert r["items"][0]["id"] == "item-1"

    async def test_category_filter(self, clean_db, ctx, app):
        await _seed_category(clean_db, "cat-1", "Mains", "mains")
        await _seed_category(clean_db, "cat-2", "Desserts", "desserts")
        await _seed_item(clean_db, "item-1", category_id="cat-1")
        await _seed_item(clean_db, "item-2", category_id="cat-2")
        t = await _resolve(SearchMenuTool, app)
        r = await t.run(ctx, category="mains")
        assert {i["id"] for i in r["items"]} == {"item-1"}

    async def test_limit_capped(self, clean_db, ctx, app):
        await _seed_category(clean_db)
        for i in range(5):
            await _seed_item(clean_db, f"item-{i}")
        t = await _resolve(SearchMenuTool, app)
        # limit=999 is clamped to 50
        r = await t.run(ctx, query="", category="mains", limit=999)
        assert len(r["items"]) == 5
        # limit=0 is clamped to 1
        r = await t.run(ctx, query="", category="mains", limit=0)
        assert len(r["items"]) == 1

    async def test_excludes_unavailable(self, clean_db, ctx, app):
        await _seed_category(clean_db)
        await _seed_item(clean_db, "item-1", is_available=0)
        t = await _resolve(SearchMenuTool, app)
        r = await t.run(ctx, query="Kung")
        assert r["count"] == 0


# ---------------------------------------------------------------------------
# GetMenuItemDetailsTool
# ---------------------------------------------------------------------------


class TestGetMenuItemDetailsTool:
    async def test_no_args(self, clean_db, ctx, app):
        t = await _resolve(GetMenuItemDetailsTool, app)
        r = await t.run(ctx)
        assert "error" in r

    async def test_by_id(self, clean_db, ctx, app):
        await _seed_category(clean_db)
        await _seed_item(clean_db)
        t = await _resolve(GetMenuItemDetailsTool, app)
        r = await t.run(ctx, item_id="item-1")
        assert r["item"]["id"] == "item-1"
        assert r["item"]["name"] == "Kung Pao Chicken"
        assert r["item"]["category"]["slug"] == "mains"

    async def test_by_id_missing(self, clean_db, ctx, app):
        t = await _resolve(GetMenuItemDetailsTool, app)
        r = await t.run(ctx, item_id="nope")
        assert "error" in r

    async def test_by_name_exact(self, clean_db, ctx, app):
        await _seed_category(clean_db)
        await _seed_item(clean_db, name="Kung Pao Chicken")
        t = await _resolve(GetMenuItemDetailsTool, app)
        r = await t.run(ctx, item_name="Kung Pao Chicken")
        assert r["item"]["name"] == "Kung Pao Chicken"

    async def test_by_name_fuzzy(self, clean_db, ctx, app):
        await _seed_category(clean_db)
        await _seed_item(clean_db, name="Kung Pao Chicken")
        t = await _resolve(GetMenuItemDetailsTool, app)
        r = await t.run(ctx, item_name="Kung")
        assert r["item"]["name"] == "Kung Pao Chicken"

    async def test_by_name_missing(self, clean_db, ctx, app):
        t = await _resolve(GetMenuItemDetailsTool, app)
        r = await t.run(ctx, item_name="Does not exist")
        assert "error" in r


# ---------------------------------------------------------------------------
# CheckDietaryInfoTool
# ---------------------------------------------------------------------------


class TestCheckDietaryInfoTool:
    async def test_no_dish(self, clean_db, ctx, app):
        t = await _resolve(CheckDietaryInfoTool, app)
        r = await t.run(ctx, dish_name="")
        assert "error" in r

    async def test_found(self, clean_db, ctx, app):
        await _seed_category(clean_db)
        await _seed_item(clean_db)
        t = await _resolve(CheckDietaryInfoTool, app)
        r = await t.run(ctx, dish_name="Kung Pao Chicken")
        assert r["found"] is True
        assert r["isGlutenFree"] is True
        assert r["spicyLevel"] == 3
        assert r["ingredients"] == ["chicken", "peanuts"]
        assert r["allergens"] == ["peanut"]

    async def test_not_found(self, clean_db, ctx, app):
        t = await _resolve(CheckDietaryInfoTool, app)
        r = await t.run(ctx, dish_name="mystery dish")
        assert r["found"] is False


# ---------------------------------------------------------------------------
# CreateOrderTool
# ---------------------------------------------------------------------------


class TestCreateOrderTool:
    async def test_no_items(self, clean_db, ctx, app):
        t = await _resolve(CreateOrderTool, app)
        r = await t.run(ctx, items=[])
        assert "error" in r

    async def test_invalid_type(self, clean_db, ctx, app):
        t = await _resolve(CreateOrderTool, app)
        r = await t.run(ctx, items=[{"menuItemId": "i", "quantity": 1}], order_type="flying")
        assert "error" in r
        assert "Invalid order type" in r["error"]

    async def test_item_missing_id(self, clean_db, ctx, app):
        t = await _resolve(CreateOrderTool, app)
        r = await t.run(ctx, items=[{"quantity": 1}])
        assert "menuItemId" in r["error"]

    async def test_zero_quantity(self, clean_db, ctx, app):
        t = await _resolve(CreateOrderTool, app)
        r = await t.run(ctx, items=[{"menuItemId": "i", "quantity": 0}])
        assert "Quantity" in r["error"]

    async def test_item_not_found(self, clean_db, ctx, app):
        t = await _resolve(CreateOrderTool, app)
        r = await t.run(ctx, items=[{"menuItemId": "missing", "quantity": 1}])
        assert "not found" in r["error"]

    async def test_item_unavailable(self, clean_db, ctx, app):
        await _seed_category(clean_db)
        await _seed_item(clean_db, "item-1", is_available=0)
        t = await _resolve(CreateOrderTool, app)
        r = await t.run(ctx, items=[{"menuItemId": "item-1", "quantity": 1}])
        assert "unavailable" in r["error"]

    async def test_success(self, clean_db, ctx, app):
        await _seed_category(clean_db)
        await _seed_item(clean_db, "item-1", price=10.0)
        await _seed_item(clean_db, "item-2", price=5.0)
        t = await _resolve(CreateOrderTool, app)
        r = await t.run(
            ctx,
            items=[
                {"menuItemId": "item-1", "quantity": 2},
                {"menu_item_id": "item-2", "quantity": 1, "notes": "extra spicy"},
            ],
            order_type="dine_in",
            table_number="7",
            notes="Birthday",
        )
        assert r["orderCreated"] is True
        assert r["subtotal"] == pytest.approx(25.0)
        assert r["tax"] == pytest.approx(2.0)
        assert r["totalAmount"] == pytest.approx(27.0)
        # And the rows are actually persisted.
        rows = await clean_db.fetch_all("SELECT * FROM orders")
        assert len(rows) == 1
        items = await clean_db.fetch_all("SELECT * FROM order_items")
        assert len(items) == 2
        # Notes persisted
        notes = {it["notes"] for it in items}
        assert "extra spicy" in notes


# ---------------------------------------------------------------------------
# CheckOrderStatusTool
# ---------------------------------------------------------------------------


class TestCheckOrderStatusTool:
    async def test_no_number(self, clean_db, ctx, app):
        t = await _resolve(CheckOrderStatusTool, app)
        r = await t.run(ctx, order_number="")
        assert "error" in r

    async def test_not_found(self, clean_db, ctx, app):
        t = await _resolve(CheckOrderStatusTool, app)
        r = await t.run(ctx, order_number="LE-X-Y")
        assert r["found"] is False

    async def test_found(self, clean_db, ctx, app):
        await clean_db.execute(
            """INSERT INTO orders (id, order_number, status, total_amount, subtotal, tax, type)
               VALUES ('o1', 'LE-X-ABCD', 'preparing', 20, 18, 2, 'dine_in')"""
        )
        t = await _resolve(CheckOrderStatusTool, app)
        r = await t.run(ctx, order_number="LE-X-ABCD")
        assert r["found"] is True
        assert r["status"] == "preparing"


# ---------------------------------------------------------------------------
# CreateReservationTool
# ---------------------------------------------------------------------------


class TestCreateReservationTool:
    async def test_missing_name(self, clean_db, ctx, app):
        t = await _resolve(CreateReservationTool, app)
        r = await t.run(ctx, customer_name="", customer_phone="555", party_size=2, date="2025-12-31", time="19:00")
        assert "error" in r

    async def test_missing_phone(self, clean_db, ctx, app):
        t = await _resolve(CreateReservationTool, app)
        r = await t.run(ctx, customer_name="X", customer_phone="", party_size=2, date="2025-12-31", time="19:00")
        assert "error" in r

    async def test_invalid_party_size(self, clean_db, ctx, app):
        t = await _resolve(CreateReservationTool, app)
        r = await t.run(ctx, customer_name="X", customer_phone="555", party_size=21, date="2025-12-31", time="19:00")
        assert "party_size" in r["error"]

    async def test_non_int_party_size(self, clean_db, ctx, app):
        t = await _resolve(CreateReservationTool, app)
        r = await t.run(ctx, customer_name="X", customer_phone="555", party_size="abc", date="2025-12-31", time="19:00")
        assert "integer" in r["error"]

    async def test_invalid_date(self, clean_db, ctx, app):
        t = await _resolve(CreateReservationTool, app)
        r = await t.run(ctx, customer_name="X", customer_phone="555", party_size=2, date="12/31/2025", time="19:00")
        assert "YYYY-MM-DD" in r["error"]

    async def test_invalid_time(self, clean_db, ctx, app):
        t = await _resolve(CreateReservationTool, app)
        r = await t.run(ctx, customer_name="X", customer_phone="555", party_size=2, date="2025-12-31", time="7pm")
        assert "HH:MM" in r["error"]

    async def test_invalid_occasion(self, clean_db, ctx, app):
        t = await _resolve(CreateReservationTool, app)
        r = await t.run(
            ctx, customer_name="X", customer_phone="555", party_size=2,
            date="2025-12-31", time="19:00", occasion="divorce",
        )
        assert "Invalid occasion" in r["error"]

    async def test_success(self, clean_db, ctx, app):
        t = await _resolve(CreateReservationTool, app)
        r = await t.run(
            ctx, customer_name="Alice", customer_phone="555", party_size=4,
            date="2025-12-31", time="19:00", customer_email="a@x.com",
            occasion="birthday", special_requests="window seat",
        )
        assert r["reservationCreated"] is True
        assert r["partySize"] == 4
        rows = await clean_db.fetch_all("SELECT * FROM reservations")
        assert len(rows) == 1


# ---------------------------------------------------------------------------
# HandoffTo
# ---------------------------------------------------------------------------


class TestHandoffTo:
    async def test_invalid_target(self, clean_db, ctx, app):
        t = await _resolve(HandoffTo, app)
        r = await t.run(ctx, to_agent="Nobody", summary="hi")
        assert "error" in r

    async def test_valid_target_no_conversation(self, clean_db, ctx, app):
        t = await _resolve(HandoffTo, app)
        r = await t.run(ctx, to_agent="Food Expert", summary="wants spicy")
        assert r["status"] == "handed_off"
        assert r["to_agent"] == "Food Expert"

    async def test_valid_target_with_conversation(self, clean_db, ctx, app):
        await clean_db.execute(
            """INSERT INTO conversations (id, agent_type, status)
               VALUES ('c1', 'concierge', 'active')"""
        )
        from lauren_ai import AgentContext as _AC  # any type
        from dataclasses import dataclass

        @dataclass
        class _C:
            metadata: dict

        ctx_with_meta = ToolContext(
            tool_use_id="x", turn=1, agent_context=_C(metadata={"conversation_id": "c1"})
        )
        t = await _resolve(HandoffTo, app)
        r = await t.run(ctx_with_meta, to_agent="Order Assistant", summary="ready to order")
        assert r["status"] == "handed_off"
        row = await clean_db.fetch_one("SELECT agent_type FROM conversations WHERE id = 'c1'")
        assert row["agent_type"] == "ordering"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


async def _resolve(cls, app):
    """Resolve a tool from the app's container."""
    return await app.container.resolve(cls)


@pytest.fixture()
def resolve(app):
    """Return a callable that resolves a tool from the app's container."""

    async def _do(cls):
        return await app.container.resolve(cls)

    return _do
