"""Unit tests for the service layer.

Exercises the P0-acceptance criteria for MenuService, OrderService,
ReservationService and AdminService — the routes a real HTTP client
travels through during the integration tests, but at unit granularity
so regressions surface as a single failing test, not a 500.
"""

from __future__ import annotations

import pytest

from app.services.admin_service import AdminService
from app.services.menu_service import MenuService
from app.services.order_service import OrderService
from app.services.reservation_service import ReservationService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _seed_category(db, id_: str = "cat-1", name: str = "Mains") -> None:
    await db.execute(
        "INSERT INTO categories (id, name, slug, is_active) VALUES (?, ?, ?, 1)",
        (id_, name, id_),
    )


async def _seed_user(db, id_: str = "u1", name: str = "Alice", role: str = "customer") -> None:
    await db.execute(
        "INSERT INTO users (id, name, email, role) VALUES (?, ?, ?, ?)",
        (id_, name, f"{id_}@x.com", role),
    )


async def _seed_item(db, id_: str = "item-1", **overrides) -> None:
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
        ingredients="chicken, peanuts",
        allergens="peanut",
        tags="spicy, popular",
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
# MenuService
# ---------------------------------------------------------------------------


class TestMenuService:
    async def test_list_menu_items_empty(self, clean_db, menu_service: MenuService):
        page = await menu_service.list_menu_items()
        assert page["data"] == []
        assert page["pagination"] == {
            "page": 1,
            "limit": 12,
            "total": 0,
            "totalPages": 0,
            "hasMore": False,
        }

    async def test_list_menu_items_returns_pagination(self, clean_db, menu_service: MenuService):
        await _seed_category(clean_db)
        for i in range(3):
            await _seed_item(clean_db, id_=f"item-{i}")
        page = await menu_service.list_menu_items(page=1, limit=2)
        assert page["pagination"]["total"] == 3
        assert page["pagination"]["totalPages"] == 2
        assert page["pagination"]["hasMore"] is True
        assert len(page["data"]) == 2

    async def test_list_filters_by_category_slug(self, clean_db, menu_service: MenuService):
        await _seed_category(clean_db, "cat-1", "Mains")
        await _seed_category(clean_db, "cat-2", "Desserts")
        await _seed_item(clean_db, "item-1", category_id="cat-1")
        await _seed_item(clean_db, "item-2", category_id="cat-2")
        page = await menu_service.list_menu_items(category="cat-1")
        assert len(page["data"]) == 1
        assert page["data"][0]["id"] == "item-1"

    async def test_list_search(self, clean_db, menu_service: MenuService):
        await _seed_category(clean_db)
        await _seed_item(clean_db, "item-1", name="Kung Pao")
        await _seed_item(clean_db, "item-2", name="Fried Rice")
        page = await menu_service.list_menu_items(search="Kung")
        assert {i["id"] for i in page["data"]} == {"item-1"}

    async def test_list_dietary_filters(self, clean_db, menu_service: MenuService):
        await _seed_category(clean_db)
        await _seed_item(clean_db, "item-1", is_vegetarian=1)
        await _seed_item(clean_db, "item-2", is_vegetarian=0)
        page = await menu_service.list_menu_items(is_vegetarian=True)
        assert {i["id"] for i in page["data"]} == {"item-1"}

    async def test_list_spicy_level_filter(self, clean_db, menu_service: MenuService):
        await _seed_category(clean_db)
        await _seed_item(clean_db, "item-1", spicy_level=2)
        await _seed_item(clean_db, "item-2", spicy_level=5)
        page = await menu_service.list_menu_items(spicy_level=3)
        assert {i["id"] for i in page["data"]} == {"item-1"}

    async def test_list_popular_filter(self, clean_db, menu_service: MenuService):
        await _seed_category(clean_db)
        await _seed_item(clean_db, "item-1", is_popular=1)
        await _seed_item(clean_db, "item-2", is_popular=0)
        page = await menu_service.list_menu_items(is_popular=True)
        assert {i["id"] for i in page["data"]} == {"item-1"}

    async def test_list_excludes_unavailable(self, clean_db, menu_service: MenuService):
        await _seed_category(clean_db)
        await _seed_item(clean_db, "item-1", is_available=0)
        page = await menu_service.list_menu_items()
        assert page["data"] == []

    async def test_get_menu_item_returns_none_for_missing(self, clean_db, menu_service: MenuService):
        assert await menu_service.get_menu_item("nope") is None

    async def test_get_menu_item_includes_category(self, clean_db, menu_service: MenuService):
        await _seed_category(clean_db, "cat-1", "Mains")
        await _seed_item(clean_db)
        item = await menu_service.get_menu_item("item-1")
        assert item is not None
        assert item["category"]["name"] == "Mains"
        assert item["price"] == 14.50
        assert item["isGlutenFree"] is True

    async def test_update_menu_item_no_op(self, clean_db, menu_service: MenuService):
        await _seed_category(clean_db)
        await _seed_item(clean_db)
        result = await menu_service.update_menu_item("item-1", {})
        assert result is not None
        assert result["id"] == "item-1"

    async def test_update_menu_item_partial(self, clean_db, menu_service: MenuService):
        await _seed_category(clean_db)
        await _seed_item(clean_db)
        result = await menu_service.update_menu_item("item-1", {"isAvailable": False, "price": 19.99})
        assert result is not None
        assert result["isAvailable"] is False
        assert result["price"] == 19.99

    async def test_update_menu_item_missing_returns_none(self, clean_db, menu_service: MenuService):
        assert await menu_service.update_menu_item("nope", {"price": 1.0}) is None

    async def test_list_categories_with_items(self, clean_db, menu_service: MenuService):
        await _seed_category(clean_db, "cat-1", "Mains")
        await _seed_item(clean_db, "item-1")
        categories = await menu_service.list_categories()
        assert len(categories) == 1
        assert categories[0]["menuItems"][0]["id"] == "item-1"

    async def test_list_categories_excludes_inactive(self, clean_db, menu_service: MenuService):
        await db_execute(
            clean_db, "INSERT INTO categories (id, name, slug, is_active) VALUES ('cat-x', 'X', 'x', 0)"
        )
        cats = await menu_service.list_categories()
        assert cats == []


async def db_execute(db, sql, params=()):
    return await db.execute(sql, params)


# ---------------------------------------------------------------------------
# OrderService
# ---------------------------------------------------------------------------


class TestOrderService:
    async def test_list_orders_empty(self, clean_db, order_service: OrderService):
        assert await order_service.list_orders() == []

    async def test_list_orders_with_status_filter(self, clean_db, order_service: OrderService):
        await _seed_category(clean_db)
        await _seed_item(clean_db)
        await order_service.create_order(
            {
                "type": "dine_in",
                "items": [{"menuItemId": "item-1", "quantity": 1}],
            }
        )
        pending = await order_service.list_orders(status="pending")
        confirmed = await order_service.list_orders(status="confirmed")
        assert len(pending) == 1
        assert confirmed == []

    async def test_list_orders_with_user_filter(self, clean_db, order_service: OrderService):
        await _seed_user(clean_db, "u1")
        await _seed_category(clean_db)
        await _seed_item(clean_db)
        await order_service.create_order(
            {
                "userId": "u1",
                "type": "dine_in",
                "items": [{"menuItemId": "item-1", "quantity": 1}],
            }
        )
        assert len(await order_service.list_orders(user_id="u1")) == 1
        assert await order_service.list_orders(user_id="other") == []

    async def test_get_order_returns_none_for_missing(self, clean_db, order_service: OrderService):
        assert await order_service.get_order("nope") is None

    async def test_create_order_minimal(self, clean_db, order_service: OrderService):
        await _seed_category(clean_db)
        await _seed_item(clean_db)
        order = await order_service.create_order(
            {
                "type": "dine_in",
                "items": [{"menuItemId": "item-1", "quantity": 2}],
            }
        )
        assert order["status"] == "pending"
        assert order["orderNumber"].startswith("LE-")
        assert order["subtotal"] == pytest.approx(29.0)
        assert order["tax"] == pytest.approx(2.32)
        assert order["totalAmount"] == pytest.approx(31.32)
        assert len(order["orderItems"]) == 1
        assert order["orderItems"][0]["quantity"] == 2

    async def test_create_order_with_table(self, clean_db, order_service: OrderService):
        await _seed_category(clean_db)
        await _seed_item(clean_db)
        order = await order_service.create_order(
            {
                "type": "dine_in",
                "tableNumber": "5",
                "items": [{"menuItemId": "item-1", "quantity": 1}],
            }
        )
        assert order["tableNumber"] == "5"

    async def test_create_order_accepts_snake_case(self, clean_db, order_service: OrderService):
        await _seed_user(clean_db, "u1")
        await _seed_category(clean_db)
        await _seed_item(clean_db)
        order = await order_service.create_order(
            {
                "user_id": "u1",
                "type": "dine_in",
                "table_number": "9",
                "items": [{"menu_item_id": "item-1", "quantity": 1}],
            }
        )
        assert order["userId"] == "u1"
        assert order["tableNumber"] == "9"

    async def test_create_order_empty_items_raises(self, clean_db, order_service: OrderService):
        with pytest.raises(ValueError, match="at least one item"):
            await order_service.create_order({"type": "dine_in", "items": []})

    async def test_create_order_invalid_type_raises(self, clean_db, order_service: OrderService):
        with pytest.raises(ValueError, match="Valid order type"):
            await order_service.create_order(
                {
                    "type": "flying",
                    "items": [{"menuItemId": "x", "quantity": 1}],
                }
            )

    async def test_create_order_missing_item_id_raises(self, clean_db, order_service: OrderService):
        with pytest.raises(ValueError, match="menuItemId"):
            await order_service.create_order(
                {
                    "type": "dine_in",
                    "items": [{"quantity": 1}],
                }
            )

    async def test_create_order_unavailable_item_raises(self, clean_db, order_service: OrderService):
        with pytest.raises(ValueError, match="unavailable"):
            await order_service.create_order(
                {
                    "type": "dine_in",
                    "items": [{"menuItemId": "missing", "quantity": 1}],
                }
            )

    async def test_update_order_status(self, clean_db, order_service: OrderService):
        await _seed_category(clean_db)
        await _seed_item(clean_db)
        order = await order_service.create_order(
            {
                "type": "dine_in",
                "items": [{"menuItemId": "item-1", "quantity": 1}],
            }
        )
        updated = await order_service.update_order_status(order["id"], "preparing")
        assert updated is not None
        assert updated["status"] == "preparing"

    async def test_update_order_status_invalid_raises(self, clean_db, order_service: OrderService):
        with pytest.raises(ValueError, match="Valid status"):
            await order_service.update_order_status("anything", "flying")

    async def test_update_order_status_missing_returns_none(self, clean_db, order_service: OrderService):
        assert await order_service.update_order_status("nope", "preparing") is None


# ---------------------------------------------------------------------------
# ReservationService
# ---------------------------------------------------------------------------


class TestReservationService:
    BASE = {
        "customerName": "Alice",
        "customerPhone": "555-1234",
        "partySize": 2,
        "date": "2025-12-31",
        "time": "19:00",
    }

    async def test_list_reservations_empty(self, clean_db, reservation_service: ReservationService):
        assert await reservation_service.list_reservations() == []

    async def test_create_reservation_minimal(self, clean_db, reservation_service: ReservationService):
        res = await reservation_service.create_reservation(self.BASE.copy())
        assert res["status"] == "pending"
        assert res["customerName"] == "Alice"

    async def test_create_reservation_with_occasion(self, clean_db, reservation_service: ReservationService):
        res = await reservation_service.create_reservation({**self.BASE, "occasion": "birthday"})
        assert res["occasion"] == "birthday"

    async def test_create_reservation_accepts_snake_case(
        self, clean_db, reservation_service: ReservationService
    ):
        data = {
            "customer_name": "Bob",
            "customer_phone": "555-9999",
            "customer_email": "b@x.com",
            "party_size": 4,
            "date": "2025-12-31",
            "time": "20:00",
        }
        res = await reservation_service.create_reservation(data)
        assert res["customerName"] == "Bob"
        assert res["customerEmail"] == "b@x.com"

    async def test_create_reservation_missing_field_raises(
        self, clean_db, reservation_service: ReservationService
    ):
        bad = {k: v for k, v in self.BASE.items() if k != "customerName"}
        with pytest.raises(ValueError, match="customerName"):
            await reservation_service.create_reservation(bad)

    async def test_create_reservation_invalid_party_size(
        self, clean_db, reservation_service: ReservationService
    ):
        # 0 fails the truthy check (treated as "missing"); 21 fails the range check.
        with pytest.raises(ValueError, match="Missing required field"):
            await reservation_service.create_reservation({**self.BASE, "partySize": 0})
        with pytest.raises(ValueError, match="Party size"):
            await reservation_service.create_reservation({**self.BASE, "partySize": 21})

    async def test_create_reservation_invalid_date(self, clean_db, reservation_service: ReservationService):
        with pytest.raises(ValueError, match="YYYY-MM-DD"):
            await reservation_service.create_reservation({**self.BASE, "date": "12/31/2025"})

    async def test_create_reservation_invalid_time(self, clean_db, reservation_service: ReservationService):
        with pytest.raises(ValueError, match="HH:MM"):
            await reservation_service.create_reservation({**self.BASE, "time": "7pm"})

    async def test_create_reservation_invalid_occasion(
        self, clean_db, reservation_service: ReservationService
    ):
        with pytest.raises(ValueError, match="Invalid occasion"):
            await reservation_service.create_reservation({**self.BASE, "occasion": "divorce"})

    async def test_update_reservation_status(self, clean_db, reservation_service: ReservationService):
        res = await reservation_service.create_reservation(self.BASE.copy())
        updated = await reservation_service.update_reservation_status(res["id"], "confirmed")
        assert updated["status"] == "confirmed"

    async def test_update_reservation_status_invalid_raises(
        self, clean_db, reservation_service: ReservationService
    ):
        with pytest.raises(ValueError, match="Valid status"):
            await reservation_service.update_reservation_status("x", "weird")

    async def test_update_reservation_status_missing_returns_none(
        self, clean_db, reservation_service: ReservationService
    ):
        assert await reservation_service.update_reservation_status("nope", "confirmed") is None

    async def test_list_reservations_filter(self, clean_db, reservation_service: ReservationService):
        await reservation_service.create_reservation(self.BASE.copy())
        assert len(await reservation_service.list_reservations(date="2025-12-31")) == 1
        assert await reservation_service.list_reservations(date="2024-01-01") == []
        assert await reservation_service.list_reservations(status="pending") != []
        assert await reservation_service.list_reservations(status="cancelled") == []


# ---------------------------------------------------------------------------
# AdminService
# ---------------------------------------------------------------------------


class TestAdminService:
    async def test_get_stats_empty(self, clean_db, admin_service: AdminService):
        stats = await admin_service.get_stats()
        assert stats["totalOrders"] == 0
        assert stats["totalReservations"] == 0
        assert stats["totalCustomers"] == 0
        assert stats["totalRevenue"] == 0
        assert stats["ordersByStatus"] == {}
        assert stats["recentOrders"] == []
        assert stats["popularItems"] == []
        assert len(stats["revenueChartData"]) == 7

    async def test_get_stats_with_data(self, clean_db, admin_service: AdminService):
        await clean_db.execute(
            "INSERT INTO users (id, name, email, role) VALUES ('u1', 'Alice', 'a@x.com', 'customer')"
        )
        await _seed_category(clean_db)
        await _seed_item(clean_db)
        await clean_db.execute(
            """INSERT INTO orders (id, user_id, order_number, status, total_amount, subtotal, tax, type)
               VALUES ('o1', 'u1', 'LE-X', 'delivered', 100, 92, 8, 'dine_in')"""
        )
        await clean_db.execute(
            """INSERT INTO order_items (id, order_id, menu_item_id, quantity, unit_price, total_price)
               VALUES ('oi1', 'o1', 'item-1', 2, 50, 100)"""
        )

        stats = await admin_service.get_stats()
        assert stats["totalOrders"] == 1
        assert stats["totalRevenue"] == 100
        assert stats["totalCustomers"] == 1
        assert stats["ordersByStatus"] == {"delivered": 1}
        assert len(stats["recentOrders"]) == 1
        assert stats["recentOrders"][0]["id"] == "o1"
        assert stats["popularItems"][0]["id"] == "item-1"
        assert stats["popularItems"][0]["totalOrdered"] == 2

    async def test_get_stats_cancelled_excluded_from_revenue(self, clean_db, admin_service: AdminService):
        await clean_db.execute(
            """INSERT INTO orders (id, order_number, status, total_amount, subtotal, tax, type)
               VALUES ('o1', 'LE-X', 'cancelled', 100, 92, 8, 'dine_in')"""
        )
        stats = await admin_service.get_stats()
        assert stats["totalRevenue"] == 0

    async def test_get_ai_insights_empty(self, clean_db, admin_service: AdminService):
        insights = await admin_service.get_ai_insights()
        assert len(insights["agentInteractions"]) == 6
        for entry in insights["agentInteractions"]:
            assert entry["conversations"] == 0
        assert insights["qualityMetrics"]["totalConversations"] == 0
        assert insights["qualityMetrics"]["avgMessagesPerConversation"] == 0
        assert insights["qualityMetrics"]["resolutionRate"] == 92  # default when empty

    async def test_get_ai_insights_categorises_queries(self, clean_db, admin_service: AdminService):
        await clean_db.execute(
            """INSERT INTO conversations (id, agent_type, status)
               VALUES ('c1', 'food_recommender', 'active')"""
        )
        await clean_db.execute(
            """INSERT INTO conversations (id, agent_type, status)
               VALUES ('c2', 'concierge', 'ended')"""
        )
        await clean_db.execute(
            """INSERT INTO agent_messages (id, conversation_id, role, content)
               VALUES ('m1', 'c1', 'user', 'I want a spicy dish recommendation please')"""
        )
        await clean_db.execute(
            """INSERT INTO agent_messages (id, conversation_id, role, content)
               VALUES ('m2', 'c2', 'user', 'How much is the kung pao?')"""
        )
        await clean_db.execute(
            """INSERT INTO agent_messages (id, conversation_id, role, content)
               VALUES ('m3', 'c2', 'assistant', 'It is $14.50')"""
        )
        insights = await admin_service.get_ai_insights()
        stats = {e["agentType"]: e["conversations"] for e in insights["agentInteractions"]}
        assert stats["food_recommender"] == 1
        assert stats["concierge"] == 1
        assert insights["qualityMetrics"]["totalConversations"] == 2
        assert insights["qualityMetrics"]["activeConversations"] == 1
        assert insights["qualityMetrics"]["endedConversations"] == 1
        # "spicy" + "recommend" hit both spicy AND recommendation
        cats = {q["category"]: q["count"] for q in insights["commonQueries"]}
        assert cats["recommendation"] >= 1
        assert cats["spicy"] >= 1
        assert cats["pricing"] >= 1
        assert insights["qualityMetrics"]["resolutionRate"] == 50  # 1 ended / 2 total


# ---------------------------------------------------------------------------
# Service fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
async def menu_service(app) -> MenuService:
    from app.services.menu_service import MenuService

    return await app.container.resolve(MenuService)


@pytest.fixture()
async def order_service(app) -> OrderService:
    from app.services.order_service import OrderService

    return await app.container.resolve(OrderService)


@pytest.fixture()
async def reservation_service(app) -> ReservationService:
    from app.services.reservation_service import ReservationService

    return await app.container.resolve(ReservationService)


@pytest.fixture()
async def admin_service(app) -> AdminService:
    from app.services.admin_service import AdminService

    return await app.container.resolve(AdminService)
