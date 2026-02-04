# 短期优化实施计划（2 周）

**目标**: 提升 MVP 系统可扩展性
**时间**: 2026-02-04 ~ 2026-02-18
**优先级**: 高

---

## 📋 功能概述

### 1. LLM 参数提取 ✅
- **技术方案**: Function Calling + Prompt Engineering 双模式
- **核心能力**: 从自然语言提取结构化 Skill 参数
- **降级策略**: Function Calling → Prompt Engineering → 规则匹配

### 2. Skill 并行执行 ✅
- **核心能力**: 无依赖 Skills 异步并发执行
- **依赖分析**: 自动拓扑排序构建执行批次
- **性能提升**: 预期吞吐量提升 2-3x

### 3. 用户反馈机制 ✅
- **核心功能**: 👍/👎 反馈收集
- **数据价值**: 持续优化 Prompt 和 Skill 选择
- **统计分析**: 按意图/Skill 分组统计

### 4. 更多数据源 ✅
- **Excel 支持**: 读取/写入/查询 Excel 文件
- **HTTP API**: 调用第三方 RESTful API
- **扩展性**: 插件化数据源架构

---

## 🏗️ 架构设计

### 整体架构图

```
┌─────────────────────────────────────────────────────────────┐
│                     FastAPI Layer                            │
│  /api/v1/chat  +  /api/v1/feedback  +  /api/v1/datasources   │
└──────────────────────────┬──────────────────────────────────┘
                             │
┌──────────────────────────▼──────────────────────────────────┐
│              LangGraph Orchestration (V2)                    │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ Intent +    │  │ Parameter    │  │ Skill Executor   │  │
│  │ Param       │─▶│ Extraction   │─▶│ (Parallel)       │  │
│  │ Recognition │  │ (V2)         │  │                  │  │
│  └─────────────┘  └──────────────┘  └──────────────────┘  │
└──────────────────────────┬──────────────────────────────────┘
                             │
┌──────────────────────────▼──────────────────────────────────┐
│                    Skills Layer                              │
│  QueryMetrics │ GenerateReport │ AnalyzeRootCause           │
└──────────────────────────┬──────────────────────────────────┘
                             │
┌──────────────────────────▼──────────────────────────────────┐
│                      MCP Tools Layer                         │
│  Database │ HTTP │ Excel │ API │ Feedback                    │
└──────────────────────────┬──────────────────────────────────┘
                             │
┌──────────────────────────▼──────────────────────────────────┐
│                   Infrastructure                             │
│  PostgreSQL │ Redis │ File Storage │ LLM                    │
└─────────────────────────────────────────────────────────────┘
```

---

## 📁 文件清单

### 新增核心模块

| 文件 | 功能 | 行数 |
|------|------|------|
| `app/core/graph/param_schemas.py` | Pydantic 参数模型定义 | ~250 |
| `app/core/graph/intent_v2.py` | 意图+参数提取 V2 | ~400 |
| `app/core/skills/parallel_executor.py` | 并行执行器 | ~280 |
| `app/core/mcp/tools/feedback.py` | 反馈 MCP 工具 | ~220 |
| `app/core/mcp/tools/excel.py` | Excel MCP 工具 | ~200 |
| `app/core/mcp/tools/api_datasource.py` | API 数据源工具 | ~230 |

### 新增 API 路由

| 文件 | 端点数 | 功能 |
|------|--------|------|
| `app/api/v1/feedback.py` | 4 | 反馈提交、统计、查询 |
| `app/api/v1/datasources.py` | 8 | Excel/API 数据源管理 |

### 配置和依赖

| 文件 | 修改内容 |
|------|----------|
| `app/dependencies.py` | 添加新工具的依赖注入 |
| `app/main.py` | 注册新路由 |
| `sql/02_init_feedback.sql` | 反馈表结构 |

---

## 🔧 技术实现细节

### 1. 参数提取架构

**三层降级策略：**

```
Function Calling (准确率 99%)
    ↓ 失败
Prompt Engineering (准确率 85%)
    ↓ 失败
规则匹配 (准确率 60%)
```

**Pydantic 模型优势：**
- 自动类型验证和转换
- IDE 自动补全
- 与 FastAPI 无缝集成

**示例模型：**
```python
class QueryMetricsParams(BaseModel):
    metric: MetricType
    time_range: TimeRange
    dimensions: List[Dimension]
    filters: Dict[str, Any]
    limit: int = Field(default=100, ge=1, le=1000)
```

### 2. 并行执行算法

**拓扑排序构建批次：**

```python
# 示例依赖关系
dependency_graph = {
    "analyze_root_cause": ["query_metrics"]
}

# 输入
["query_metrics", "analyze_root_cause"]

# 批次
Batch 1: ["query_metrics"]
Batch 2: ["analyze_root_cause"]
```

**性能优化：**
- 使用 `asyncio.gather` 并发执行
- 可配置最大并发数（默认 5）
- 超时控制（默认 30s）
- 错误隔离（单个失败不影响其他）

### 3. 反馈数据模型

**表结构：**
```sql
CREATE TABLE user_feedback (
    id BIGSERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    message_id VARCHAR(255) NOT NULL,
    feedback_type VARCHAR(20) NOT NULL,
    user_comment TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP,
    UNIQUE(session_id, message_id)
);
```

**索引优化：**
- `session_id`: 快速查询会话反馈
- `(metadata->>'intent')`: 按意图统计
- `(metadata->>'skill_name')`: 按 Skill 统计
- `feedback_type`: 筛选正负反馈
- `created_at DESC`: 时间排序

### 4. 数据源扩展

**Excel 工具功能：**
- 读取 Excel/CSV 文件
- 按列筛选数据
- 写入/导出 Excel
- 文件上传/下载

**API 数据源功能：**
- 注册第三方 API
- 自动认证（Bearer/API Key）
- 请求重试（最多 3 次）
- 超时控制（默认 10s）

---

## 📊 性能预期

### 并行执行性能提升

**场景 1: 3 个无依赖 Skills**
- 串行执行: 3s + 2s + 1s = 6s
- 并行执行: max(3s, 2s, 1s) = 3s
- **提升**: 2x

**场景 2: 2 个有依赖 Skills**
- 串行: 2s + 3s = 5s
- 并行（智能调度）: Batch1 (2s) + Batch2 (3s) = 5s
- **提升**: 1x（依赖限制）

**场景 3: 5 个无依赖 Skills**
- 串行: 10s
- 并发控制: max(3s, 2s, 4s, 1s, 2s) = 4s
- **提升**: 2.5x

### 参数提取准确率

| 方法 | 准确率 | 延迟 | 成本 |
|------|--------|------|------|
| Function Calling | 99% | ~1s | ¥0.001/次 |
| Prompt Engineering | 85% | ~1.2s | ¥0.001/次 |
| 规则匹配 | 60% | <0.1s | ¥0 |

---

## 🗓️ 实施时间表

### Week 1: 核心功能开发

| 任务 | 负责人 | 工期 | 交付物 |
|------|--------|------|--------|
| 参数提取 V2 | Backend | 2d | `intent_v2.py`, `param_schemas.py` |
| 并行执行器 | Backend | 1.5d | `parallel_executor.py` |
| 反馈机制 | Backend | 1.5d | `feedback.py` MCP + API |
| Excel 工具 | Backend | 1d | `excel.py` MCP |
| API 数据源 | Backend | 1d | `api_datasource.py` MCP |

### Week 2: 集成测试和文档

| 任务 | 负责人 | 工期 | 交付物 |
|------|--------|------|--------|
| 数据源 API | Backend | 1d | `datasources.py` API |
| 单元测试 | QA | 2d | 测试覆盖率 >80% |
| 集成测试 | QA | 1d | 端到端测试 |
| 性能测试 | QA | 1d | 压力测试报告 |
| 文档更新 | Tech Writer | 1d | API 文档、README 更新 |

---

## ✅ 验收标准

### 功能验收

- [ ] 参数提取准确率 >90%（混合模式）
- [ ] 无依赖 Skills 并行执行成功
- [ ] 反馈提交和统计正常工作
- [ ] Excel 文件读取/写入成功
- [ ] API 数据源调用成功

### 性能验收

- [ ] 并行执行吞吐量提升 >1.5x
- [ ] 参数提取延迟 <1.5s（p95）
- [ ] 系统响应时间 <3s（p95）
- [ ] 并发支持 >100 QPS

### 质量验收

- [ ] 单元测试覆盖率 >80%
- [ ] 所有测试通过
- [ ] 无 P0/P1 级 Bug
- [ ] 文档完整（API + 架构）

---

## 🔒 风险和缓解

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|----------|
| 智谱 API 不稳定 | 高 | 中 | 多层降级策略 |
| 并发执行复杂度 | 中 | 高 | 充分测试 + 监控 |
| Excel 大文件内存 | 中 | 低 | 流式读取 + 限制大小 |
| 第三方 API 兼容性 | 低 | 中 | 规范化响应格式 |

---

## 📈 后续优化方向

### 中期规划（1-2 个月）

1. **LLM 参数优化**
   - 收集反馈数据优化 Prompt
   - A/B 测试不同 Few-shot 示例
   - 引入参数提取模型的微调

2. **并行执行增强**
   - 动态调整并发数
   - 支持 Skill 优先级
   - 执行进度实时推送

3. **反馈数据应用**
   - 自动分析负面反馈
   - Prompt 优化建议
   - Skill 性能评分

4. **数据源扩展**
   - 支持 CSV、JSON、Parquet
   - 支持 GraphQL API
   - 支持 WebSocket 数据流

---

## 📚 参考文档

- [智谱 GLM-4 Function Calling](https://open.bigmodel.cn/dev/api#function_calling)
- [Pydantic V2 文档](https://docs.pydantic.dev/latest/)
- [asyncio 并发编程](https://docs.python.org/3/library/asyncio.html)
- [pandas Excel 操作](https://pandas.pydata.org/docs/reference/api/pandas.read_excel.html)

---

**文档版本**: v1.0
**创建时间**: 2026-02-04
**维护者**: Claude Code
**状态**: ✅ 设计完成，待实施
