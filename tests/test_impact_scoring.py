from src.services.impact_scoring import compute_impact_score


class TestComputeImpactScore:
    def test_high_citation_paper(self):
        paper = {
            "citationCount": 500,
            "influentialCitationCount": 30,
            "year": 2020,
            "publicationTypes": ["JournalArticle"],
            "publicationVenue": {"name": "NeurIPS"},
        }
        score = compute_impact_score(paper)
        assert 0.0 <= score <= 1.0
        assert score > 0.5

    def test_zero_citations_recent(self):
        paper = {
            "citationCount": 0,
            "influentialCitationCount": 0,
            "year": 2025,
            "publicationTypes": None,
            "publicationVenue": None,
        }
        score = compute_impact_score(paper)
        assert score > 0.0  # recency bonus for recent papers

    def test_zero_citations_old(self):
        paper = {
            "citationCount": 0,
            "influentialCitationCount": 0,
            "year": 2018,
            "publicationTypes": None,
            "publicationVenue": None,
        }
        score = compute_impact_score(paper)
        assert score == 0.0  # no recency bonus for old papers

    def test_survey_bonus(self):
        base = {
            "citationCount": 10,
            "influentialCitationCount": 2,
            "year": 2024,
            "publicationVenue": None,
        }
        paper_no_survey = {**base, "publicationTypes": ["JournalArticle"]}
        paper_survey = {**base, "publicationTypes": ["Review"]}

        score_no = compute_impact_score(paper_no_survey)
        score_yes = compute_impact_score(paper_survey)
        assert score_yes > score_no

    def test_missing_fields(self):
        score = compute_impact_score({})
        assert score >= 0.0
        assert score <= 0.2

    def test_none_values(self):
        paper = {
            "citationCount": None,
            "influentialCitationCount": None,
            "year": None,
        }
        score = compute_impact_score(paper)
        assert score >= 0.0
        assert score <= 0.2
