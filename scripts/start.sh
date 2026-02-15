#!/bin/bash
# Paper Agent 服务启动脚本
# 用法: ./scripts/start.sh

set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

echo "🧹 停止旧服务..."
pkill -f "uvicorn src.main:app" 2>/dev/null || true
pkill -f "vite.*paper-agent" 2>/dev/null || true
pkill -f "http.server 3001" 2>/dev/null || true
sleep 2

echo "🗄️ 检查PostgreSQL..."
if docker ps | grep -q paper-agent-postgres; then
    echo "  ✓ PostgreSQL 运行中"
else
    echo "  启动 PostgreSQL..."
    docker start paper-agent-postgres 2>/dev/null || \
    docker run -d --name paper-agent-postgres \
        -p 5432:5432 \
        -e POSTGRES_USER=paper_agent \
        -e POSTGRES_PASSWORD=paper_agent \
        -e POSTGRES_DB=paper_agent \
        postgres:15-alpine
    sleep 3
fi

echo "🚀 启动后端..."
export DATABASE_URL="postgresql://paper_agent:paper_agent@localhost:5432/paper_agent"
cd "$PROJECT_DIR"

# 初始化数据库表
echo "  初始化数据库表..."
uv run python -c "
from src.models.paper import Base
from src.database import engine
Base.metadata.create_all(bind=engine)
print('  ✓ 数据库表已就绪')
" 2>/dev/null || echo "  ⚠️ 表初始化跳过"

nohup uv run uvicorn src.main:app --host 127.0.0.1 --port 8000 > /tmp/backend.log 2>&1 &
BACKEND_PID=$!
echo "  后端 PID: $BACKEND_PID"

echo "🌐 启动前端..."
cd "$PROJECT_DIR/frontend"
nohup npm run dev -- --host 0.0.0.0 --port 3001 > /tmp/frontend.log 2>&1 &
FRONTEND_PID=$!
echo "  前端 PID: $FRONTEND_PID"

echo "⏳ 等待服务就绪..."
sleep 5

echo ""
echo "========================================="
echo "🎉 Paper Agent 服务已启动！"
echo "========================================="
echo ""
echo "📌 访问地址:"
echo "   前端: http://localhost:3001"
echo "   后端: http://localhost:8000"
echo "   API文档: http://localhost:8000/docs"
echo ""
echo "📋 日志文件:"
echo "   后端: tail -f /tmp/backend.log"
echo "   前端: tail -f /tmp/frontend.log"
echo ""

# 验证服务
echo "🔍 验证服务状态..."
if curl -s http://localhost:8000/health > /dev/null; then
    echo "   ✓ 后端 OK"
else
    echo "   ✗ 后端启动失败，查看 /tmp/backend.log"
fi

if curl -s --max-time 3 http://localhost:3001 > /dev/null 2>&1; then
    echo "   ✓ 前端 OK"
else
    echo "   ⏳ 前端启动中..."
fi

echo ""
echo "停止服务: pkill -f 'uvicorn src.main'; pkill -f vite"
