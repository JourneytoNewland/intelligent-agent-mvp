# 🌟 IntelligentAgentMVP 项目概览

## 🎯 项目简介

基于 **FastAPI + LangGraph + MCP + Skills** 的智能数据分析 Agent MVP

**GitHub 仓库**: https://github.com/JourneytoNewland/intelligent-agent-mvp

## 📊 完成情况

```
✅ MVP 完成: 100%
✅ 测试通过: 27/27 (100%)
✅ 代码行数: 11,440 行
✅ 文件数量: 67 个
✅ 文档数量: 10+ 篇
✅ GitHub 发布: ✅ 完成
```

## 🏗️ 技术架构

```
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI + LangGraph + Skills              │
└─────────────────────────────────────────────────────────────┘

    API 层
        ↓
    编排层
        ↓
    业务层
        ↓
    工具层
        ↓
    基础设施层
```

## 🚀 快速开始

\`\`\`bash
# 1. 克隆仓库
git clone https://github.com/JourneytoNewland/intelligent-agent-mvp.git
cd intelligent-agent-mvp

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境
cp .env.example .env
vim .env

# 4. 初始化数据库
psql -U postgres -d agent_db -f sql/01_init_database.sql

# 5. 启动服务
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 6. 测试 API
curl -X POST http://localhost:8000/api/v1/chat/ \
  -H "Content-Type: application/json" \
  -d '{"message": "你好"}'
\`\`\`

## 📁 核心文件

### 应用代码
- [app/main.py](app/main.py) - FastAPI 应用入口
- [app/api/v1/chat.py](app/api/v1/chat.py) - 聊天 API
- [app/core/graph/agent.py](app/core/graph/agent.py) - Agent 状态图
- [app/core/skills/query_metrics.py](app/core/skills/query_metrics.py) - Skills 实现
- [app/core/session.py](app/core/session.py) - 会话管理器

### 测试脚本
- [scripts/test_api.py](scripts/test_api.py) - API 测试
- [scripts/test_graph.py](scripts/test_graph.py) - LangGraph 测试
- [scripts/test_skills.py](scripts/test_skills.py) - Skills 测试
- [scripts/test_mcp_tools.py](scripts/test_mcp_tools.py) - MCP 工具测试

### 文档
- [README.md](README.md) - 项目主页
- [MVP_COMPLETE.md](MVP_COMPLETE.md) - MVP 完成总结
- [TEST_REPORT.md](TEST_REPORT.md) - 测试报告

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

## ✨ 核心功能

### 1. 智能意图识别
- **支持意图**: query_metrics, generate_report, analyze_root_cause, chat
- **LLM 模式**: 智谱 AI GLM-4
- **规则匹配**: 关键词匹配降级

### 2. Skills 能力封装
- **QueryMetricsSkill**: 查询业务指标
- **GenerateReportSkill**: 生成业务报表
- **AnalyzeRootCauseSkill**: 分析异常原因

### 3. LangGraph 状态编排
- **状态节点**: intent_recognition → skill_execution → response_generation
- **消息历史**: LangChain BaseMessage 格式
- **流式事件**: SSE 实时推送

### 4. RESTful API
- **聊天接口**: POST /api/v1/chat/
- **流式聊天**: POST /api/v1/chat/stream
- **会话管理**: GET /api/v1/chat/sessions/{id}
- **健康检查**: GET /api/v1/health

## 📊 测试结果

| 阶段 | 测试数 | 通过率 | 状态 |
|------|--------|--------|------|
| Stage 1: 项目基础 | 2/2 | 100% | ✅ |
| Stage 2: MCP 工具层 | 6/6 | 100% | ✅ |
| Stage 3: Skills 层 | 6/6 | 100% | ✅ |
| Stage 4: LangGraph 编排 | 5/5 | 100% | ✅ |
| Stage 5: FastAPI 集成 | 8/8 | 100% | ✅ |
| **总计** | **27/27** | **100%** | ✅ |

## 🎯 后续规划

- [ ] 实现 LLM 参数提取
- [ ] 优化数据库 Schema
- [ ] 添加 JWT 认证
- [ ] 添加速率限制
- [ ] OpenTelemetry 集成

## 📄 许可证

MIT License

## 👥 贡献

欢迎提交 Issue 和 Pull Request！

---

**项目状态**: ✅ MVP 完成，已发布到 GitHub
**版本**: 0.1.0
**仓库地址**: https://github.com/JourneytoNewland/intelligent-agent-mvp

🎉🎉🎉
