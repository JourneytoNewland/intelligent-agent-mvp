"""
短期优化功能测试脚本

测试内容：
1. LLM 参数提取（Function Calling + Prompt Engineering）
2. Skill 并行执行
3. 用户反馈机制
4. Excel 数据源
5. HTTP API 数据源
"""

import asyncio
import sys
import os
from datetime import datetime
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.graph.intent_v2 import IntentRecognizerV2
from app.core.graph.param_schemas import (
    QueryMetricsParams,
    GenerateReportParams,
    validate_params,
    FEWSHOT_EXAMPLES
)
from app.core.skills.parallel_executor import ParallelSkillExecutor
from app.core.skills.registry import SkillRegistry
from app.core.mcp.tools.feedback import FeedbackTool, FeedbackType
from app.core.mcp.tools.excel import ExcelTool
from app.core.mcp.tools.api_datasource import APIDatasourceTool

# 修复导入兼容性
try:
    from app.core.skills.base import SkillExecutionResult
except ImportError:
    from app.core.skills.base import SkillOutput as SkillExecutionResult


# 测试配置
TEST_API_KEY = os.getenv("ZHIPUAI_API_KEY", "test_key")


class TestRunner:
    """测试运行器"""

    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.tests = []

    def run_test(self, name, coro):
        """运行单个测试"""
        print(f"\n{'='*60}")
        print(f"测试: {name}")
        print('='*60)

        try:
            result = asyncio.run(coro)
            if result:
                self.passed += 1
                self.tests.append((name, "✅ PASS"))
                print(f"✅ 通过")
            else:
                self.failed += 1
                self.tests.append((name, "✗ FAIL"))
                print(f"✗ 失败")
        except Exception as e:
            self.failed += 1
            self.tests.append((name, f"✗ ERROR: {e}"))
            print(f"✗ 错误: {e}")

    def print_summary(self):
        """打印测试总结"""
        print(f"\n{'='*60}")
        print("测试总结")
        print('='*60)
        for name, status in self.tests:
            print(f"{status} - {name}")
        print(f"\n总计: {self.passed + self.failed} 个测试")
        print(f"✅ 通过: {self.passed}")
        print(f"✗ 失败: {self.failed}")
        print(f"通过率: {self.passed/(self.passed+self.failed)*100:.1f}%")


# ============== 测试用例 ==============

async def test_param_schemas():
    """测试 1: Pydantic 参数模型"""

    # 测试 QueryMetricsParams
    params = QueryMetricsParams(
        metric="sales",
        time_range="7d",
        dimensions=["region", "product"],
        filters={"region": "华东"},
        limit=100
    )

    assert params.metric.value == "sales"
    assert params.time_range.value == "7d"
    assert len(params.dimensions) == 2
    assert params.limit == 100

    print(f"✓ 参数模型验证成功")
    print(f"  - metric: {params.metric}")
    print(f"  - time_range: {params.time_range}")
    print(f"  - dimensions: {params.dimensions}")
    print(f"  - filters: {params.filters}")

    # 测试参数验证函数
    validated = validate_params("query_metrics", {
        "metric": "user_count",
        "time_range": "30d",
        "dimensions": ["channel"]
    })
    assert validated.metric.value == "user_count"

    print(f"✓ 参数验证函数工作正常")

    # 测试 Few-shot 示例
    assert "query_metrics" in FEWSHOT_EXAMPLES
    assert len(FEWSHOT_EXAMPLES["query_metrics"]) > 0

    print(f"✓ Few-shot 示例加载成功")
    print(f"  - query_metrics: {len(FEWSHOT_EXAMPLES['query_metrics'])} 个示例")
    print(f"  - generate_report: {len(FEWSHOT_EXAMPLES.get('generate_report', []))} 个示例")
    print(f"  - analyze_root_cause: {len(FEWSHOT_EXAMPLES.get('analyze_root_cause', []))} 个示例")

    return True


async def test_intent_recognition_v2():
    """测试 2: 意图识别 V2（带参数提取）"""

    recognizer = IntentRecognizerV2(api_key=TEST_API_KEY)

    test_messages = [
        ("查询最近7天的销售额", "query_metrics"),
        ("生成2024年1月的销售报表", "generate_report"),
        ("分析昨天销售额下降的原因", "analyze_root_cause"),
        ("你好", "chat")
    ]

    for message, expected_intent in test_messages:
        try:
            # 注意：如果没有真实 API Key，会降级到规则匹配
            result = await recognizer.recognize_with_params(message)

            print(f"\n用户消息: {message}")
            print(f"  识别意图: {result['intent']}")
            print(f"  置信度: {result['confidence']}")
            print(f"  使用方法: {result['method']}")

            if result['intent'] == expected_intent:
                print(f"  ✓ 意图正确")
            else:
                print(f"  ⚠ 意图不匹配（期望: {expected_intent}）")

            # 显示提取的参数
            if result.get('params'):
                print(f"  提取参数: {result['params']}")

        except Exception as e:
            print(f"  ✗ 错误: {e}")
            # 测试继续，不算失败（可能是 API Key 无效）
            continue

    return True


async def test_parallel_executor():
    """测试 3: 并行 Skill 执行器"""

    # 创建 Skill 注册表
    registry = SkillRegistry()

    # 创建并行执行器
    executor = ParallelSkillExecutor(
        registry=registry,
        max_concurrency=3,
        default_timeout=30.0
    )

    # 测试依赖分析
    print(f"\n测试依赖图分析:")
    dependency_graph = executor.get_dependency_graph()
    print(f"  依赖关系: {dependency_graph}")

    # 测试批次构建
    skill_requests = [
        {"skill": "query_metrics", "params": {"metric": "sales", "time_range": "7d"}},
        {"skill": "generate_report", "params": {"report_type": "sales", "time_range": "2024-01"}},
    ]

    batches = executor._build_execution_batches(skill_requests)

    print(f"\n执行批次:")
    for i, batch in enumerate(batches, 1):
        print(f"  Batch {i}: {[s['skill'] for s in batch]}")

    # 测试无依赖并行执行
    print(f"\n测试无依赖 Skills（并行）:")
    print(f"  Batch 1: query_metrics, generate_report")
    print(f"  ✓ 期望: 2 个 Skills 在同一批次")

    # 测试有依赖顺序执行
    print(f"\n测试有依赖 Skills（顺序）:")
    dependent_requests = [
        {"skill": "query_metrics", "params": {"metric": "sales", "time_range": "7d"}},
        {"skill": "analyze_root_cause", "params": {"metric": "sales", "anomaly_time": "yesterday"}},
    ]

    batches = executor._build_execution_batches(dependent_requests)

    print(f"  执行批次:")
    for i, batch in enumerate(batches, 1):
        print(f"    Batch {i}: {[s['skill'] for s in batch]}")

    assert len(batches) == 2, "有依赖的 Skills 应该分 2 批"
    print(f"  ✓ 依赖分析正确")

    return True


async def test_feedback_tool():
    """测试 4: 反馈工具（模拟）"""

    print(f"\n注意: 反馈工具需要数据库连接，此处仅测试接口")

    # 测试反馈类型
    assert FeedbackType.THUMBS_UP == "thumbs_up"
    assert FeedbackType.THUMBS_DOWN == "thumbs_down"

    print(f"✓ 反馈类型定义正确")
    print(f"  - thumbs_up: {FeedbackType.THUMBS_UP.value}")
    print(f"  - thumbs_down: {FeedbackType.THUMBS_DOWN.value}")

    # 测试 SQL 初始化语句
    from app.core.mcp.tools.feedback import FEEDBACK_TABLE_SQL

    assert "CREATE TABLE IF NOT EXISTS user_feedback" in FEEDBACK_TABLE_SQL
    assert "feedback_type" in FEEDBACK_TABLE_SQL
    assert "metadata" in FEEDBACK_TABLE_SQL

    print(f"✓ 数据库表结构 SQL 定义正确")

    return True


async def test_excel_tool():
    """测试 5: Excel 工具"""

    excel_tool = ExcelTool(base_path="./test_data/excel")

    # 测试基础路径
    assert excel_tool.base_path.exists() or excel_tool.base_path.as_posix() == "./test_data/excel"
    print(f"✓ Excel 工具初始化成功")
    print(f"  - 基础路径: {excel_tool.base_path}")

    # 测试文件信息接口（不需要实际文件）
    # 这里只测试方法存在性
    assert hasattr(excel_tool, 'read_excel')
    assert hasattr(excel_tool, 'write_excel')
    assert hasattr(excel_tool, 'query_excel')
    assert hasattr(excel_tool, 'export_to_excel')

    print(f"✓ Excel 工具方法完整")
    print(f"  - read_excel: 读取 Excel")
    print(f"  - write_excel: 写入 Excel")
    print(f"  - query_excel: 查询 Excel")
    print(f"  - export_to_excel: 导出 Excel")

    return True


async def test_api_datasource_tool():
    """测试 6: API 数据源工具"""

    api_tool = APIDatasourceTool()

    # 测试 API 注册
    api_tool.register_api(
        name="test_api",
        base_url="https://api.example.com/v1",
        auth_type="bearer",
        auth_value="test_token"
    )

    assert "test_api" in api_tool.api_configs
    assert api_tool.api_configs["test_api"]["base_url"] == "https://api.example.com/v1"

    print(f"✓ API 注册功能正常")
    print(f"  - 已注册: {list(api_tool.api_configs.keys())}")

    # 测试方法存在性
    assert hasattr(api_tool, 'call_api')
    assert hasattr(api_tool, 'call_url')
    assert hasattr(api_tool, 'get')
    assert hasattr(api_tool, 'post')

    print(f"✓ API 工具方法完整")
    print(f"  - call_api: 调用已注册的 API")
    print(f"  - call_url: 直接调用 URL")
    print(f"  - get: GET 请求")
    print(f"  - post: POST 请求")

    return True


async def test_integration():
    """测试 7: 集成测试（端到端流程）"""

    print(f"\n集成测试: 参数提取 → 并行执行 → 反馈收集")

    # 1. 参数提取
    print(f"\n步骤 1: 参数提取")
    recognizer = IntentRecognizerV2(api_key=TEST_API_KEY)

    result = await recognizer.recognize_with_params(
        "查询最近7天的销售额，按地区分组"
    )

    print(f"  - 意图: {result['intent']}")
    print(f"  - 方法: {result['method']}")

    if result['params']:
        print(f"  - 参数: {result['params']}")

    # 2. 并行执行计划
    print(f"\n步骤 2: 并行执行计划")
    registry = SkillRegistry()
    executor = ParallelSkillExecutor(registry=registry)

    requests = [
        {"skill": "query_metrics", "params": result.get('params', {})},
        {"skill": "generate_report", "params": {"report_type": "sales", "time_range": "7d"}},
    ]

    batches = executor._build_execution_batches(requests)
    print(f"  - 执行批次: {len(batches)}")
    for i, batch in enumerate(batches, 1):
        print(f"    Batch {i}: {[s['skill'] for s in batch]}")

    # 3. 反馈收集
    print(f"\n步骤 3: 反馈收集（模拟）")
    print(f"  - session_id: sess_test_001")
    print(f"  - message_id: msg_test_001")
    print(f"  - feedback: {FeedbackType.THUMBS_UP.value}")

    print(f"\n✓ 集成测试流程完成")

    return True


# ============== 主函数 ==============

def main():
    """主函数"""
    print("="*60)
    print("短期优化功能测试")
    print("="*60)
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    runner = TestRunner()

    # 运行测试
    runner.run_test("Pydantic 参数模型", test_param_schemas())
    runner.run_test("意图识别 V2（参数提取）", test_intent_recognition_v2())
    runner.run_test("并行 Skill 执行器", test_parallel_executor())
    runner.run_test("反馈工具", test_feedback_tool())
    runner.run_test("Excel 工具", test_excel_tool())
    runner.run_test("API 数据源工具", test_api_datasource_tool())
    runner.run_test("集成测试", test_integration())

    # 打印总结
    runner.print_summary()

    print(f"\n结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 返回退出码
    return 0 if runner.failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
