"""Unit tests for shared Pydantic models in ``app.models.common``."""

from __future__ import annotations

from app.models.common import ApiResponse, PaginatedResponse, Pagination


class TestApiResponse:
    def test_defaults(self):
        r = ApiResponse()
        assert r.success is True
        assert r.data is None
        assert r.error is None
        assert r.message is None

    def test_with_data(self):
        r = ApiResponse(data={"id": 1})
        assert r.success is True
        assert r.data == {"id": 1}

    def test_error_response(self):
        r = ApiResponse(success=False, error="boom")
        assert r.success is False
        assert r.error == "boom"


class TestPagination:
    def test_defaults(self):
        p = Pagination()
        assert p.page == 1
        assert p.limit == 12
        assert p.total == 0
        assert p.total_pages == 0
        assert p.has_more is False

    def test_alias_population(self):
        p = Pagination.model_validate(
            {"page": 2, "limit": 20, "total": 100, "totalPages": 5, "hasMore": True}
        )
        assert p.page == 2
        assert p.limit == 20
        assert p.total == 100
        assert p.total_pages == 5
        assert p.has_more is True

    def test_dump_by_alias(self):
        p = Pagination(page=2, limit=20, total=100, total_pages=5, has_more=True)
        d = p.model_dump(by_alias=True)
        assert d["totalPages"] == 5
        assert d["hasMore"] is True


class TestPaginatedResponse:
    def test_module_exports(self):
        # Pydantic v2 generic models can't be instantiated bare, but we can
        # verify the class is exported and has the expected fields.
        from app.models import common
        assert hasattr(common, "PaginatedResponse")
        assert hasattr(common, "Pagination")
        assert hasattr(common, "ApiResponse")
        assert "data" in PaginatedResponse.model_fields
        assert "pagination" in PaginatedResponse.model_fields
