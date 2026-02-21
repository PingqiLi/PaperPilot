import pytest
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.models.paper import Base, Paper, TokenUsage
from src.models.ruleset import RuleSet, Run, PaperRuleSet


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


class TestPaperModel:
    def test_create_paper(self, db):
        paper = Paper(
            arxiv_id="2412.12345",
            title="Test Paper",
            authors=["Author A"],
            categories=["cs.AI"],
            citation_count=10,
            impact_score=0.5,
        )
        db.add(paper)
        db.commit()

        result = db.query(Paper).first()
        assert result.arxiv_id == "2412.12345"
        assert result.title == "Test Paper"
        assert result.authors == ["Author A"]
        assert result.citation_count == 10

    def test_paper_unique_arxiv_id(self, db):
        db.add(Paper(arxiv_id="2412.11111", title="Paper 1"))
        db.commit()

        db.add(Paper(arxiv_id="2412.11111", title="Paper 2"))
        with pytest.raises(Exception):
            db.commit()


class TestRuleSetModel:
    def test_create_ruleset(self, db):
        rs = RuleSet(
            name="Test Topic",
            topic_sentence="LLM inference optimization",
            categories=["cs.AI"],
            keywords_include=["quantization"],
            search_queries=["LLM inference"],
        )
        db.add(rs)
        db.commit()

        result = db.query(RuleSet).first()
        assert result.name == "Test Topic"
        assert result.is_active is True
        assert result.is_initialized is False

    def test_ruleset_run_relationship(self, db):
        rs = RuleSet(name="Test", topic_sentence="test topic")
        db.add(rs)
        db.commit()

        run = Run(ruleset_id=rs.id, run_type="initialize")
        db.add(run)
        db.commit()

        assert len(db.query(Run).filter(Run.ruleset_id == rs.id).all()) == 1
        assert run.status == "pending"


class TestPaperRuleSetModel:
    def test_paper_ruleset_association(self, db):
        paper = Paper(arxiv_id="2412.99999", title="Assoc Test")
        rs = RuleSet(name="Assoc RS", topic_sentence="test")
        db.add_all([paper, rs])
        db.commit()

        assoc = PaperRuleSet(
            paper_id=paper.id,
            ruleset_id=rs.id,
            status="inbox",
            source="initialize",
            llm_score=8.5,
            llm_reason="Highly relevant",
        )
        db.add(assoc)
        db.commit()

        result = db.query(PaperRuleSet).first()
        assert result.status == "inbox"
        assert result.source == "initialize"
        assert result.llm_score == 8.5


class TestTokenUsageModel:
    def test_create_token_usage(self, db):
        usage = TokenUsage(
            model="qwen3.5-plus",
            workflow="batch_scoring",
            input_tokens=1000,
            output_tokens=200,
            cost_yuan=0.003,
        )
        db.add(usage)
        db.commit()

        result = db.query(TokenUsage).first()
        assert result.model == "qwen3.5-plus"
        assert result.cost_yuan == 0.003
