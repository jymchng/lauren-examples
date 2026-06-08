"""End-to-end tests — full user flows across multiple endpoints.

These tests verify that the entire stack (controller → service → DB) works
together correctly without pydantic.  Each flow starts from a clean DB state.
"""

from __future__ import annotations

import sys

import pytest


# ---------------------------------------------------------------------------
# No-pydantic guard
# ---------------------------------------------------------------------------

# NOTE: no ``from __future__ import annotations`` in this file —
# handler annotations inside the app fixture must be eagerly evaluated
# (same reasoning as the smoke test in lauren-eats).


@pytest.fixture(autouse=True, scope="module")
def _no_pydantic():
    """Evict pydantic from sys.modules for the duration of this test module.

    Proves that the URL shortener works entirely without pydantic installed.
    The session-scoped _preload_lauren in conftest.py has already set
    _PYDANTIC_AVAILABLE=True so Lauren's dataclass extractor is registered
    before we block pydantic here.
    """
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


class TestNoPydanticGuard:
    """Pydantic must be invisible for every test in this module."""

    def test_pydantic_import_fails(self):
        with pytest.raises((ImportError, TypeError)):
            import pydantic  # noqa: F401

            pydantic.BaseModel


# ---------------------------------------------------------------------------
# E2E Flow 1 — Create → Retrieve → Redirect → Stats
# ---------------------------------------------------------------------------


class TestCreateRedirectStatsFlow:
    @pytest.fixture(autouse=True)
    def _clean(self, clean_db):
        pass

    def test_full_create_redirect_stats_flow(self, client):
        # 1. Create
        create_resp = client.post(
            "/api/urls/",
            json={"url": "https://example.com/article", "title": "An Article", "custom_code": "art1"},
        )
        assert create_resp.status_code == 200
        rec = create_resp.json()["data"]
        code = rec["code"]
        assert code == "art1"
        assert rec["click_count"] == 0

        # 2. Retrieve — no clicks yet
        get_resp = client.get(f"/api/urls/{code}")
        assert get_resp.status_code == 200
        assert get_resp.json()["data"]["original_url"] == "https://example.com/article"

        # 3. Redirect three times
        for _ in range(3):
            r = client.get(f"/api/r/{code}")
            assert r.status_code == 302
            assert r.header("location") == "https://example.com/article"

        # 4. Stats reflect clicks
        stats_resp = client.get(f"/api/urls/{code}/stats")
        assert stats_resp.status_code == 200
        stats = stats_resp.json()["data"]
        assert stats["click_count"] == 3
        assert stats["last_clicked_at"] is not None
        assert len(stats["recent_clicks"]) == 3

        # 5. Verify list also shows updated count
        list_resp = client.get("/api/urls/")
        entry = next(r for r in list_resp.json()["data"] if r["code"] == code)
        assert entry["click_count"] == 3


# ---------------------------------------------------------------------------
# E2E Flow 2 — Create → Update → Verify
# ---------------------------------------------------------------------------


class TestUpdateFlow:
    @pytest.fixture(autouse=True)
    def _clean(self, clean_db):
        pass

    def test_create_then_update_title_and_expiry(self, client):
        resp = client.post("/api/urls/", json={"url": "https://update.com", "custom_code": "upd2"})
        assert resp.status_code == 200
        code = resp.json()["data"]["code"]

        patch_resp = client.patch(
            f"/api/urls/{code}",
            json={"title": "Updated Title", "expires_at": "2099-06-01T00:00:00"},
        )
        assert patch_resp.status_code == 200
        updated = patch_resp.json()["data"]
        assert updated["title"] == "Updated Title"
        assert "2099" in updated["expires_at"]

        # Verify GET reflects update
        get_resp = client.get(f"/api/urls/{code}")
        assert get_resp.json()["data"]["title"] == "Updated Title"


# ---------------------------------------------------------------------------
# E2E Flow 3 — Create → Delete → Confirm Gone
# ---------------------------------------------------------------------------


class TestDeleteFlow:
    @pytest.fixture(autouse=True)
    def _clean(self, clean_db):
        pass

    def test_create_then_delete_then_404(self, client):
        resp = client.post("/api/urls/", json={"url": "https://gone.com", "custom_code": "gone1"})
        code = resp.json()["data"]["code"]

        del_resp = client.delete(f"/api/urls/{code}")
        assert del_resp.status_code == 200
        assert del_resp.json()["success"] is True

        assert client.get(f"/api/urls/{code}").status_code == 404
        assert client.get(f"/api/r/{code}").status_code == 404

        # Confirm not in list
        codes = [r["code"] for r in client.get("/api/urls/").json()["data"]]
        assert code not in codes


# ---------------------------------------------------------------------------
# E2E Flow 4 — Expiry enforcement
# ---------------------------------------------------------------------------


class TestExpiryFlow:
    @pytest.fixture(autouse=True)
    def _clean(self, clean_db):
        pass

    def test_expired_url_returns_410_on_redirect(self, client):
        resp = client.post(
            "/api/urls/",
            json={"url": "https://old.com", "custom_code": "old1", "expires_at": "2000-01-01T00:00:00"},
        )
        assert resp.status_code == 200
        assert client.get("/api/r/old1").status_code == 410

    def test_future_expiry_url_redirects_normally(self, client):
        resp = client.post(
            "/api/urls/",
            json={"url": "https://future.com", "custom_code": "fut1", "expires_at": "2099-01-01T00:00:00"},
        )
        assert resp.status_code == 200
        r = client.get("/api/r/fut1")
        assert r.status_code == 302
        assert r.header("location") == "https://future.com"


# ---------------------------------------------------------------------------
# E2E Flow 5 — Duplicate custom codes
# ---------------------------------------------------------------------------


class TestCustomCodeFlow:
    @pytest.fixture(autouse=True)
    def _clean(self, clean_db):
        pass

    def test_custom_code_collision_returns_409(self, client):
        client.post("/api/urls/", json={"url": "https://first.com", "custom_code": "clash"})
        resp = client.post("/api/urls/", json={"url": "https://second.com", "custom_code": "clash"})
        assert resp.status_code == 409

    def test_different_custom_codes_both_work(self, client):
        r1 = client.post("/api/urls/", json={"url": "https://one.com", "custom_code": "one"})
        r2 = client.post("/api/urls/", json={"url": "https://two.com", "custom_code": "two"})
        assert r1.status_code == 200
        assert r2.status_code == 200

        assert client.get("/api/r/one").header("location") == "https://one.com"
        assert client.get("/api/r/two").header("location") == "https://two.com"


# ---------------------------------------------------------------------------
# E2E Flow 6 — Pagination and search
# ---------------------------------------------------------------------------


class TestPaginationSearchFlow:
    @pytest.fixture(autouse=True)
    def _setup(self, client, clean_db):
        for i in range(10):
            client.post("/api/urls/", json={"url": f"https://example.com/page{i}", "title": f"Page {i}"})
        # One with a distinct keyword
        client.post("/api/urls/", json={"url": "https://special.io/unique", "title": "Special Link"})

    def test_first_page_has_correct_count(self, client):
        resp = client.get("/api/urls/?limit=5&page=1")
        assert resp.status_code == 200
        assert len(resp.json()["data"]) == 5

    def test_second_page_has_remaining(self, client):
        resp = client.get("/api/urls/?limit=5&page=2")
        assert resp.status_code == 200
        assert len(resp.json()["data"]) == 5

    def test_third_page_has_one(self, client):
        resp = client.get("/api/urls/?limit=5&page=3")
        assert resp.status_code == 200
        assert len(resp.json()["data"]) == 1

    def test_search_finds_special_link(self, client):
        resp = client.get("/api/urls/?search=Special")
        assert resp.status_code == 200
        body = resp.json()
        assert body["pagination"]["total"] == 1
        assert body["data"][0]["title"] == "Special Link"

    def test_search_by_domain(self, client):
        resp = client.get("/api/urls/?search=special.io")
        assert resp.status_code == 200
        assert resp.json()["pagination"]["total"] == 1


# ---------------------------------------------------------------------------
# E2E Flow 7 — Bulk operations don't cross-contaminate
# ---------------------------------------------------------------------------


class TestIsolationFlow:
    @pytest.fixture(autouse=True)
    def _clean(self, clean_db):
        pass

    def test_redirecting_one_url_does_not_affect_another(self, client):
        r1 = client.post("/api/urls/", json={"url": "https://a.com", "custom_code": "aa1"})
        r2 = client.post("/api/urls/", json={"url": "https://b.com", "custom_code": "bb1"})
        assert r1.status_code == r2.status_code == 200

        for _ in range(5):
            client.get("/api/r/aa1")

        s1 = client.get("/api/urls/aa1/stats").json()["data"]["click_count"]
        s2 = client.get("/api/urls/bb1/stats").json()["data"]["click_count"]
        assert s1 == 5
        assert s2 == 0

    def test_deleting_one_url_leaves_other_intact(self, client):
        client.post("/api/urls/", json={"url": "https://keep.com", "custom_code": "keep1"})
        client.post("/api/urls/", json={"url": "https://drop.com", "custom_code": "drop1"})

        client.delete("/api/urls/drop1")

        assert client.get("/api/urls/keep1").status_code == 200
        assert client.get("/api/urls/drop1").status_code == 404
