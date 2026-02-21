import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.database import init_db, engine
from src.models.paper import Base


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    return TestClient(app)


class TestHealthRouter:
    def test_health_check(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_root_endpoint(self, client):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Paper Agent"
        assert data["version"] == "1.0.0"


class TestRulesRouter:
    def test_get_categories(self, client):
        response = client.get("/api/v1/rules/categories")
        assert response.status_code == 200
        data = response.json()
        assert "cs" in data
        assert "cs.AI" in data["cs"]
        assert "cs.LG" in data["cs"]


class TestRulesetsRouter:
    def test_list_rulesets_empty(self, client):
        response = client.get("/api/v1/rulesets")
        assert response.status_code == 200
        assert response.json() == []

    def test_create_ruleset(self, client, sample_ruleset_data):
        response = client.post("/api/v1/rulesets", json=sample_ruleset_data)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "LLM Inference"
        assert data["is_active"] is True
        assert data["is_initialized"] is False
        assert data["id"] > 0

    def test_get_ruleset(self, client, sample_ruleset_data):
        create_resp = client.post("/api/v1/rulesets", json=sample_ruleset_data)
        rs_id = create_resp.json()["id"]

        response = client.get(f"/api/v1/rulesets/{rs_id}")
        assert response.status_code == 200
        assert response.json()["name"] == "LLM Inference"

    def test_get_ruleset_not_found(self, client):
        response = client.get("/api/v1/rulesets/9999")
        assert response.status_code == 404

    def test_update_ruleset(self, client, sample_ruleset_data):
        create_resp = client.post("/api/v1/rulesets", json=sample_ruleset_data)
        rs_id = create_resp.json()["id"]

        response = client.put(f"/api/v1/rulesets/{rs_id}", json={"name": "Updated Name"})
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Name"

    def test_delete_ruleset(self, client, sample_ruleset_data):
        create_resp = client.post("/api/v1/rulesets", json=sample_ruleset_data)
        rs_id = create_resp.json()["id"]

        response = client.delete(f"/api/v1/rulesets/{rs_id}")
        assert response.status_code == 200

        list_resp = client.get("/api/v1/rulesets")
        assert len(list_resp.json()) == 0

    def test_duplicate_name_rejected(self, client, sample_ruleset_data):
        client.post("/api/v1/rulesets", json=sample_ruleset_data)
        response = client.post("/api/v1/rulesets", json=sample_ruleset_data)
        assert response.status_code == 400

    def test_create_run_no_active_run(self, client, sample_ruleset_data):
        create_resp = client.post("/api/v1/rulesets", json=sample_ruleset_data)
        rs_id = create_resp.json()["id"]

        response = client.post(f"/api/v1/rulesets/{rs_id}/runs", json={"run_type": "initialize"})
        assert response.status_code == 200
        data = response.json()
        assert data["run_type"] == "initialize"
        assert data["status"] == "pending"

    def test_list_runs(self, client, sample_ruleset_data):
        create_resp = client.post("/api/v1/rulesets", json=sample_ruleset_data)
        rs_id = create_resp.json()["id"]

        client.post(f"/api/v1/rulesets/{rs_id}/runs", json={"run_type": "initialize"})

        response = client.get(f"/api/v1/rulesets/{rs_id}/runs")
        assert response.status_code == 200
        assert len(response.json()) == 1

    def test_get_ruleset_papers_empty(self, client, sample_ruleset_data):
        create_resp = client.post("/api/v1/rulesets", json=sample_ruleset_data)
        rs_id = create_resp.json()["id"]

        response = client.get(f"/api/v1/rulesets/{rs_id}/papers")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []

    def test_reinit_preview_empty(self, client, sample_ruleset_data):
        create_resp = client.post("/api/v1/rulesets", json=sample_ruleset_data)
        rs_id = create_resp.json()["id"]

        response = client.get(f"/api/v1/rulesets/{rs_id}/reinit-preview")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["favorited"] == 0
        assert data["will_remove"] == 0

    def test_reinit_preview_not_found(self, client):
        response = client.get("/api/v1/rulesets/9999/reinit-preview")
        assert response.status_code == 404


class TestDigestsRouter:
    def test_list_digests_empty(self, client, sample_ruleset_data):
        create_resp = client.post("/api/v1/rulesets", json=sample_ruleset_data)
        rs_id = create_resp.json()["id"]

        response = client.get(f"/api/v1/rulesets/{rs_id}/digests")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []

    def test_list_digests_not_found(self, client):
        response = client.get("/api/v1/rulesets/99999/digests")
        assert response.status_code == 404

    def test_create_digest_not_found(self, client):
        response = client.post(
            "/api/v1/rulesets/99999/digests",
            json={"digest_type": "field_overview"}
        )
        assert response.status_code == 404

    def test_create_digest_invalid_type(self, client, sample_ruleset_data):
        create_resp = client.post("/api/v1/rulesets", json=sample_ruleset_data)
        rs_id = create_resp.json()["id"]

        response = client.post(
            f"/api/v1/rulesets/{rs_id}/digests",
            json={"digest_type": "invalid"}
        )
        assert response.status_code == 422

    def test_get_digest_not_found(self, client):
        response = client.get("/api/v1/rulesets/1/digests/99999")
        assert response.status_code == 404


class TestReinitCleanup:
    def test_reinit_clears_non_favorited_papers(self, client, sample_ruleset_data):
        create_resp = client.post("/api/v1/rulesets", json=sample_ruleset_data)
        rs_id = create_resp.json()["id"]

        from src.database import SessionLocal
        from src.models import Paper, PaperRuleSet, RuleSet
        db = SessionLocal()
        try:
            paper1 = Paper(arxiv_id="2412.00001", title="Paper A", authors=[], categories=[])
            paper2 = Paper(arxiv_id="2412.00002", title="Paper B", authors=[], categories=[])
            paper3 = Paper(arxiv_id="2412.00003", title="Paper C", authors=[], categories=[])
            db.add_all([paper1, paper2, paper3])
            db.flush()

            db.add(PaperRuleSet(paper_id=paper1.id, ruleset_id=rs_id, status="inbox", llm_score=8))
            db.add(PaperRuleSet(paper_id=paper2.id, ruleset_id=rs_id, status="favorited", llm_score=9))
            db.add(PaperRuleSet(paper_id=paper3.id, ruleset_id=rs_id, status="archived", llm_score=3))

            ruleset = db.query(RuleSet).filter(RuleSet.id == rs_id).first()
            ruleset.is_initialized = True
            db.commit()

            deleted = db.query(PaperRuleSet).filter(
                PaperRuleSet.ruleset_id == rs_id,
                PaperRuleSet.status != "favorited",
            ).delete(synchronize_session="fetch")
            ruleset.is_initialized = False
            db.commit()

            assert deleted == 2

            remaining = db.query(PaperRuleSet).filter(
                PaperRuleSet.ruleset_id == rs_id,
            ).all()
            assert len(remaining) == 1
            assert remaining[0].status == "favorited"
            assert remaining[0].paper_id == paper2.id

            ruleset = db.query(RuleSet).filter(RuleSet.id == rs_id).first()
            assert ruleset.is_initialized is False
        finally:
            db.close()

    def test_reinit_preserves_other_topic_papers(self, client, sample_ruleset_data):
        resp1 = client.post("/api/v1/rulesets", json=sample_ruleset_data)
        rs1_id = resp1.json()["id"]

        other_data = {**sample_ruleset_data, "name": "Other Topic"}
        resp2 = client.post("/api/v1/rulesets", json=other_data)
        rs2_id = resp2.json()["id"]

        from src.database import SessionLocal
        from src.models import Paper, PaperRuleSet
        db = SessionLocal()
        try:
            paper = Paper(arxiv_id="2412.00010", title="Shared Paper", authors=[], categories=[])
            db.add(paper)
            db.flush()

            db.add(PaperRuleSet(paper_id=paper.id, ruleset_id=rs1_id, status="inbox", llm_score=7))
            db.add(PaperRuleSet(paper_id=paper.id, ruleset_id=rs2_id, status="inbox", llm_score=8))
            db.commit()

            deleted = db.query(PaperRuleSet).filter(
                PaperRuleSet.ruleset_id == rs1_id,
                PaperRuleSet.status != "favorited",
            ).delete(synchronize_session="fetch")
            db.commit()

            assert deleted == 1

            other_assocs = db.query(PaperRuleSet).filter(
                PaperRuleSet.ruleset_id == rs2_id,
            ).all()
            assert len(other_assocs) == 1
            assert other_assocs[0].llm_score == 8
        finally:
            db.close()


class TestStatsRouter:
    def test_get_cost_stats(self, client):
        response = client.get("/api/v1/stats/costs")
        assert response.status_code == 200
        data = response.json()
        assert data["currency"] == "CNY"
        assert "today_cost" in data
        assert "total_cost" in data

