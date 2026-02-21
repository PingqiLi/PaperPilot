# PaperPilot

ArXiv 论文智能筛选系统 — 描述一个研究方向，自动收集高影响力基础论文，持续追踪新发布的高价值论文，生成结构化研究简报。

## 特性

- **AI 驱动的主题生成** — 输入一句话描述研究兴趣，LLM 自动生成三层金字塔搜索查询、ArXiv 分类、方法关键词
- **多源论文发现** — Semantic Scholar 语义搜索 + ArXiv 布尔检索 + 引文雪球 + 方法定向搜索
- **两阶段筛选** — Impact Score 元数据初筛（引用量 + 影响力 + 综述/顶会加分）→ LLM 批量精排（5 篇/次）
- **智能推荐** — S2 Recommendations API，高分论文作正向信号 + archived 论文作负向信号
- **Highlights 首页** — 默认展示所有主题中 LLM 评分 ≥ 7 的高价值论文
- **持续监控** — 每日自动检索新论文，关键词自动扩展，每周自动生成研究简报
- **研究简报** — 三种 LLM 驱动的结构化报告：领域概览、周报、月报
- **邮件推送** — 可选 SMTP 邮件发送简报，支持 SSL/STARTTLS
- **成本可控** — 分级评分策略，LLM 仅用于 shortlist，目标 < 30 RMB/月
- **暗色/亮色主题** — 现代 UI，支持主题切换

## 快速开始

### 环境要求

- Python >= 3.11
- Node.js >= 18
- Docker（可选，用于容器化部署）

### 本地开发

```bash
# 后端
uv sync                                    # 或 pip install -r requirements.txt
cp .env.example .env                       # 编辑 .env，填入 LLM_API_KEY
uvicorn src.main:app --reload --port 8000

# 前端
cd frontend && npm install && npm run dev

# 访问 http://localhost:3000
```

### Docker 部署

```bash
cp .env.example .env                       # 编辑 .env，填入 LLM_API_KEY
docker-compose up -d --build

# 访问 http://localhost:3000
```

两个容器：backend（Python + SQLite）+ frontend（Nginx）。SQLite 数据通过 Docker volume 持久化。

## 环境变量

| 变量 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `LLM_API_KEY` | 是 | — | 阿里云百炼 API Key |
| `LLM_BASE_URL` | 否 | `https://dashscope.aliyuncs.com/compatible-mode/v1` | OpenAI 兼容 API 地址 |
| `LLM_MODEL` | 否 | `qwen3.5-plus` | 模型 ID |
| `S2_API_KEY` | 否 | — | Semantic Scholar API Key，可提高速率限制 |
| `DATABASE_URL` | 否 | `sqlite:///data/paper_agent.db` | 数据库连接 |

SMTP 邮件推送通过应用内 Settings 页面配置（存储于 `app_settings` 表），也可通过环境变量设置初始值：

| 变量 | 说明 |
|------|------|
| `SMTP_HOST` | SMTP 服务器地址 |
| `SMTP_PORT` | SMTP 端口（465 用 SSL，587 用 STARTTLS）|
| `SMTP_USER` | SMTP 用户名 |
| `SMTP_PASSWORD` | SMTP 密码/授权码 |
| `SMTP_FROM` | 发件人地址 |
| `DIGEST_EMAIL_TO` | 简报收件人地址 |

## Pipeline 流程

<img src="docs/pipeline.png" alt="PaperPilot Pipeline" width="900">

**Initialize** 从零构建基础论文库：LLM 生成主题配置 → S2 语义搜索 + 方法定向搜索 + ArXiv 布尔检索 → 去重 → Impact Score 排序 → Shortlist ~40 篇 → LLM 批量评分 (5篇/次) → 引文雪球 (score ≥ 8) → 清理低分论文

**Track** 持续追踪新论文：S2 语义搜索 (日期过滤) + S2 推荐 (正向/负向信号) + ArXiv 布尔检索 → 关键词 Triage → Impact Score → Top N → LLM 评分 → 引文雪球 → 关键词自动扩展 → 清理低分论文

> 清理阈值默认值：Initialize 移除 score < 6 的论文，Track 移除 score < 7 的论文。可在 Settings 页面调整。

### 自动调度

- **Track**: 每周日 00:00（Asia/Shanghai），可在 Settings 页面调整
- **周报生成**: 每周一 09:00（Asia/Shanghai）

## 架构

**技术栈**: Python 3.11 / FastAPI / SQLAlchemy / SQLite(WAL) + React 18 / Vite 5 / Tailwind CSS v4

**LLM**: Qwen3.5-Plus via 阿里云百炼（OpenAI 兼容接口），httpx + tenacity 重试（3 次，指数退避 2-30s，超时 300s）

**Prompt Skill 系统** — 5 个结构化 prompt 模板，固定输入/输出 JSON schema：

| Prompt | 用途 | 输出 |
|--------|------|------|
| `batch_scoring.md` | 批量论文评分 | `{scores: [{index, score, reason}]}` |
| `draft_generation.md` | 主题配置生成 | `{name, categories, keywords, search_queries, method_queries}` |
| `field_overview.md` | 领域概览 | `{summary, pillars[], reading_path{}, open_problems[]}` |
| `weekly_digest.md` | 周报 | `{week_summary, must_read[], worth_noting[], trend_signal}` |
| `monthly_report.md` | 月报 | `{month_summary, highlights[], clusters[], momentum{}}` |

**配置管理**: `app_settings` 表（key-value），优先级：DB > `.env` > 硬编码默认值。通过 Settings 页面管理。

## 项目结构

```
src/
  main.py              # FastAPI 入口 + lifespan + 路由注册
  config.py            # Pydantic Settings（SQLite + LLM + SMTP）
  database.py          # SQLAlchemy + SQLite (WAL)
  models/              # ORM: Paper, RuleSet, Run, PaperRuleSet, TokenUsage, Digest, EmailLog
  schemas/             # Pydantic 请求/响应模型
  routers/             # API 路由
    rulesets.py          # 主题 CRUD + runs + papers
    papers.py            # 全局论文（highlighted 筛选）
    digests.py           # 简报 CRUD + 生成 + 邮件发送
    stats.py             # 成本统计（costs, daily, requests）
    rules.py             # ArXiv 分类列表
    health.py            # 健康检查
    app_settings.py      # 应用设置 + 邮件测试
  services/            # 业务逻辑
    llm_client.py        # OpenAI 兼容 LLM 客户端 + tenacity 重试
    draft_generator.py   # AI 主题配置生成（三层金字塔查询）
    batch_scorer.py      # 批量 LLM 评分（5 篇/次）
    digest_generator.py  # 领域概览 / 周报 / 月报生成
    email_service.py     # SMTP 邮件推送 + 结构化 HTML 模板
    impact_scoring.py    # S2 元数据 impact score
    pipeline.py          # Initialize + Track 编排
    semantic_scholar.py  # Semantic Scholar API（搜索 + 推荐 + 引文）
    arxiv.py             # ArXiv API 布尔检索
    scheduler.py         # APScheduler 定时任务
    app_settings.py      # 应用设置读写（DB 优先）
  prompts/             # 5 个 Markdown prompt 模板
frontend/
  src/
    pages/               # Papers, RuleSetWizard, RuleSetDashboard, CostStats, AppSettings
    components/          # Layout（侧边栏、主题切换、LLM Loading Banner）
    contexts/            # ThemeContext（暗色/亮色）
    api/                 # Axios API 层（client, rulesets, stats）
  e2e/                   # Playwright E2E 测试
```

## 测试

```bash
# 后端测试（60 tests, 排除 2 个已知 hang 的测试）
.venv/bin/pytest -k "not (test_create_run or test_list_runs)"

# E2E 测试
cd frontend && npx playwright test

# 前端构建
cd frontend && npm run build
```

## License

MIT
