"""
核心Pipeline - Initialize（构建基础阅读清单）和Track（追踪新论文）
"""
import asyncio
import re
from collections import Counter
from datetime import datetime, timedelta
from typing import Any, Dict, List, cast

import structlog

from ..database import SessionLocal
from ..models import Paper, PaperRuleSet, RuleSet, Run
from . import app_settings
from .arxiv import ArxivService
from .batch_scorer import score_batch
from .paper_analyzer import analyze_paper
from .impact_scoring import compute_impact_score, is_survey_paper
from .semantic_scholar import SemanticScholarService

logger = structlog.get_logger(__name__)

S2_SEARCH_FIELDS = (
    "paperId,externalIds,title,abstract,authors,year,"
    "citationCount,influentialCitationCount,venue,publicationVenue,"
    "publicationTypes,publicationDate"
)


def _get_sources(setting_key: str) -> set[str]:
    raw = app_settings.get(setting_key)
    return {s.strip().lower() for s in raw.split(",") if s.strip()}


async def _s2_search_stream(
    s2: SemanticScholarService,
    queries: list[str],
    run_id: int,
    year_start: int | None = None,
    cutoff: datetime | None = None,
) -> Dict[str, Dict[str, Any]]:
    all_papers: Dict[str, Dict[str, Any]] = {}
    _update_run_progress(run_id, "searching", 0, len(queries))

    for i, query in enumerate(queries):
        papers = await s2.search_papers(
            query=query,
            limit=100,
            year_start=year_start,
            fields=S2_SEARCH_FIELDS,
        )
        for p in papers:
            pid = p.get("paperId")
            if pid and pid not in all_papers:
                if cutoff:
                    pub_date = _parse_pub_date(p)
                    if pub_date and pub_date < cutoff:
                        continue
                all_papers[pid] = p
        _update_run_progress(run_id, "searching", i + 1, len(queries))

    return all_papers


async def _arxiv_search_stream(
    categories: List[str],
    keywords: List[str],
    max_results: int,
    date_from: str | None = None,
) -> list[Dict[str, Any]]:
    arxiv = ArxivService()
    return await arxiv.search(
        categories=categories,
        keywords=keywords,
        max_results=max_results,
        date_from=date_from,
    )


async def _s2_recommendations_stream(
    s2: SemanticScholarService,
    db,
    ruleset_id: int,
    cutoff: datetime | None = None,
) -> Dict[str, Dict[str, Any]]:
    positive_s2_ids = [
        row[0] for row in db.query(Paper.s2_id).join(
            PaperRuleSet, Paper.id == PaperRuleSet.paper_id
        ).filter(
            PaperRuleSet.ruleset_id == ruleset_id,
            Paper.s2_id.isnot(None),
            (PaperRuleSet.status == "favorited") | (PaperRuleSet.llm_score >= 8),
        ).order_by(PaperRuleSet.llm_score.desc().nullslast()).limit(5).all()
        if row[0]
    ]
    negative_s2_ids = [
        row[0] for row in db.query(Paper.s2_id).join(
            PaperRuleSet, Paper.id == PaperRuleSet.paper_id
        ).filter(
            PaperRuleSet.ruleset_id == ruleset_id,
            PaperRuleSet.status == "archived",
            Paper.s2_id.isnot(None),
        ).limit(5).all()
        if row[0]
    ]

    recommended: Dict[str, Dict[str, Any]] = {}
    if positive_s2_ids:
        rec_papers = await s2.get_recommendations(
            positive_s2_ids,
            negative_paper_ids=negative_s2_ids or None,
            limit=100,
            fields=S2_SEARCH_FIELDS,
        )
        for p in rec_papers:
            pid = p.get("paperId")
            if pid and pid not in recommended:
                if cutoff:
                    pub_date = _parse_pub_date(p)
                    if pub_date and pub_date < cutoff:
                        continue
                recommended[pid] = p

        logger.info(
            "S2 recommendations merged",
            positive=len(positive_s2_ids),
            negative=len(negative_s2_ids),
            results=len(rec_papers),
        )

    return recommended

def _update_run_progress(run_id: int, stage: str, done: int, total: int):
    db = SessionLocal()
    try:
        run = db.query(Run).filter(Run.id == run_id).first()
        if run:
            run.progress = {"stage": stage, "done": done, "total": total}
            db.commit()
    finally:
        db.close()



def _mark_run_failed(run_id: int, error: str):
    fresh_db = SessionLocal()
    try:
        run = fresh_db.query(Run).filter(Run.id == run_id).first()
        if run and run.status != "failed":
            run.status = "failed"
            run.error = error
            run.completed_at = datetime.utcnow()
            fresh_db.commit()
    except Exception as inner_e:
        logger.error("Failed to mark run as failed", run_id=run_id, error=str(inner_e))
    finally:
        fresh_db.close()

def _s2_paper_to_arxiv_id(paper: Dict[str, Any]) -> str:
    external_ids = paper.get("externalIds") or {}
    arxiv_id = external_ids.get("ArXiv")
    if arxiv_id:
        return arxiv_id
    return f"s2:{paper.get('paperId', 'unknown')}"


def _parse_authors(authors_raw: list) -> List[str]:
    result = []
    for a in authors_raw:
        if isinstance(a, dict) and "name" in a:
            result.append(a["name"])
        elif isinstance(a, str):
            result.append(a)
    return result


def _parse_pub_date(paper: Dict[str, Any]) -> datetime | None:
    pd = paper.get("publicationDate")
    if pd:
        try:
            return datetime.strptime(pd, "%Y-%m-%d")
        except (ValueError, TypeError):
            pass
    year = paper.get("year")
    if year:
        return datetime(year, 1, 1)
    return None


def _upsert_paper(db, s2_paper: Dict[str, Any]) -> Paper:
    arxiv_id = _s2_paper_to_arxiv_id(s2_paper)
    existing = db.query(Paper).filter(Paper.arxiv_id == arxiv_id).first()

    survey = is_survey_paper(s2_paper)

    if existing:
        existing.citation_count = s2_paper.get("citationCount", 0) or 0
        existing.influential_citation_count = s2_paper.get("influentialCitationCount", 0) or 0
        existing.impact_score = compute_impact_score(s2_paper)
        existing.is_survey = survey
        existing.updated_at = datetime.utcnow()
        return existing

    paper = Paper(
        arxiv_id=arxiv_id,
        s2_id=s2_paper.get("paperId"),
        title=s2_paper.get("title", ""),
        authors=_parse_authors(s2_paper.get("authors", [])),
        abstract=s2_paper.get("abstract"),
        categories=[],
        published_date=_parse_pub_date(s2_paper),
        year=s2_paper.get("year"),
        venue=s2_paper.get("venue"),
        pdf_url=f"https://arxiv.org/pdf/{arxiv_id}.pdf" if not arxiv_id.startswith("s2:") else None,
        citation_count=s2_paper.get("citationCount", 0) or 0,
        influential_citation_count=s2_paper.get("influentialCitationCount", 0) or 0,
        impact_score=compute_impact_score(s2_paper),
        is_survey=survey,
    )
    db.add(paper)
    db.flush()
    return paper


def _get_user_preferences(db, ruleset_id: int) -> tuple[List[Dict], List[Dict]]:
    fav_rows = db.query(Paper, PaperRuleSet).join(
        PaperRuleSet, Paper.id == PaperRuleSet.paper_id
    ).filter(
        PaperRuleSet.ruleset_id == ruleset_id,
        PaperRuleSet.status == "favorited",
        PaperRuleSet.is_scored == True,
    ).order_by(PaperRuleSet.llm_score.desc().nullslast()).limit(5).all()

    arch_rows = db.query(Paper, PaperRuleSet).join(
        PaperRuleSet, Paper.id == PaperRuleSet.paper_id
    ).filter(
        PaperRuleSet.ruleset_id == ruleset_id,
        PaperRuleSet.status == "archived",
        PaperRuleSet.is_scored == True,
    ).order_by(PaperRuleSet.scored_at.desc()).limit(3).all()

    favorited = [{"title": p.title, "reason": a.llm_reason} for p, a in fav_rows]
    archived = [{"title": p.title} for p, a in arch_rows]
    return favorited, archived


def _passes_source_filter(s2_paper: Dict[str, Any], source_filter: str) -> bool:
    if source_filter == "all":
        return True
    external_ids = s2_paper.get("externalIds") or {}
    if source_filter == "arxiv":
        return "ArXiv" in external_ids
    if source_filter == "open_access":
        return "ArXiv" in external_ids or "PubMedCentral" in external_ids
    return True


def _kw_match(keyword: str, text: str) -> bool:
    pattern = r'\b' + re.escape(keyword) + r's?\b'
    return bool(re.search(pattern, text, re.IGNORECASE))


def _remove_low_score_papers(db, ruleset_id: int, min_score: int) -> int:
    low = db.query(PaperRuleSet).filter(
        PaperRuleSet.ruleset_id == ruleset_id,
        PaperRuleSet.is_scored == True,
        PaperRuleSet.llm_score < min_score,
        PaperRuleSet.status == "inbox",
    ).all()
    count = len(low)
    for assoc in low:
        db.delete(assoc)
    if count:
        db.commit()
    return count


async def _score_papers_concurrent(
    saved_papers: list,
    topic_sentence: str,
    favorited: list,
    archived: list,
    run_id: int,
    db,
):
    batch_size = app_settings.get_int("scoring_batch_size")
    concurrency = app_settings.get_int("scoring_concurrency")
    total = len(saved_papers)

    all_batches = []
    for i in range(0, total, batch_size):
        all_batches.append(saved_papers[i:i + batch_size])

    scored_count = 0
    for group_start in range(0, len(all_batches), concurrency):
        group = all_batches[group_start:group_start + concurrency]

        tasks = []
        for batch in group:
            batch_dicts = [{
                "title": p.title,
                "abstract": p.abstract,
                "year": p.year,
                "venue": p.venue,
                "citation_count": p.citation_count,
                "impact_score": p.impact_score,
                "is_survey": p.is_survey,
            } for p, _, _ in batch]
            tasks.append(score_batch(
                topic_sentence, batch_dicts,
                favorited=favorited, archived=archived,
            ))

        group_results = await asyncio.gather(*tasks, return_exceptions=True)

        for batch, result in zip(group, group_results):
            if isinstance(result, Exception):
                logger.error("Scoring group failed", error=str(result))
                for _, assoc, _ in batch:
                    assoc.llm_score = 5
                    assoc.llm_reason = "评分超时"
                    assoc.is_scored = True
                    assoc.scored_at = datetime.utcnow()
                    scored_count += 1
                continue
            for score_entry in result:
                idx = score_entry["index"]
                if 0 <= idx < len(batch):
                    _, assoc, _ = batch[idx]
                    assoc.llm_score = score_entry["score"]
                    assoc.llm_reason = score_entry["reason"]
                    assoc.is_scored = True
                    assoc.scored_at = datetime.utcnow()
                    scored_count += 1

        db.commit()
        papers_done = min((group_start + len(group)) * batch_size, total)
        _update_run_progress(run_id, "scoring", papers_done, total)

    return scored_count


async def _auto_analyze_papers(ruleset_id: int, run_id: int, db):
    if not app_settings.get_bool("auto_analysis_enabled"):
        return 0

    min_score = app_settings.get_int("auto_analysis_min_score")
    concurrency = app_settings.get_int("scoring_concurrency")

    rows = db.query(Paper, PaperRuleSet).join(
        PaperRuleSet, Paper.id == PaperRuleSet.paper_id
    ).filter(
        PaperRuleSet.ruleset_id == ruleset_id,
        PaperRuleSet.is_scored == True,
        PaperRuleSet.llm_score >= min_score,
        PaperRuleSet.analyzed_at.is_(None),
    ).all()

    if not rows:
        return 0

    total = len(rows)
    logger.info("Auto-analysis starting", ruleset_id=ruleset_id, count=total)
    _update_run_progress(run_id, "auto_analysis", 0, total)

    analyzed = 0
    for i in range(0, total, concurrency):
        group = rows[i:i + concurrency]
        tasks = [
            analyze_paper(
                arxiv_id=str(paper.arxiv_id),
                title=str(paper.title),
                authors=list(paper.authors or []),
                abstract=str(paper.abstract) if paper.abstract else None,
                year=int(paper.year) if paper.year else None,
                venue=str(paper.venue) if paper.venue else None,
                citation_count=int(paper.citation_count or 0),
                fetch_full_text=False,
            )
            for paper, assoc in group
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for (paper, assoc), result in zip(group, results):
            if isinstance(result, Exception):
                logger.error("Auto-analysis failed", arxiv_id=paper.arxiv_id, error=str(result))
                continue
            assoc.analysis = result
            assoc.analyzed_at = datetime.utcnow()
            analyzed += 1

        db.commit()
        done = min(i + len(group), total)
        _update_run_progress(run_id, "auto_analysis", done, total)

    logger.info("Auto-analysis done", ruleset_id=ruleset_id, analyzed=analyzed, total=total)
    return analyzed


async def _citation_snowball(
    s2: SemanticScholarService,
    db,
    ruleset_id: int,
    topic_sentence: str,
    favorited: list,
    archived: list,
    run_id: int,
    already_seen: Dict[str, Dict],
    source: str = "initialize",
) -> int:
    current_year = datetime.now().year

    seeds = db.query(Paper, PaperRuleSet).join(
        PaperRuleSet, Paper.id == PaperRuleSet.paper_id
    ).filter(
        PaperRuleSet.ruleset_id == ruleset_id,
        PaperRuleSet.is_scored == True,
        PaperRuleSet.llm_score >= 8,
        Paper.s2_id.isnot(None),
    ).order_by(Paper.citation_count.desc()).limit(5).all()

    if not seeds:
        logger.info("Citation snowball skipped: no high-score seeds", ruleset_id=ruleset_id)
        return 0

    seed_ids = [(p.s2_id, p.title) for p, _ in seeds]
    logger.info("Citation snowball starting", seeds=len(seed_ids), titles=[t for _, t in seed_ids])

    _update_run_progress(run_id, "citation_discovery", 0, len(seed_ids))

    existing_arxiv_ids = set(
        row[0] for row in db.query(Paper.arxiv_id).join(
            PaperRuleSet, Paper.id == PaperRuleSet.paper_id
        ).filter(PaperRuleSet.ruleset_id == ruleset_id).all()
    )

    discovered: Dict[str, Dict] = {}
    for i, (s2_id, title) in enumerate(seed_ids):
        citations = await s2.get_citations(s2_id, limit=10000, fields=S2_SEARCH_FIELDS)
        for p in citations:
            pid = p.get("paperId")
            if not pid or pid in already_seen or pid in discovered:
                continue
            cc = p.get("citationCount", 0) or 0
            yr = p.get("year", 0) or 0
            if cc >= 50 or (yr >= current_year - 1 and cc >= 10):
                aid = _s2_paper_to_arxiv_id(p)
                if aid not in existing_arxiv_ids:
                    discovered[pid] = p
        _update_run_progress(run_id, "citation_discovery", i + 1, len(seed_ids))
        logger.info("Seed citations fetched", seed=title[:40], raw=len(citations), new=len(discovered))

    if not discovered:
        logger.info("Citation snowball: no new papers found")
        return 0

    for p in discovered.values():
        p["_impact_score"] = compute_impact_score(p)
    ranked = sorted(discovered.values(), key=lambda x: x["_impact_score"], reverse=True)

    shortlist_size = app_settings.get_int("init_shortlist_size")
    citation_shortlist = ranked[:shortlist_size]

    new_papers = []
    for p in citation_shortlist:
        paper = _upsert_paper(db, p)
        assoc = db.query(PaperRuleSet).filter(
            PaperRuleSet.paper_id == paper.id,
            PaperRuleSet.ruleset_id == ruleset_id,
        ).first()
        if not assoc:
            assoc = PaperRuleSet(
                paper_id=paper.id,
                ruleset_id=ruleset_id,
                source=source,
                status="inbox",
            )
            db.add(assoc)
            new_papers.append((paper, assoc, p))
    db.commit()

    if not new_papers:
        logger.info("Citation snowball: all papers already in topic")
        return 0

    logger.info("Citation snowball scoring", new_papers=len(new_papers))
    _update_run_progress(run_id, "citation_scoring", 0, len(new_papers))

    scored = await _score_papers_concurrent(
        new_papers, topic_sentence,
        favorited, archived, run_id, db,
    )

    logger.info("Citation snowball done", ruleset_id=ruleset_id, discovered=len(discovered), scored=scored)
    return scored


async def run_initialize(run_id: int, ruleset_id: int, task_id: int | None = None):
    """
    Initialize Pipeline:
    1. S2 broad search (multiple query variants) -> dedupe
    2. Compute impact_score -> rank -> shortlist top ~40
    3. Batch LLM scoring (5 per call) -> save results
    """
    from .task_manager import complete_task, fail_task
    s2 = SemanticScholarService()
    db = SessionLocal()

    try:
        run = db.query(Run).filter(Run.id == run_id).first()
        ruleset = db.query(RuleSet).filter(RuleSet.id == ruleset_id).first()
        if not run or not ruleset:
            return

        run.status = "running"
        run.started_at = datetime.utcnow()
        db.commit()

        topic_sentence = str(getattr(ruleset, "topic_sentence", ""))
        raw_search_queries = getattr(ruleset, "search_queries", None)
        if isinstance(raw_search_queries, list) and len(raw_search_queries) > 0:
            search_queries = [str(q) for q in raw_search_queries]
        else:
            search_queries = [topic_sentence]
        sources = _get_sources("init_sources")
        logger.info("Init sources", sources=list(sources))

        all_papers: Dict[str, Dict[str, Any]] = {}
        method_papers: Dict[str, Dict[str, Any]] = {}
        arxiv_papers = []

        if "s2" in sources:
            all_papers = await _s2_search_stream(s2, search_queries, run_id)
            logger.info("S2 search done", total_unique=len(all_papers))

            raw_method_queries = getattr(ruleset, "method_queries", None)
            method_queries = [str(q) for q in raw_method_queries] if isinstance(raw_method_queries, list) else []
            if method_queries:
                _update_run_progress(run_id, "method_search", 0, len(method_queries))
                for i, mq in enumerate(method_queries):
                    results = await s2.search_papers(
                        query=mq, limit=3, fields=S2_SEARCH_FIELDS,
                    )
                    for p in results:
                        pid = p.get("paperId")
                        if pid and pid not in all_papers and pid not in method_papers:
                            method_papers[pid] = p
                    _update_run_progress(run_id, "method_search", i + 1, len(method_queries))
                logger.info("Method search done", queries=len(method_queries), new_papers=len(method_papers))

        if "arxiv" in sources:
            _update_run_progress(run_id, "arxiv_search", 0, 1)
            arxiv_max = app_settings.get_int("arxiv_max_papers")
            raw_categories = getattr(ruleset, "categories", None)
            categories = [str(c) for c in raw_categories] if isinstance(raw_categories, list) else []
            raw_keywords = getattr(ruleset, "keywords_include", None)
            keywords = [str(k) for k in raw_keywords] if isinstance(raw_keywords, list) else []
            arxiv_papers = await _arxiv_search_stream(
                categories=categories,
                keywords=keywords,
                max_results=arxiv_max,
            )
            _update_run_progress(run_id, "arxiv_search", 1, 1)

        _update_run_progress(run_id, "ranking", 0, len(all_papers))
        for p in all_papers.values():
            p["_impact_score"] = compute_impact_score(p)

        ranked = sorted(all_papers.values(), key=lambda x: x["_impact_score"], reverse=True)

        sf = str(getattr(ruleset, "source_filter", "all") or "all")
        if sf != "all":
            before = len(ranked)
            ranked = [p for p in ranked if _passes_source_filter(p, sf)]
            logger.info("Source filter applied", filter=sf, before=before, after=len(ranked))

        max_surveys = app_settings.get_int("init_max_surveys")
        shortlist_size = app_settings.get_int("init_shortlist_size")
        surveys = [p for p in ranked if is_survey_paper(p)][:max_surveys]
        non_surveys = [p for p in ranked if not is_survey_paper(p)]
        s2_shortlist = (surveys + non_surveys)[:shortlist_size]

        shortlisted_arxiv_ids = set()
        for p in s2_shortlist:
            aid = ((p.get("externalIds") or {}).get("ArXiv", ""))
            if aid:
                shortlisted_arxiv_ids.add(aid)

        arxiv_only = []
        if arxiv_papers:
            for ap in arxiv_papers:
                aid = (ap.get("externalIds") or {}).get("ArXiv", "")
                if not aid:
                    arxiv_only.append(ap)
                    continue
                if aid not in shortlisted_arxiv_ids:
                    arxiv_only.append(ap)
                    shortlisted_arxiv_ids.add(aid)

        method_shortlist = []
        if method_papers:
            for p in method_papers.values():
                aid = ((p.get("externalIds") or {}).get("ArXiv", ""))
                if aid and aid in shortlisted_arxiv_ids:
                    continue
                if aid:
                    shortlisted_arxiv_ids.add(aid)
                method_shortlist.append(p)

        shortlist = s2_shortlist + arxiv_only + method_shortlist
        logger.info(
            "Shortlisted",
            count=len(shortlist),
            s2=len(s2_shortlist),
            arxiv=len(arxiv_only),
            method=len(method_shortlist),
            surveys=len(surveys),
        )

        _update_run_progress(run_id, "scoring", 0, len(shortlist))

        method_paper_ids = set(p.get("paperId") for p in method_shortlist) if method_shortlist else set()

        saved_papers = []
        for p in shortlist:
            paper = _upsert_paper(db, p)
            assoc = db.query(PaperRuleSet).filter(
                PaperRuleSet.paper_id == paper.id,
                PaperRuleSet.ruleset_id == ruleset_id,
            ).first()
            if not assoc:
                assoc = PaperRuleSet(
                    paper_id=paper.id,
                    ruleset_id=ruleset_id,
                    source="initialize",
                    status="inbox",
                )
                db.add(assoc)
            saved_papers.append((paper, assoc, p))
        db.commit()

        favorited, archived = _get_user_preferences(db, ruleset_id)

        scored_count = await _score_papers_concurrent(
            saved_papers, topic_sentence,
            favorited, archived, run_id, db,
        )

        citation_scored = 0
        if "s2" in sources:
            citation_scored = await _citation_snowball(
                s2, db, ruleset_id, topic_sentence,
                favorited, archived, run_id, all_papers,
            )
        scored_count += citation_scored

        min_score = app_settings.get_int("min_score_to_keep")
        if min_score > 1:
            removed = _remove_low_score_papers(db, ruleset_id, min_score)
            logger.info("Low-score cleanup", ruleset_id=ruleset_id, removed=removed, threshold=min_score)

        await _auto_analyze_papers(ruleset_id, run_id, db)

        ruleset.is_initialized = True
        run.status = "completed"
        run.completed_at = datetime.utcnow()
        run.progress = {"stage": "done", "done": scored_count, "total": len(shortlist)}
        db.commit()

        if task_id:
            complete_task(task_id)
        logger.info("Initialize pipeline done", ruleset_id=ruleset_id, scored=scored_count)

    except Exception as e:
        logger.error("Initialize pipeline failed", error=str(e))
        _mark_run_failed(run_id, str(e))
        if task_id:
            fail_task(task_id, str(e))
    finally:
        db.close()


_STOPWORDS = frozenset({
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "as", "is", "was", "are", "were", "be",
    "been", "being", "have", "has", "had", "do", "does", "did", "will",
    "would", "could", "should", "may", "might", "shall", "can", "need",
    "this", "that", "these", "those", "it", "its", "we", "our", "they",
    "their", "not", "no", "nor", "so", "if", "then", "than", "too",
    "very", "just", "about", "also", "into", "over", "such", "after",
    "before", "between", "through", "during", "each", "all", "both",
    "more", "most", "other", "some", "only", "same", "how", "what",
    "which", "who", "when", "where", "why", "up", "out", "new", "use",
    "used", "using", "based", "via", "non", "pre", "under", "within",
    "without", "across", "among", "along", "per", "vs", "etc",
    "paper", "papers", "approach", "method", "methods", "results",
    "show", "propose", "proposed", "study", "work", "model", "models",
    "data", "learning", "training", "performance", "task", "tasks",
    "framework", "system", "analysis", "problem", "achieve", "existing",
})


def _extract_keyword_candidates(titles: List[str], existing_keywords: List[str]) -> List[str]:
    existing_lower = {kw.lower() for kw in existing_keywords}
    bigram_counter = Counter()
    unigram_counter = Counter()

    for title in titles:
        tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9+#.-]*", title.lower())
        meaningful = [t for t in tokens if t not in _STOPWORDS and len(t) > 2]

        for t in meaningful:
            if t not in existing_lower:
                unigram_counter[t] += 1

        for i in range(len(meaningful) - 1):
            bigram = f"{meaningful[i]} {meaningful[i+1]}"
            if bigram not in existing_lower:
                bigram_counter[bigram] += 1

    candidates = []
    for term, count in bigram_counter.most_common(10):
        if count >= 2:
            candidates.append(term)
    for term, count in unigram_counter.most_common(10):
        if count >= 3 and term not in " ".join(candidates):
            candidates.append(term)

    return candidates[:5]


def _auto_expand_keywords(db, ruleset_id: int):
    ruleset = db.query(RuleSet).filter(RuleSet.id == ruleset_id).first()
    if not ruleset:
        return

    good_papers = db.query(Paper).join(
        PaperRuleSet, Paper.id == PaperRuleSet.paper_id
    ).filter(
        PaperRuleSet.ruleset_id == ruleset_id,
        (PaperRuleSet.status == "favorited") | (PaperRuleSet.llm_score >= 8),
    ).all()

    if len(good_papers) < 3:
        return

    texts = []
    for p in good_papers:
        if p.title:
            texts.append(p.title)
        if p.abstract:
            texts.append(p.abstract)

    current_keywords = list(ruleset.keywords_include or [])
    new_terms = _extract_keyword_candidates(texts, current_keywords)

    archived_papers = db.query(Paper).join(
        PaperRuleSet, Paper.id == PaperRuleSet.paper_id
    ).filter(
        PaperRuleSet.ruleset_id == ruleset_id,
        PaperRuleSet.status == "archived",
    ).all()
    if archived_papers:
        archived_texts = []
        for p in archived_papers:
            if p.title:
                archived_texts.append(p.title)
        exclude_candidates = _extract_keyword_candidates(archived_texts, list(ruleset.keywords_exclude or []))
        exclude_candidates = [t for t in exclude_candidates if t not in current_keywords]
        if exclude_candidates:
            updated_exclude = list(ruleset.keywords_exclude or []) + exclude_candidates[:3]
            ruleset.keywords_exclude = updated_exclude
            logger.info(
                "Exclude keywords expanded",
                ruleset_id=ruleset_id,
                new_excludes=exclude_candidates[:3],
            )

    if new_terms:
        updated = current_keywords + new_terms
        ruleset.keywords_include = updated
        db.commit()
        logger.info(
            "Keywords auto-expanded",
            ruleset_id=ruleset_id,
            new_terms=new_terms,
            total_keywords=len(updated),
        )


async def run_track(run_id: int, ruleset_id: int, task_id: int | None = None):
    from .task_manager import complete_task, fail_task
    s2 = SemanticScholarService()
    db = SessionLocal()

    try:
        run = db.query(Run).filter(Run.id == run_id).first()
        ruleset = db.query(RuleSet).filter(RuleSet.id == ruleset_id).first()
        if not run or not ruleset:
            return

        run.status = "running"
        run.started_at = datetime.utcnow()
        db.commit()

        topic_sentence = str(getattr(ruleset, "topic_sentence", ""))
        raw_search_queries = getattr(ruleset, "search_queries", None)
        if isinstance(raw_search_queries, list) and len(raw_search_queries) > 0:
            search_queries = [str(q) for q in raw_search_queries]
        else:
            search_queries = [topic_sentence]
        sources = _get_sources("track_sources")
        logger.info("Track sources", sources=list(sources))

        cutoff: datetime
        if isinstance(ruleset.last_track_at, datetime):
            cutoff = cast(datetime, ruleset.last_track_at) - timedelta(days=3)
        elif isinstance(ruleset.created_at, datetime):
            cutoff = cast(datetime, ruleset.created_at)
        else:
            cutoff = datetime.utcnow() - timedelta(days=3)
        cutoff_year = cutoff.year

        all_papers: Dict[str, Dict[str, Any]] = {}
        arxiv_papers = []

        if "s2" in sources:
            all_papers = await _s2_search_stream(
                s2,
                search_queries,
                run_id,
                year_start=cutoff_year,
                cutoff=cutoff,
            )

            rec_papers = await _s2_recommendations_stream(
                s2,
                db,
                ruleset_id,
                cutoff=cutoff,
            )
            for pid, p in rec_papers.items():
                if pid not in all_papers:
                    all_papers[pid] = p

        if "arxiv" in sources:
            arxiv_date_from = cutoff.strftime("%Y%m%d") + "0000"
            raw_categories = getattr(ruleset, "categories", None)
            categories = [str(c) for c in raw_categories] if isinstance(raw_categories, list) else []
            raw_keywords = getattr(ruleset, "keywords_include", None)
            keywords = [str(k) for k in raw_keywords] if isinstance(raw_keywords, list) else []
            arxiv_papers = await _arxiv_search_stream(
                categories=categories,
                keywords=keywords,
                max_results=app_settings.get_int("arxiv_max_papers"),
                date_from=arxiv_date_from,
            )

            s2_arxiv_ids = set()
            for p in all_papers.values():
                aid = ((p.get("externalIds") or {}).get("ArXiv", ""))
                if aid:
                    s2_arxiv_ids.add(aid)

            arxiv_new = 0
            for i, ap in enumerate(arxiv_papers):
                aid = (ap.get("externalIds") or {}).get("ArXiv", "")
                if not aid:
                    all_papers[f"arxiv:unknown:{i}"] = ap
                    arxiv_new += 1
                    continue
                if aid not in s2_arxiv_ids:
                    all_papers[f"arxiv:{aid}"] = ap
                    s2_arxiv_ids.add(aid)
                    arxiv_new += 1

            logger.info("Track ArXiv done", total=len(arxiv_papers), new=arxiv_new)

        sf = str(getattr(ruleset, "source_filter", "all") or "all")
        if sf != "all":
            before = len(all_papers)
            all_papers = {pid: p for pid, p in all_papers.items() if _passes_source_filter(p, sf)}
            logger.info("Track source filter", filter=sf, before=before, after=len(all_papers))

        raw_keywords = getattr(ruleset, "keywords_include", None)
        keywords = [str(k) for k in raw_keywords] if isinstance(raw_keywords, list) else []
        raw_exclude_keywords = getattr(ruleset, "keywords_exclude", None)
        exclude_keywords = [str(k) for k in raw_exclude_keywords] if isinstance(raw_exclude_keywords, list) else []

        filtered = {}
        for pid, p in all_papers.items():
            text = f"{p.get('title', '')} {p.get('abstract', '')}".lower()
            if exclude_keywords and any(_kw_match(kw, text) for kw in exclude_keywords):
                continue
            if keywords and not any(_kw_match(kw, text) for kw in keywords):
                continue
            filtered[pid] = p

        logger.info("Track keyword filter", before=len(all_papers), after=len(filtered))

        s2_filtered = {pid: p for pid, p in filtered.items() if not pid.startswith("arxiv:")}
        arxiv_filtered = [p for pid, p in filtered.items() if pid.startswith("arxiv:")]

        for p in s2_filtered.values():
            p["_impact_score"] = compute_impact_score(p)

        ranked_s2 = sorted(s2_filtered.values(), key=lambda x: x["_impact_score"], reverse=True)
        track_top = app_settings.get_int("track_top_n")
        shortlist = ranked_s2[:track_top] + arxiv_filtered
        logger.info("Track shortlist", s2=min(len(ranked_s2), track_top), arxiv=len(arxiv_filtered))

        _update_run_progress(run_id, "scoring", 0, len(shortlist))

        existing_arxiv_ids = set(
            row[0] for row in db.query(Paper.arxiv_id).join(
                PaperRuleSet, Paper.id == PaperRuleSet.paper_id
            ).filter(PaperRuleSet.ruleset_id == ruleset_id).all()
        )

        new_papers = []
        for p in shortlist:
            aid = _s2_paper_to_arxiv_id(p)
            if aid in existing_arxiv_ids:
                continue
            paper = _upsert_paper(db, p)
            assoc = PaperRuleSet(
                paper_id=paper.id,
                ruleset_id=ruleset_id,
                source="track",
                status="inbox",
            )
            db.add(assoc)
            new_papers.append((paper, assoc, p))
        db.commit()

        favorited, archived = _get_user_preferences(db, ruleset_id)

        scored_count = await _score_papers_concurrent(
            new_papers, topic_sentence,
            favorited, archived, run_id, db,
        )

        citation_scored = 0
        if "s2" in sources:
            citation_scored = await _citation_snowball(
                s2, db, ruleset_id, topic_sentence,
                favorited, archived, run_id, all_papers,
                source="track",
            )
        scored_count += citation_scored

        track_min = app_settings.get_int("track_min_score")
        if track_min > 1:
            removed = _remove_low_score_papers(db, ruleset_id, track_min)
            logger.info("Track low-score cleanup", ruleset_id=ruleset_id, removed=removed, threshold=track_min)

        await _auto_analyze_papers(ruleset_id, run_id, db)

        try:
            _auto_expand_keywords(db, ruleset_id)
        except Exception as e:
            logger.warning("Keyword auto-expansion failed", error=str(e))

        ruleset.last_track_at = datetime.utcnow()
        run.status = "completed"
        run.completed_at = datetime.utcnow()
        run.progress = {"stage": "done", "done": scored_count, "total": len(new_papers)}
        db.commit()

        if task_id:
            complete_task(task_id)
        logger.info("Track pipeline done", ruleset_id=ruleset_id, new=len(new_papers), scored=scored_count)

    except Exception as e:
        logger.error("Track pipeline failed", error=str(e))
        _mark_run_failed(run_id, str(e))
        if task_id:
            fail_task(task_id, str(e))
    finally:
        db.close()
