"""
AuditLens — API Tests
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import pytest
from fastapi.testclient import TestClient
from main import app, Base, engine, SessionLocal

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_db():
    """Reset DB before each test."""
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


class TestRoot:
    def test_root(self):
        r = client.get("/")
        assert r.status_code == 200
        assert r.json()["app"] == "AuditLens"


class TestCreateAudit:
    def test_create_audit(self):
        r = client.post("/api/audits", json={"url": "https://example.com"})
        assert r.status_code == 200
        data = r.json()
        assert data["url"] == "https://example.com"
        assert data["status"] == "completed"
        assert 0 <= data["overall_score"] <= 100
        assert data["id"] > 0

    def test_create_multiple(self):
        urls = ["https://a.com", "https://b.com", "https://c.com"]
        for url in urls:
            r = client.post("/api/audits", json={"url": url})
            assert r.status_code == 200
        r = client.get("/api/audits")
        assert len(r.json()) == 3

    def test_different_urls_different_scores(self):
        r1 = client.post("/api/audits", json={"url": "https://site-a.com"})
        r2 = client.post("/api/audits", json={"url": "https://site-b.com"})
        assert r1.json()["overall_score"] != r2.json()["overall_score"]


class TestGetAudit:
    def test_get_audit_detail(self):
        created = client.post("/api/audits", json={"url": "https://example.com"}).json()
        r = client.get(f"/api/audits/{created['id']}")
        assert r.status_code == 200
        data = r.json()
        assert data["url"] == "https://example.com"
        assert len(data["category_scores"]) == 5
        assert len(data["issues"]) > 0
        assert "accessibility" in [c["category"] for c in data["category_scores"]]

    def test_get_nonexistent(self):
        r = client.get("/api/audits/9999")
        assert r.status_code == 404

    def test_issues_have_required_fields(self):
        created = client.post("/api/audits", json={"url": "https://example.com"}).json()
        data = client.get(f"/api/audits/{created['id']}").json()
        for issue in data["issues"]:
            assert "severity" in issue
            assert "category" in issue
            assert "title" in issue
            assert "description" in issue
            assert "suggestion" in issue
            assert issue["severity"] in ["critical", "warning", "info", "success"]


class TestListAudits:
    def test_list_empty(self):
        r = client.get("/api/audits")
        assert r.status_code == 200
        assert r.json() == []

    def test_list_ordered_by_date(self):
        client.post("/api/audits", json={"url": "https://first.com"})
        client.post("/api/audits", json={"url": "https://second.com"})
        r = client.get("/api/audits")
        data = r.json()
        assert len(data) == 2
        assert data[0]["url"] == "https://second.com"  # newest first


class TestDeleteAudit:
    def test_delete_audit(self):
        created = client.post("/api/audits", json={"url": "https://example.com"}).json()
        r = client.delete(f"/api/audits/{created['id']}")
        assert r.status_code == 200
        assert r.json()["ok"] is True
        r2 = client.get(f"/api/audits/{created['id']}")
        assert r2.status_code == 404

    def test_delete_nonexistent(self):
        r = client.delete("/api/audits/9999")
        assert r.status_code == 404


class TestAuditEngine:
    def test_score_range(self):
        for url in [f"https://site-{i}.com" for i in range(10)]:
            r = client.post("/api/audits", json={"url": url})
            score = r.json()["overall_score"]
            assert 0 <= score <= 100, f"Score {score} out of range for {url}"

    def test_all_categories_present(self):
        created = client.post("/api/audits", json={"url": "https://example.com"}).json()
        data = client.get(f"/api/audits/{created['id']}").json()
        cats = {c["category"] for c in data["category_scores"]}
        expected = {"accessibility", "performance", "seo", "best_practices", "mobile"}
        assert cats == expected
