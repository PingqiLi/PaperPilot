# AGENTS.md — Paper Agent

> ArXiv paper screening system powered by Qwen3.5-Plus via Alibaba Cloud Bailian API.
> Python 3.11 / FastAPI backend + React/Vite frontend + SQLite.

## Build & Run

```bash
# Install dependencies (uv preferred, pip also works)
uv sync                          # installs from pyproject.toml + uv.lock
pip install -r requirements.txt  # alternative

# Backend (port 8000) — SQLite auto-creates on first run
uvicorn src.main:app --reload --port 8000

# Frontend (port 3000)
cd frontend && npm install && npm run dev

# Docker (2 containers: backend + nginx frontend)
cp .env.example .env             # fill in LLM_API_KEY
docker-compose up -d --build
```

## Test Commands

```bash
# Backend tests (exclude known hangers)
.venv/bin/pytest -k "not (test_create_run or test_list_runs)"

# Single test file / class / function
pytest tests/test_api.py
pytest tests/test_api.py::TestDigestsRouter
pytest tests/test_api.py::TestDigestsRouter::test_list_digests_empty

# With output
pytest -s tests/test_api.py

# E2E tests (Playwright)
cd frontend && npx playwright test

# Frontend build
cd frontend && npm run build

# Kill dev servers before running E2E
lsof -ti:3000,8000 | xargs kill -9

# Async tests use pytest-asyncio with asyncio_mode=auto (see pytest.ini)
```

## Lint & Format

```bash
ruff check src/ tests/           # lint
ruff check --fix src/ tests/     # lint + autofix
black src/ tests/                 # format
```

No ruff/black config files exist — use defaults.

## Project Structure

```
src/
  main.py              # FastAPI app, lifespan, router registration
  config.py            # Pydantic Settings (SQLite + LLM + SMTP config)
  database.py          # SQLAlchemy engine (SQLite with WAL)
  models/
    paper.py             # Paper, TokenUsage, Base
    ruleset.py           # RuleSet, Run, PaperRuleSet
    digest.py            # Digest (field_overview/weekly/monthly)
  schemas/
    paper.py             # All Pydantic request/response schemas
  routers/
    papers.py            # Global papers endpoint with highlighted filter
    rulesets.py          # Topic CRUD, runs, papers
    digests.py           # Digest CRUD + generation
    stats.py             # Cost stats (costs, daily, requests)
    health.py            # Health check
    rules.py             # ArXiv categories
  services/
    llm_client.py        # OpenAI-compatible client with tenacity retry
    draft_generator.py   # LLM-generated topic config from sentence
    batch_scorer.py      # Batch LLM scoring (5 papers/call)
    digest_generator.py  # Field overview, weekly digest, monthly report
    email_service.py     # Optional SMTP digest delivery
    impact_scoring.py    # S2 metadata impact score formula
    pipeline.py          # Initialize + Track orchestration
    semantic_scholar.py  # S2 API client
    scheduler.py         # APScheduler (daily track + weekly digest)
  prompts/             # Markdown prompt templates (5 skills)
    batch_scoring.md
    draft_generation.md
    field_overview.md
    weekly_digest.md
    monthly_report.md
tests/                 # pytest tests (39 passing)
frontend/
  src/
    pages/               # Papers, RuleSetWizard, RuleSetDashboard, CostStats
    components/          # Layout (sidebar, theme toggle)
    contexts/            # ThemeContext (dark/light)
    api/                 # Axios API layer (client, rulesets, stats)
  e2e/                   # Playwright E2E tests (42 passing)
```

## Code Style

### Imports — 3 groups, separated by blank line

```python
# 1. Standard library
import json
from datetime import datetime
from typing import List, Dict, Any, Optional

# 2. Third-party
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
import structlog

# 3. Local (relative)
from ..config import settings
from ..models import Paper, RuleSet, PaperRuleSet
from ..services.llm_client import call_llm, load_prompt
```

### Naming

| Element      | Convention         | Example                          |
|--------------|--------------------|----------------------------------|
| Files        | `snake_case.py`    | `batch_scorer.py`                |
| Classes      | `PascalCase`       | `RuleSet`, `DigestResponse`      |
| Functions    | `snake_case`       | `generate_field_overview`        |
| Constants    | `UPPER_SNAKE_CASE` | `S2_API_BASE`, `PROMPTS_DIR`     |
| DB tables    | `snake_case`       | `paper_rulesets`, `digests`      |

### Docstrings & Comments

- Module-level: triple-quote one-liner describing purpose (Chinese OK)
- Class/method: triple-quote with Chinese descriptions
- Inline comments: Chinese for domain logic, English for technical notes

### Logging

Use `structlog` with keyword args. One logger per module.

```python
logger = structlog.get_logger(__name__)
logger.info("Paper processed", arxiv_id=paper.arxiv_id, score=result["score"])
```

### Error Handling

- **Graceful degradation**: services return sensible defaults on failure, never crash the pipeline.
- **Log errors with context**: always include identifiers (paper_id, ruleset_id).
- **Route handlers**: raise `HTTPException` with Chinese detail messages.
- **LLM calls**: tenacity retry (3 attempts, exponential backoff 2-30s) on timeout/connect errors.

```python
except Exception as e:
    logger.error("Rating failed", arxiv_id=paper.arxiv_id, error=str(e))
    return {"score": 5, "reason": "评分失败"}

if not ruleset:
    raise HTTPException(status_code=404, detail="规则集不存在")
```

### Database Access

- **Routes**: use `db: Session = Depends(get_db)` (FastAPI DI)
- **Services**: use `with get_db_context() as db:` (auto commit/rollback)
- **Background tasks**: create `SessionLocal()` manually with `try/finally: db.close()`

### LLM Integration

All LLM calls go through `src/services/llm_client.py` which wraps OpenAI-compatible API (Alibaba Cloud Bailian).

- `call_llm(prompt, workflow)` — single LLM call with retry and cost tracking
- `load_prompt(name)` — loads prompt template from `src/prompts/{name}.md`
- Each call is tagged with a `workflow` string for cost tracking in `TokenUsage` table
- Responses parsed with `_clean_json_response()` to strip markdown fences before `json.loads()`

5 prompt skills with strict JSON output schemas:

| Prompt | Workflow Tag | Input | Output |
|--------|-------------|-------|--------|
| `batch_scoring.md` | `batch_scoring` | topic + papers batch | `{scores: [{index, score, reason}]}` |
| `draft_generation.md` | `draft_generation` | topic sentence | `{name, categories, keywords, search_queries}` |
| `field_overview.md` | `field_overview` | topic + all papers | `{summary, pillars[], reading_path{}, open_problems[]}` |
| `weekly_digest.md` | `weekly_digest` | topic + week's papers | `{week_summary, must_read[], worth_noting[], trend_signal}` |
| `monthly_report.md` | `monthly_report` | topic + month's papers | `{month_summary, highlights[], clusters[], momentum{}}` |

### Testing Patterns

- Test classes: `TestXxxRouter`, `TestXxxModel`
- Use fixtures from `conftest.py` for sample data
- Async tests: `@pytest.mark.asyncio` (auto mode enabled)
- Do NOT test LLM generation directly (calls real API) — test validation & 404s only
- E2E tests: Playwright with backend webServer auto-start

### Key Rules

- **Direct API calls** to Alibaba Cloud Bailian — no proxy/gateway
- **Prompt templates** live in `src/prompts/*.md` — keep them as external files
- **Config** comes from `.env` (Pydantic Settings) — never hardcode
- **SQLite** with WAL mode — no migrations, tables auto-created via `Base.metadata.create_all`
- **Frontend** is plain JSX (no TypeScript) — keep it that way
- **Cost budget**: < 30 RMB/month LLM spend
