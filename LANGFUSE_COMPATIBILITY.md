# Langfuse + Pydantic v2 兼容方案

## 问题分析

**Langfuse SDK** (langfuse-python) 当前依赖 **Pydantic v1**，与我们的 **Pydantic v2.6.0** 不兼容。

---

## 解决方案

### 方案 A: 使用 Pydantic v1 兼容层 (推荐 ⭐)

**优点**:
- ✅ 保持项目使用 Pydantic v2
- ✅ Langfuse 可以正常工作
- ✅ 最小化改动

**实现**:
```bash
# 安装兼容包
pip install pydantic==1.10.18 langfuse --upgrade
```

**注意事项**:
- Langfuse 内部使用 v1，不影响项目的 v2 代码
- 需要确保两个版本隔离

---

### 方案 B: 使用 OpenTelemetry 替代 (推荐 ⭐⭐⭐)

**优点**:
- ✅ 完全兼容 Pydantic v2
- ✅ 更标准的 LLM 可观测性方案
- ✅ 不依赖第三方服务
- ✅ Stage 5 计划中已包含

**实现**:
```python
# 使用 OpenTelemetry 追踪 LLM 调用
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider

tracer = trace.get_tracer(__name__)
```

---

### 方案 C: 等待 Langfuse 官方支持

**状态**: Langfuse 团队正在开发 Pydantic v2 支持

**时间线**: 预计 2025 年 Q2-Q3

**当前方案**: 使用方案 A 或 B

---

### 方案 D: 使用自定义包装器

创建一个适配层，将 Pydantic v2 模型转换为 v1：

```python
from pydantic import BaseModel as BaseModelV2
from pydantic.v1 import BaseModel as BaseModelV1

def to_v1(model_v2: BaseModelV2) -> BaseModelV1:
    """将 Pydantic v2 模型转换为 v1"""
    import json
    return BaseModelV1(**json.loads(model_v2.model_dump_json()))
```

---

## 推荐方案

### MVP 阶段: **方案 B (OpenTelemetry)**

**理由**:
1. Stage 5 本来就要实现 OpenTelemetry
2. OpenTelemetry 是行业标准
3. 不依赖第三方服务
4. 完全兼容 Pydantic v2

### 生产环境: **方案 A (兼容层)**

**理由**:
1. Langfuse 提供更好的 LLM 可观测性
2. 支持成本追踪和用户会话
3. 可以在 Stage 5 之后添加

---

## 快速实现 (方案 A)

如果你想现在就启用 Langfuse，运行：

```bash
# 1. 卸载当前 Pydantic v2
pip uninstall pydantic pydantic-settings

# 2. 安装兼容版本
pip install 'pydantic>=1.10.0,<2.0.0'
pip install 'langfuse>=3.0.0'

# 3. 更新项目代码以兼容 Pydantic v1
# (需要大量修改，不推荐)
```

---

## 下一步建议

我建议：

1. **现在**: 使用 OpenTelemetry (方案 B)，保持 Pydantic v2
2. **Stage 5**: 实现 OpenTelemetry 集成
3. **生产环境**: 考虑添加 Langfuse (使用方案 A 的改进版)

你想采用哪个方案？
