"""
impact_score计算 - 基于S2元数据的免费信号排序
"""
from datetime import datetime
from typing import Any, Dict

TOP_VENUES = {
    "neurips", "icml", "iclr", "acl", "emnlp", "cvpr", "iccv", "eccv",
    "aaai", "ijcai", "naacl", "sigir", "kdd", "www",
    "nature", "science", "cell",
    "jmlr", "tacl", "tmlr",
}

SURVEY_TITLE_KEYWORDS = {"survey", "review", "tutorial", "benchmark", "overview"}


def is_survey_paper(paper: Dict[str, Any]) -> bool:
    title = (paper.get("title") or "").lower()
    pub_types = paper.get("publicationTypes") or []
    return any(kw in title for kw in SURVEY_TITLE_KEYWORDS) or "Review" in pub_types


def compute_impact_score(paper: Dict[str, Any]) -> float:
    current_year = datetime.now().year
    year = paper.get("year") or current_year
    age = max(1, current_year - year + 1)

    citation_count = paper.get("citationCount", 0) or 0
    influential = paper.get("influentialCitationCount", 0) or 0
    cpy = citation_count / age

    venue = (paper.get("venue") or "").lower()
    pub_venue = paper.get("publicationVenue") or {}
    venue_name = (pub_venue.get("name") or "").lower() if isinstance(pub_venue, dict) else ""
    combined_venue = f"{venue} {venue_name}"
    has_top_venue = any(v in combined_venue for v in TOP_VENUES)

    recency_bonus = max(0, 0.15 - (age - 1) * 0.05) if age <= 3 else 0

    score = (
        min(cpy / 50, 1.0) * 0.35
        + min(influential / 20, 1.0) * 0.25
        + recency_bonus
        + (0.05 if is_survey_paper(paper) else 0)
        + (0.20 if has_top_venue else 0)
    )

    return round(score, 4)
