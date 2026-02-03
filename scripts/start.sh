#!/bin/bash

# 智能体 MVP 项目启动脚本

set -e

echo "🚀 启动智能体 MVP 项目..."

# 检查 Docker 是否运行
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker 未运行，请先启动 Docker"
    exit 1
fi

# 检查 .env 文件是否存在
if [ ! -f .env ]; then
    echo "⚠️  .env 文件不存在，从 .env.example 复制..."
    cp .env.example .env
    echo "✅ .env 文件已创建，请编辑并填入必要的配置"
    exit 0
fi

# 启动 Docker 服务
echo "📦 启动 Docker 服务 (PostgreSQL + Redis + Langfuse + Jaeger)..."
docker-compose -f docker/docker-compose.yml up -d

# 等待数据库启动
echo "⏳ 等待数据库启动..."
sleep 5

# 检查数据库是否就绪
until docker exec agent-postgres pg_isready -U postgres > /dev/null 2>&1; do
    echo "⏳ 等待 PostgreSQL..."
    sleep 2
done
echo "✅ PostgreSQL 已就绪"

# 检查 Redis 是否就绪
until docker exec agent-redis redis-cli ping > /dev/null 2>&1; do
    echo "⏳ 等待 Redis..."
    sleep 2
done
echo "✅ Redis 已就绪"

# 初始化数据库（如果需要）
echo "🗄️  初始化数据库..."
docker exec agent-postgres psql -U postgres -d agent_db -f /docker-entrypoint-initdb.d/01_init_database.sql > /dev/null 2>&1 || echo "数据库可能已初始化"

echo ""
echo "✅ 所有服务已启动！"
echo ""
echo "📊 服务地址："
echo "  - FastAPI 应用:     http://localhost:8000"
echo "  - API 文档:         http://localhost:8000/docs"
echo "  - PostgreSQL:       localhost:5432"
echo "  - Redis:            localhost:6379"
echo "  - Langfuse:         http://localhost:3000"
echo "  - Jaeger UI:        http://localhost:16686"
echo ""
echo "🧪 快速测试："
echo "  curl http://localhost:8000/health"
echo ""
echo "🛠️  启动 FastAPI 开发服务器："
echo "  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
echo ""
echo "📚 查看日志："
echo "  docker-compose -f docker/docker-compose.yml logs -f"
echo ""
echo "🛑 停止服务："
echo "  docker-compose -f docker/docker-compose.yml down"
echo ""
