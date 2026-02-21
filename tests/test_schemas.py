import pytest
from pydantic import ValidationError

from src.schemas.paper import (
    RuleSetDraftRequest,
    RuleSetCreate,
    RuleSetUpdate,
    RunCreate,
    PaperStatusUpdate,
)


class TestRuleSetDraftRequest:
    def test_valid(self):
        req = RuleSetDraftRequest(topic_sentence="LLM inference optimization techniques")
        assert req.topic_sentence == "LLM inference optimization techniques"

    def test_too_short(self):
        with pytest.raises(ValidationError):
            RuleSetDraftRequest(topic_sentence="hi")


class TestRuleSetCreate:
    def test_valid(self, sample_ruleset_data):
        rs = RuleSetCreate(**sample_ruleset_data)
        assert rs.name == "LLM Inference"
        assert len(rs.search_queries) == 2

    def test_empty_name_rejected(self):
        with pytest.raises(ValidationError):
            RuleSetCreate(name="", topic_sentence="Some topic here")


class TestRunCreate:
    def test_valid_initialize(self):
        run = RunCreate(run_type="initialize")
        assert run.run_type == "initialize"

    def test_valid_track(self):
        run = RunCreate(run_type="track")
        assert run.run_type == "track"

    def test_invalid_type(self):
        with pytest.raises(ValidationError):
            RunCreate(run_type="invalid")


class TestPaperStatusUpdate:
    def test_valid_statuses(self):
        for status in ["inbox", "archived", "favorited"]:
            update = PaperStatusUpdate(status=status)
            assert update.status == status

    def test_invalid_status(self):
        with pytest.raises(ValidationError):
            PaperStatusUpdate(status="deleted")


class TestRuleSetUpdate:
    def test_partial_update(self):
        update = RuleSetUpdate(name="New Name")
        assert update.name == "New Name"
        assert update.topic_sentence is None

    def test_empty_update(self):
        update = RuleSetUpdate()
        assert update.name is None
