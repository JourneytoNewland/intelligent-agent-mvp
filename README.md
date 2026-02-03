# IntelligentAgentMVP - 智能数据分析平台

基于 **FastAPI + LangGraph + MCP + Skills** 的智能数据分析 Agent MVP

## 🎯 项目概述

这是一个完整的智能数据分析平台 MVP，实现了：

- ✅ **智能意图识别** - LLM + 规则双模式
- ✅ **业务能力封装** - Skills 插件系统
- ✅ **状态机编排** - LangGraph 状态流转
- ✅ **RESTful API** - 聊天接口 + 会话管理
- ✅ **SSE 流式输出** - 实时进度反馈

**MVP 完成度**: 100% (27/27 测试通过)

## 🏗️ 技术架构

```
API 层 (FastAPI)
    ↓
编排层 (LangGraph)
    ↓
业务层 (Skills)
    ↓
工具层 (MCP)
    ↓
基础设施 (PostgreSQL, Redis, LLM)
```

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，配置数据库、Redis、智谱 AI API Key
```

### 3. 初始化数据库

```bash
psql -U postgres -d agent_db -f sql/01_init_database.sql
```

### 4. 启动服务

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. 访问 API

- API 文档: http://localhost:8000/docs
- 健康检查: http://localhost:8000/health

## 📡 API 使用示例

### 简单聊天

```bash
curl -X POST http://localhost:8000/api/v1/chat/ \
  -H "Content-Type: application/json" \
  -d '{"message": "查询最近7天的销售额"}'
```

### 多轮对话

```bash
# 第一轮
SESSION_ID=$(curl -X POST http://localhost:8000/api/v1/chat/ \
  -H "Content-Type: application/json" \
  -d '{"message": "你好"}' | jq -r '.session_id')

# 第二轮
curl -X POST http://localhost:8000/api/v1/chat/ \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"查询销售额\", \"session_id\": \"$SESSION_ID\"}"
```

### 流式聊天

```bash
curl -X POST http://localhost:8000/api/v1/chat/stream \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{"message": "生成销售报表"}'
```

## 🧪 运行测试

```bash
# MCP 工具测试
python scripts/test_mcp_tools.py

# Skills 测试
python scripts/test_skills.py

# LangGraph 测试
python scripts/test_graph.py

# API 测试（需要先启动服务）
python scripts/test_api.py
```

## 📁 项目结构

```
intelligent-agent-mvp/
├── app/
│   ├── api/v1/           # API 路由
│   │   ├── chat.py       # 聊天接口
│   │   └── health.py     # 健康检查
│   ├── core/
│   │   ├── graph/        # LangGraph 状态图
│   │   │   ├── agent.py  # Agent 状态图
│   │   │   ├── intent.py # 意图识别
│   │   │   └── state.py  # 状态定义
│   │   ├── skills/       # Skills 业务层
│   │   │   ├── base.py   # BaseSkill 抽象类
│   │   │   ├── query_metrics.py # Skills 实现
│   │   │   └── registry.py # Skills 注册表
│   │   ├── mcp/          # MCP 工具层
│   │   │   ├── tools/    # MCP 工具实现
│   │   │   └── client.py # MCP 客户端
│   │   └── session.py    # 会话管理器
│   ├── config.py         # 配置管理
│   ├── dependencies.py   # 依赖注入
│   └── main.py           # 应用入口
├── scripts/              # 测试脚本
├── sql/                  # 数据库脚本
├── docs/                 # 架构文档
├── STAGE*.md            # 各阶段总结
└── MVP_COMPLETE.md      # MVP 完成总结
```

## ✨ 核心功能

### 1. 智能意图识别

- **支持意图**: query_metrics, generate_report, analyze_root_cause, chat
- **LLM 模式**: 智谱 AI GLM-4 深度理解
- **规则匹配**: 关键词匹配降级方案

### 2. Skills 能力封装

- **QueryMetricsSkill**: 查询业务指标（时间范围、维度聚合）
- **GenerateReportSkill**: 生成业务报表（CSV/JSON 导出）
- **AnalyzeRootCauseSkill**: 分析异常原因（规则+LLM）

### 3. LangGraph 状态编排

- **状态节点**: intent_recognition → skill_execution → response_generation
- **消息历史**: LangChain BaseMessage 格式
- **流式事件**: SSE 实时推送

### 4. 会话管理

- **Redis 存储**: 自动过期（1 小时 TTL）
- **消息历史**: 完整的对话上下文
- **CRUD 操作**: 创建、查询、更新、删除

## 📊 测试结果

```
✅ Stage 1: 2/2 测试通过
✅ Stage 2: 6/6 测试通过
✅ Stage 3: 6/6 测试通过
✅ Stage 4: 5/5 测试通过
✅ Stage 5: 8/8 测试通过

总计: 27/27 测试通过 🎉
```

## 🔧 技术栈

| 组件 | 版本 | 用途 |
|------|------|------|
| FastAPI | 0.109.0 | Web 框架 |
| LangGraph | 1.0.7 | 状态机编排 |
| LangChain | 1.2.8 | LLM 集成 |
| Pydantic | v2.12.5 | 数据验证 |
| PostgreSQL | 17.7 | 数据存储 |
| Redis | 8.4.0 | 缓存和会话 |
| 智谱 AI | GLM-4 | 意图识别 |
| httpx | 0.28.1 | 异步 HTTP |
| asyncpg | - | 异步 PostgreSQL |
| redis-py | 5.0.1 | 异步 Redis |

## 📚 文档

- [MVP 完成总结](MVP_COMPLETE.md) - 完整的项目总结
- [Stage 1 总结](STAGE1_SUMMARY.md) - 项目基础
- [Stage 2 总结](STAGE2_SUMMARY.md) - MCP 工具层
- [Stage 3 总结](STAGE3_SUMMARY.md) - Skills 层
- [Stage 4 总结](STAGE4_SUMMARY.md) - LangGraph 编排
- [Stage 5 总结](STAGE5_SUMMARY.md) - FastAPI 集成
- [Skills 架构](docs/skills_architecture.md) - Skills 架构图
- [LangGraph 架构](docs/langgraph_architecture.md) - 状态图架构
- [API 架构](docs/api_architecture.md) - API 架构图

## 🚦 生产部署

### Docker 部署（推荐）

```bash
# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

### 手动部署

```bash
# 启动 PostgreSQL 和 Redis
# 使用系统包或 Docker

# 启动应用
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## 🔐 配置说明

### 必填配置

```bash
# .env
DATABASE_URL=postgresql://postgres:postgres123@localhost:5432/agent_db
REDIS_URL=redis://localhost:6379/0
ZHIPUAI_API_KEY=your_api_key_here
```

### 可选配置

```bash
DEBUG=false
LOG_LEVEL=INFO
HOST=0.0.0.0
PORT=8000
CORS_ORIGINS=["http://localhost:3000"]
```

## 🎯 后续规划

- [ ] 实现 LLM 参数提取
- [ ] 优化数据库 Schema
- [ ] 添加 JWT 认证
- [ ] 添加速率限制
- [ ] OpenTelemetry 集成
- [ ] 前端界面开发

## 📄 许可证

MIT License

## 👥 贡献

欢迎提交 Issue 和 Pull Request！

---

**项目状态**: ✅ MVP 完成 (2026-02-03)
**维护者**: Claude Code
**版本**: 0.1.0
