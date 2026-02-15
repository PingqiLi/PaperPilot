# Paper Agent (v0.8.0 Release) 🚀

Paper Agent 是一个基于本地大模型 (Local LLM) 的 ArXiv 论文智能筛选与追踪系统。它结合了 Semantic Scholar 的海量数据与 OpenClaw 的智能体能力，能够自动发现、阅读并评分每日更新的学术论文。

![Dashboard Preview](https://via.placeholder.com/800x400?text=Paper+Agent+Dashboard)

## ✨ 核心特性

- **🤖 本地智能体驱动**: 集成 OpenClaw + Ollama (推荐 Qwen3-VL 8B)，完全本地运行，保护隐私零成本。
- **🎯 深度语义筛选**: 基于 "Topic Description" 而非简单关键词匹配，准确理解研究方向。
- **📚 S2 深度集成**: 利用 Semantic Scholar API 获取权威引用数据，发现高影响力论文。
- **🖥️ 现代化 UI**: 沉浸式阅读体验，Markdown 渲染分析报告，支持暗色模式。
- **⚡️ 快速部署**: Docker Compose 一键启动数据库，Python/Node.js 双栈架构。

---

## 🛠️ 环境准备 (Prerequisites)

请确保本地环境满足以下要求：

- **Python**: >= 3.10
- **Node.js**: >= v18 (推荐 v20 LTS)
- **PostgreSQL**: >= 14
- **Ollama**: 本地运行的大模型服务
  - 推荐模型: `ollama pull qwen3-vl:8b` (兼顾速度与图文理解)
- **OpenClaw Gateway**: 智能体网关服务 (详见下方安装)

---

## 📦 安装与配置 (Installation)

### 1. 基础服务准备
首先确保 PostgreSQL 和 Redis (可选) 正在运行。推荐使用 Docker Compose 启动数据库：

```bash
docker-compose up -d db
```

### 2. 后端服务 (Backend)

```bash
# 1. 安装 Python依赖
pip install -r requirements.txt

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入 S2_API_KEY (可选) 和 DATABASE_URL

# 3. 初始化数据库
alembic upgrade head

# 4. 启动后端 API
python src/main.py
# 服务将运行在 http://localhost:8000
```

### 3. 前端界面 (Frontend)

```bash
cd frontend

# 1. 安装依赖
npm install

# 2. 启动开发服务器
npm run dev
# 访问 http://localhost:5173
```

### 4. OpenClaw 智能体网关 (Agent Runtime)

本项目依赖 OpenClaw Gateway 提供本地 Agent 能力。

**A. 获取代码 (指定版本)**
```bash
# 假设与 paper-agent 同级目录
git clone https://github.com/openclaw/openclaw.git
cd openclaw
git checkout 417509c5396f52a7e8e375c7b3eaa7050f7b3d9f  # 固化版本 (2026-02-15 Verified)
npm install
```

**B. 配置 OpenClaw (连接 Ollama)**
创建或编辑 `~/.openclaw/openclaw.json`:

```json
{
  "gateway": {
    "auth": { "token": "test" },
    "mode": "local"
  },
  "models": {
    "providers": {
      "ollama": {
        "baseUrl": "http://127.0.0.1:11434/v1",
        "apiKey": "ollama",
        "api": "openai-completions",
        "models": [
          {
            "id": "qwen3-vl:8b",
            "name": "Qwen3-VL 8B",
            "contextWindow": 32768,
            "maxTokens": 8192,
            "input": ["text", "image"],
            "reasoning": false
          }
        ]
      }
    }
  },
  "agents": {
    "defaults": {
      "model": { "primary": "ollama/qwen3-vl:8b" }
    }
  }
}
```

**C. 启动网关**
```bash
node scripts/run-node.mjs gateway --port 18789 --verbose
# 网关将运行在 ws://127.0.0.1:18789
```

---

## ✅ 验证安装 (Verification)

我们提供了一键健康检查脚本，确保所有组件连接正常：

```bash
python scripts/check_health.py
```

**预期输出**:
```text
🏥 Starting System Health Check...

📊 Summary:
Database: ✅ PASS
Semantic Scholar: ✅ PASS
OpenClaw Agent: ✅ PASS

🚀 System is READY for deployment!
```

---

## 🚀 使用指南 (Run Screening)

1. **创建 RuleSet**:
   - 访问 Web UI，点击 `New RuleSet`。
   - 输入 `Topic Name` (如 "LLM Inference")。
   - **关键**: 在 `Topic Description` 中详细描述你的需求 (如 "关注量化、剪枝技术，忽略综述")。
   - 保存。

2. **运行智能筛选**:
   - 进入 RuleSet 详情页。
   - 点击右上角 **"Run Screening"** 按钮。
   - 系统将自动搜索 S2 最新论文，并调用本地 Agent 阅读打分。

3. **查看结果**:
   -刷新页面，分数 >= 6 的论文将高亮显示。
   - 点击论文查看详细的 Agent 分析报告。

---

## 📄 License

MIT License
