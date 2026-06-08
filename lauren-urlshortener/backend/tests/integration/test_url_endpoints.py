"""Integration tests — each endpoint tested against a real in-memory SQLite DB.

Every test class gets a clean database via the ``clean_db`` fixture so tests
are fully isolated from each other.
"""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


class TestHealth:
    def test_health_returns_ok(self, client):
        resp = client.get("/api/health/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["service"] == "lauren-urlshortener"


# ---------------------------------------------------------------------------
# POST /api/urls/ — create
# ---------------------------------------------------------------------------


class TestCreateUrl:
    @pytest.fixture(autouse=True)
    def _clean(self, clean_db):
        pass

    def test_create_returns_200_with_code(self, client):
        resp = client.post("/api/urls/", json={"url": "https://example.com"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        rec = data["data"]
        assert rec["original_url"] == "https://example.com"
        assert len(rec["code"]) == 7
        assert rec["is_active"] is True
        assert rec["click_count"] == 0

    def test_create_with_custom_code(self, client):
        resp = client.post("/api/urls/", json={"url": "https://example.com/page", "custom_code": "mylink"})
        assert resp.status_code == 200
        assert resp.json()["data"]["code"] == "mylink"

    def test_create_with_title(self, client):
        resp = client.post("/api/urls/", json={"url": "https://example.com", "title": "My Page"})
        assert resp.status_code == 200
        assert resp.json()["data"]["title"] == "My Page"

    def test_create_with_expires_at(self, client):
        resp = client.post(
            "/api/urls/",
            json={"url": "https://example.com", "expires_at": "2099-01-01T00:00:00"},
        )
        assert resp.status_code == 200
        assert "2099" in resp.json()["data"]["expires_at"]

    def test_duplicate_custom_code_returns_409(self, client):
        client.post("/api/urls/", json={"url": "https://a.com", "custom_code": "dup"})
        resp = client.post("/api/urls/", json={"url": "https://b.com", "custom_code": "dup"})
        assert resp.status_code == 409
        assert resp.json()["success"] is False

    def test_missing_url_returns_422(self, client):
        resp = client.post("/api/urls/", json={"title": "no url field"})
        assert resp.status_code == 422

    def test_empty_body_returns_422(self, client):
        resp = client.post("/api/urls/", json={})
        assert resp.status_code == 422

    def test_multiple_creates_get_unique_codes(self, client):
        codes = set()
        for i in range(5):
            resp = client.post("/api/urls/", json={"url": f"https://example.com/{i}"})
            assert resp.status_code == 200
            codes.add(resp.json()["data"]["code"])
        assert len(codes) == 5


# ---------------------------------------------------------------------------
# GET /api/urls/ — list
# ---------------------------------------------------------------------------


class TestListUrls:
    @pytest.fixture(autouse=True)
    def _setup(self, client, clean_db):
        for i in range(5):
            client.post("/api/urls/", json={"url": f"https://example.com/{i}", "title": f"Link {i}"})

    def test_list_returns_all(self, client):
        resp = client.get("/api/urls/")
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["pagination"]["total"] == 5
        assert len(body["data"]) == 5

    def test_list_pagination_limit(self, client):
        resp = client.get("/api/urls/?limit=2&page=1")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["data"]) == 2
        assert body["pagination"]["total_pages"] == 3
        assert body["pagination"]["has_more"] is True

    def test_list_pagination_page2(self, client):
        resp = client.get("/api/urls/?limit=2&page=2")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["data"]) == 2

    def test_list_search_by_title(self, client):
        resp = client.get("/api/urls/?search=Link+2")
        assert resp.status_code == 200
        body = resp.json()
        assert body["pagination"]["total"] == 1
        assert body["data"][0]["title"] == "Link 2"

    def test_list_search_by_url(self, client):
        resp = client.get("/api/urls/?search=example.com%2F3")
        assert resp.status_code == 200
        assert resp.json()["pagination"]["total"] == 1

    def test_list_search_no_results(self, client):
        resp = client.get("/api/urls/?search=zzznomatch")
        assert resp.status_code == 200
        assert resp.json()["pagination"]["total"] == 0
        assert resp.json()["data"] == []

    def test_list_respects_limit_max(self, client):
        resp = client.get("/api/urls/?limit=9999")
        assert resp.status_code == 200
        assert resp.json()["pagination"]["limit"] <= 100


# ---------------------------------------------------------------------------
# GET /api/urls/{code} — fetch single
# ---------------------------------------------------------------------------


class TestGetUrl:
    @pytest.fixture(autouse=True)
    def _setup(self, client, clean_db):
        resp = client.post("/api/urls/", json={"url": "https://target.com", "custom_code": "tgt"})
        self.code = resp.json()["data"]["code"]

    def test_get_by_code_returns_record(self, client):
        resp = client.get(f"/api/urls/{self.code}")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["code"] == self.code
        assert data["original_url"] == "https://target.com"

    def test_get_missing_code_returns_404(self, client):
        resp = client.get("/api/urls/nonexistent")
        assert resp.status_code == 404
        assert resp.json()["success"] is False


# ---------------------------------------------------------------------------
# GET /api/urls/{code}/stats — stats
# ---------------------------------------------------------------------------


class TestGetStats:
    @pytest.fixture(autouse=True)
    def _setup(self, client, clean_db):
        resp = client.post("/api/urls/", json={"url": "https://stats.com", "custom_code": "stat1"})
        self.code = resp.json()["data"]["code"]

    def test_stats_initial_click_count_zero(self, client):
        resp = client.get(f"/api/urls/{self.code}/stats")
        assert resp.status_code == 200
        stats = resp.json()["data"]
        assert stats["click_count"] == 0
        assert stats["last_clicked_at"] is None
        assert stats["recent_clicks"] == []

    def test_stats_after_redirects(self, client):
        client.get(f"/api/r/{self.code}")
        client.get(f"/api/r/{self.code}")
        resp = client.get(f"/api/urls/{self.code}/stats")
        assert resp.status_code == 200
        stats = resp.json()["data"]
        assert stats["click_count"] == 2
        assert stats["last_clicked_at"] is not None
        assert len(stats["recent_clicks"]) == 2

    def test_stats_missing_code_returns_404(self, client):
        resp = client.get("/api/urls/zzzmissing/stats")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# PATCH /api/urls/{code} — update
# ---------------------------------------------------------------------------


class TestUpdateUrl:
    @pytest.fixture(autouse=True)
    def _setup(self, client, clean_db):
        resp = client.post(
            "/api/urls/",
            json={"url": "https://update.com", "custom_code": "upd", "title": "Old Title"},
        )
        self.code = resp.json()["data"]["code"]

    def test_update_title(self, client):
        resp = client.patch(f"/api/urls/{self.code}", json={"title": "New Title"})
        assert resp.status_code == 200
        assert resp.json()["data"]["title"] == "New Title"

    def test_update_expires_at(self, client):
        resp = client.patch(f"/api/urls/{self.code}", json={"expires_at": "2099-12-31T23:59:59"})
        assert resp.status_code == 200
        assert "2099" in resp.json()["data"]["expires_at"]

    def test_update_empty_body_no_change(self, client):
        resp = client.patch(f"/api/urls/{self.code}", json={})
        assert resp.status_code == 200
        assert resp.json()["data"]["title"] == "Old Title"

    def test_update_missing_code_returns_404(self, client):
        resp = client.patch("/api/urls/zzznone", json={"title": "x"})
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /api/urls/{code}
# ---------------------------------------------------------------------------


class TestDeleteUrl:
    @pytest.fixture(autouse=True)
    def _setup(self, client, clean_db):
        resp = client.post("/api/urls/", json={"url": "https://delete.com", "custom_code": "del1"})
        self.code = resp.json()["data"]["code"]

    def test_delete_returns_success(self, client):
        resp = client.delete(f"/api/urls/{self.code}")
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_deleted_url_not_found_on_get(self, client):
        client.delete(f"/api/urls/{self.code}")
        resp = client.get(f"/api/urls/{self.code}")
        assert resp.status_code == 404

    def test_deleted_url_not_in_list(self, client):
        client.delete(f"/api/urls/{self.code}")
        resp = client.get("/api/urls/")
        codes = [r["code"] for r in resp.json()["data"]]
        assert self.code not in codes

    def test_deleted_url_redirect_returns_404(self, client):
        client.delete(f"/api/urls/{self.code}")
        resp = client.get(f"/api/r/{self.code}")
        assert resp.status_code == 404

    def test_delete_missing_code_returns_404(self, client):
        resp = client.delete("/api/urls/zzznone")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/r/{code} — redirect
# ---------------------------------------------------------------------------


class TestRedirect:
    @pytest.fixture(autouse=True)
    def _setup(self, client, clean_db):
        resp = client.post("/api/urls/", json={"url": "https://redirect-target.com", "custom_code": "rdr"})
        self.code = resp.json()["data"]["code"]

    def test_redirect_returns_302(self, client):
        resp = client.get(f"/api/r/{self.code}")
        assert resp.status_code == 302

    def test_redirect_location_header(self, client):
        resp = client.get(f"/api/r/{self.code}")
        assert resp.header("location") == "https://redirect-target.com"

    def test_redirect_increments_click_count(self, client):
        for _ in range(3):
            client.get(f"/api/r/{self.code}")
        stats = client.get(f"/api/urls/{self.code}/stats").json()
        assert stats["data"]["click_count"] == 3

    def test_redirect_missing_code_returns_404(self, client):
        resp = client.get("/api/r/zzzmiss")
        assert resp.status_code == 404

    def test_redirect_expired_url_returns_410(self, client, clean_db):
        resp = client.post(
            "/api/urls/",
            json={"url": "https://gone.com", "custom_code": "exp1", "expires_at": "2000-01-01T00:00:00"},
        )
        assert resp.status_code == 200
        resp = client.get("/api/r/exp1")
        assert resp.status_code == 410


# ---------------------------------------------------------------------------
# OpenAPI schema sanity
# ---------------------------------------------------------------------------


class TestOpenAPI:
    def test_openapi_json_returns_200(self, client):
        resp = client.get("/openapi.json")
        assert resp.status_code == 200

    def test_openapi_has_urls_paths(self, client):
        spec = client.get("/openapi.json").json()
        paths = spec.get("paths", {})
        assert any("/api/urls" in p for p in paths), f"No /api/urls paths: {list(paths)}"

    def test_openapi_has_redirect_path(self, client):
        spec = client.get("/openapi.json").json()
        paths = spec.get("paths", {})
        assert any("/api/r" in p for p in paths)

    def test_openapi_has_create_url_schema(self, client):
        spec = client.get("/openapi.json").json()
        schemas = spec.get("components", {}).get("schemas", {})
        assert "CreateUrlRequest" in schemas, f"CreateUrlRequest missing: {list(schemas)}"

    def test_openapi_create_url_schema_has_url_required(self, client):
        spec = client.get("/openapi.json").json()
        schema = spec["components"]["schemas"]["CreateUrlRequest"]
        assert "url" in schema.get("required", [])

    def test_openapi_no_pydantic_artifacts(self, client):
        import json

        spec_text = json.dumps(client.get("/openapi.json").json())
        assert "pydantic" not in spec_text.lower()
