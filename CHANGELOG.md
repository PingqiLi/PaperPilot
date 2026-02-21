# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-02-21

### Added

- **AI-driven topic generation** — One-sentence input generates 3-tier pyramid search queries, ArXiv categories, and method keywords via LLM
- **Multi-source paper discovery** — Semantic Scholar semantic search + ArXiv boolean search + citation snowballing + method-specific search
- **Two-stage screening** — Impact Score metadata pre-filtering → LLM batch scoring with configurable batch size and concurrency
- **Smart recommendations** — S2 Recommendations API with positive/negative signal papers
- **Highlights homepage** — Cross-topic high-value paper view (LLM score ≥ 7)
- **Continuous tracking** — Scheduled automatic tracking with keyword auto-expansion
- **Deep paper analysis** — Full-text fetch + LLM-generated structured analysis reports
- **Research digests** — Field overview, weekly digest, and monthly report generation
- **Customizable prompts** — All prompt templates editable in Settings, with separate scoring rubric customization
- **Multi-language output** — Configurable output language (中文/English/日本語/한국어/Français/Español)
- **Email delivery** — SMTP digest delivery with SSL/STARTTLS support and structured HTML templates
- **Cost control** — Monthly budget cap, tiered scoring strategy, per-workflow cost tracking
- **App settings** — DB-first key-value configuration with .env fallback, full Settings UI
- **Scheduling** — APScheduler with configurable cron for track, weekly digest, and monthly report
- **Dark/light theme** — Full theme support with system preference detection
- **Docker deployment** — Two-container setup (backend + nginx frontend) with volume persistence
- **Backend tests** — 60 pytest tests covering API routes, models, and schemas
- **E2E tests** — Playwright browser tests for frontend workflows
