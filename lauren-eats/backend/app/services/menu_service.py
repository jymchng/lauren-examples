"""Menu service — CRUD operations for menu items and categories."""

from __future__ import annotations

import uuid
from lauren import injectable, Scope
from app.db.database import DatabaseService


def _new_id() -> str:
    return uuid.uuid4().hex[:25]


def _row_to_menu_item(row: dict) -> dict:
    """Convert a DB row to a camelCase JSON dict matching the Next.js API format."""
    return {
        "id": row.get("id", ""),
        "name": row.get("name", ""),
        "nameZh": row.get("name_zh"),
        "description": row.get("description", ""),
        "price": row.get("price", 0),
        "image": row.get("image"),
        "categoryId": row.get("category_id", ""),
        "spicyLevel": row.get("spicy_level", 0),
        "isVegetarian": bool(row.get("is_vegetarian", 0)),
        "isVegan": bool(row.get("is_vegan", 0)),
        "isGlutenFree": bool(row.get("is_gluten_free", 0)),
        "isPopular": bool(row.get("is_popular", 0)),
        "isAvailable": bool(row.get("is_available", 1)),
        "calories": row.get("calories"),
        "preparationTime": row.get("preparation_time"),
        "ingredients": row.get("ingredients"),
        "allergens": row.get("allergens"),
        "tags": row.get("tags"),
        "createdAt": row.get("created_at", ""),
        "updatedAt": row.get("updated_at", ""),
    }


def _row_to_category(row: dict) -> dict:
    return {
        "id": row.get("id", ""),
        "name": row.get("name", ""),
        "nameZh": row.get("name_zh"),
        "slug": row.get("slug", ""),
        "description": row.get("description"),
        "icon": row.get("icon"),
        "sortOrder": row.get("sort_order", 0),
        "isActive": bool(row.get("is_active", 1)),
        "createdAt": row.get("created_at", ""),
        "updatedAt": row.get("updated_at", ""),
    }


@injectable(scope=Scope.SINGLETON)
class MenuService:
    def __init__(self, db: DatabaseService) -> None:
        self._db = db

    async def list_menu_items(
        self,
        page: int = 1,
        limit: int = 12,
        category: str = "all",
        search: str | None = None,
        is_vegetarian: bool | None = None,
        is_vegan: bool | None = None,
        is_gluten_free: bool | None = None,
        spicy_level: int | None = None,
        is_popular: bool | None = None,
    ) -> dict:
        conditions = ["mi.is_available = 1"]
        params: list = []

        if category and category != "all":
            conditions.append("c.slug = ?")
            params.append(category)

        if search:
            conditions.append("(mi.name LIKE ? OR mi.name_zh LIKE ? OR mi.description LIKE ?)")
            params.extend([f"%{search}%"] * 3)

        if is_vegetarian:
            conditions.append("mi.is_vegetarian = 1")
        if is_vegan:
            conditions.append("mi.is_vegan = 1")
        if is_gluten_free:
            conditions.append("mi.is_gluten_free = 1")
        if spicy_level is not None:
            conditions.append("mi.spicy_level <= ?")
            params.append(spicy_level)
        if is_popular:
            conditions.append("mi.is_popular = 1")

        where = " AND ".join(conditions)

        # Count
        count_sql = f"SELECT COUNT(*) as cnt FROM menu_items mi LEFT JOIN categories c ON mi.category_id = c.id WHERE {where}"
        total = await self._db.fetch_count(count_sql, tuple(params))

        # Fetch
        offset = (page - 1) * limit
        data_sql = f"""
            SELECT mi.*, c.name as cat_name, c.name_zh as cat_name_zh, c.slug as cat_slug,
                   c.description as cat_desc, c.icon as cat_icon, c.sort_order as cat_sort,
                   c.is_active as cat_active, c.created_at as cat_created, c.updated_at as cat_updated
            FROM menu_items mi
            LEFT JOIN categories c ON mi.category_id = c.id
            WHERE {where}
            ORDER BY mi.is_popular DESC, mi.name ASC
            LIMIT ? OFFSET ?
        """
        rows = await self._db.fetch_all(data_sql, tuple(params + [limit, offset]))

        items = []
        for row in rows:
            item = _row_to_menu_item(row)
            item["category"] = {
                "id": row.get("category_id", ""),
                "name": row.get("cat_name", ""),
                "nameZh": row.get("cat_name_zh"),
                "slug": row.get("cat_slug", ""),
                "description": row.get("cat_desc"),
                "icon": row.get("cat_icon"),
                "sortOrder": row.get("cat_sort", 0),
                "isActive": bool(row.get("cat_active", 1)),
                "createdAt": row.get("cat_created", ""),
                "updatedAt": row.get("cat_updated", ""),
            }
            items.append(item)

        total_pages = (total + limit - 1) // limit if limit > 0 else 0
        return {
            "data": items,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "totalPages": total_pages,
                "hasMore": page < total_pages,
            },
        }

    async def get_menu_item(self, item_id: str) -> dict | None:
        sql = """
            SELECT mi.*, c.name as cat_name, c.name_zh as cat_name_zh, c.slug as cat_slug,
                   c.description as cat_desc, c.icon as cat_icon, c.sort_order as cat_sort,
                   c.is_active as cat_active, c.created_at as cat_created, c.updated_at as cat_updated
            FROM menu_items mi
            LEFT JOIN categories c ON mi.category_id = c.id
            WHERE mi.id = ?
        """
        row = await self._db.fetch_one(sql, (item_id,))
        if row is None:
            return None
        item = _row_to_menu_item(row)
        item["category"] = {
            "id": row.get("category_id", ""),
            "name": row.get("cat_name", ""),
            "nameZh": row.get("cat_name_zh"),
            "slug": row.get("cat_slug", ""),
            "description": row.get("cat_desc"),
            "icon": row.get("cat_icon"),
            "sortOrder": row.get("cat_sort", 0),
            "isActive": bool(row.get("cat_active", 1)),
            "createdAt": row.get("cat_created", ""),
            "updatedAt": row.get("cat_updated", ""),
        }
        return item

    async def update_menu_item(self, item_id: str, data: dict) -> dict | None:
        existing = await self.get_menu_item(item_id)
        if existing is None:
            return None

        sets: list[str] = []
        params: list = []
        field_map = {
            "is_available": "isAvailable",
            "is_popular": "isPopular",
            "price": "price",
            "name": "name",
            "description": "description",
        }
        for db_field, json_field in field_map.items():
            if json_field in data and data[json_field] is not None:
                val = data[json_field]
                if db_field.startswith("is_"):
                    val = 1 if val else 0
                sets.append(f"{db_field} = ?")
                params.append(val)

        if not sets:
            return existing

        sets.append("updated_at = CURRENT_TIMESTAMP")
        params.append(item_id)
        sql = f"UPDATE menu_items SET {', '.join(sets)} WHERE id = ?"
        await self._db.execute(sql, tuple(params))
        return await self.get_menu_item(item_id)

    async def list_categories(self) -> list[dict]:
        sql = """
            SELECT c.* FROM categories c
            WHERE c.is_active = 1
            ORDER BY c.sort_order ASC
        """
        rows = await self._db.fetch_all(sql)
        categories = [_row_to_category(row) for row in rows]

        # Attach menu items to each category
        for cat in categories:
            items_sql = """
                SELECT * FROM menu_items
                WHERE category_id = ? AND is_available = 1
                ORDER BY name ASC
            """
            item_rows = await self._db.fetch_all(items_sql, (cat["id"],))
            cat["menuItems"] = [_row_to_menu_item(r) for r in item_rows]

        return categories
