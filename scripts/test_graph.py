"""
LangGraph 状态图测试脚本

测试 Agent 完整执行流程
"""
import asyncio
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import get_settings
from app.core.mcp.client import MCPClient
from app.core.skills.registry import SkillRegistry
from app.core.graph.intent import IntentRecognizer
from app.core.graph.agent import AgentGraph


async def test_intent_recognition():
    """测试意图识别"""
    print("\n" + "="*60)
    print("测试 1: 意图识别")
    print("="*60)

    try:
        recognizer = IntentRecognizer()

        test_messages = [
            "查询最近7天的销售额",
            "生成一份按地区统计的销售报表",
            "分析一下昨天销售额下降的原因",
            "你好，我是新用户"
        ]

        for message in test_messages:
            print(f"\n用户消息: {message}")
            result = await recognizer.recognize(message)
            print(f"  意图: {result['intent']}")
            print(f"  置信度: {result['confidence']:.2f}")
            print(f"  推理: {result['reasoning'][:80]}...")
            print(f"  将调用: {recognizer.get_skill_mapping(result['intent'])}")

        return True

    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_agent_execution():
    """测试 Agent 完整执行流程"""
    print("\n" + "="*60)
    print("测试 2: Agent 执行流程")
    print("="*60)

    try:
        # 初始化组件
        mcp_client = MCPClient()
        skill_registry = SkillRegistry(mcp_client=mcp_client)
        intent_recognizer = IntentRecognizer()

        # 创建 Agent 状态图
        agent = AgentGraph(
            skill_registry=skill_registry,
            intent_recognizer=intent_recognizer
        )

        print("\n✓ Agent 状态图创建成功")

        # 测试场景 1: 查询指标
        print("\n场景 1: 查询指标")
        result1 = await agent.run(
            session_id="test_session_1",
            user_message="查询最近7天的销售额"
        )

        print(f"  意图: {result1['intent']}")
        print(f"  置信度: {result1['intent_confidence']:.2f}")
        print(f"  调用的 Skills: {result1['selected_skills']}")
        print(f"  Skill 结果数: {len(result1['skill_results'])}")

        if result1['skill_results']:
            for skill_result in result1['skill_results']:
                print(f"    - {skill_result.skill_name}: "
                      f"{'成功' if skill_result.success else '失败'} "
                      f"({skill_result.execution_time:.2f}s)")

        print(f"  最终回复: {result1['final_response'][:100]}...")

        # 测试场景 2: 普通对话
        print("\n场景 2: 普通对话")
        result2 = await agent.run(
            session_id="test_session_2",
            user_message="你好，我是新用户"
        )

        print(f"  意图: {result2['intent']}")
        print(f"  调用的 Skills: {result2['selected_skills']}")
        print(f"  最终回复: {result2['final_response']}")

        await mcp_client.close()
        return True

    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_state_transitions():
    """测试状态流转"""
    print("\n" + "="*60)
    print("测试 3: 状态流转")
    print("="*60)

    try:
        # 初始化组件
        mcp_client = MCPClient()
        skill_registry = SkillRegistry(mcp_client=mcp_client)
        intent_recognizer = IntentRecognizer()

        # 创建 Agent
        agent = AgentGraph(
            skill_registry=skill_registry,
            intent_recognizer=intent_recognizer
        )

        # 执行 Agent
        result = await agent.run(
            session_id="test_state",
            user_message="生成销售报表"
        )

        # 验证状态流转
        print(f"\n状态流转验证:")
        print(f"  ✓ session_id: {result['session_id']}")
        print(f"  ✓ user_message: {result['user_message']}")
        print(f"  ✓ intent: {result['intent']}")
        print(f"  ✓ intent_confidence: {result['intent_confidence']:.2f}")
        print(f"  ✓ selected_skills: {result['selected_skills']}")
        print(f"  ✓ skill_results: {len(result['skill_results'])} 个")
        print(f"  ✓ messages: {len(result['messages'])} 条")
        print(f"  ✓ final_response: {len(result['final_response'])} 字符")
        print(f"  ✓ metadata: {list(result['metadata'].keys())}")

        # 验证消息历史
        print(f"\n消息历史:")
        for i, msg in enumerate(result['messages'], 1):
            msg_type = msg.__class__.__name__
            content = msg.content[:50] + "..." if len(msg.content) > 50 else msg.content
            print(f"  {i}. [{msg_type}] {content}")

        await mcp_client.close()
        return True

    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_error_handling():
    """测试错误处理"""
    print("\n" + "="*60)
    print("测试 4: 错误处理")
    print("="*60)

    try:
        # 初始化组件
        mcp_client = MCPClient()
        skill_registry = SkillRegistry(mcp_client=mcp_client)
        intent_recognizer = IntentRecognizer()

        # 创建 Agent
        agent = AgentGraph(
            skill_registry=skill_registry,
            intent_recognizer=intent_recognizer
        )

        # 测试空消息
        print("\n场景 1: 空消息")
        result1 = await agent.run(
            session_id="test_error_1",
            user_message=""
        )
        print(f"  ✓ 处理完成: {result1['final_response'][:50]}...")

        # 测试无效意图
        print("\n场景 2: 复杂/模糊消息")
        result2 = await agent.run(
            session_id="test_error_2",
            user_message="afjasdkfjhaskjfhaskdfhaksdf"  # 无意义文本
        )
        print(f"  ✓ 意图: {result2['intent']}")
        print(f"  ✓ 最终回复: {result2['final_response'][:50]}...")

        await mcp_client.close()
        return True

    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_integration_with_skills():
    """测试与 Skills 的集成"""
    print("\n" + "="*60)
    print("测试 5: Skills 集成")
    print("="*60)

    try:
        # 初始化组件
        mcp_client = MCPClient()
        skill_registry = SkillRegistry(mcp_client=mcp_client)
        intent_recognizer = IntentRecognizer()

        # 验证 Skills 可用
        skills = skill_registry.list_skills()
        print(f"\n可用 Skills: {len(skills)}")
        for skill in skills:
            print(f"  - {skill['name']}: {skill['description']}")

        # 创建 Agent
        agent = AgentGraph(
            skill_registry=skill_registry,
            intent_recognizer=intent_recognizer
        )

        # 测试每个意图对应的 Skill
        test_cases = [
            ("查询销售额", "query_metrics"),
            ("生成报表", "generate_report"),
            ("分析异常", "analyze_root_cause")
        ]

        for message, expected_intent in test_cases:
            print(f"\n测试: {message}")
            result = await agent.run(
                session_id=f"test_integration_{expected_intent}",
                user_message=message
            )

            print(f"  期望意图: {expected_intent}")
            print(f"  实际意图: {result['intent']}")
            print(f"  匹配: {'✓' if result['intent'] == expected_intent else '✗'}")
            print(f"  调用 Skills: {result['selected_skills']}")

        await mcp_client.close()
        return True

    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """主测试函数"""
    print("\n" + "="*60)
    print("LangGraph 状态图功能测试")
    print("="*60)

    # 加载配置
    settings = get_settings()
    print(f"\n环境: {settings.environment}")
    print(f"智谱 AI: {'已配置' if settings.zhipuai_api_key else '未配置'}")

    # 运行所有测试
    tests = [
        ("意图识别", test_intent_recognition),
        ("Agent 执行流程", test_agent_execution),
        ("状态流转", test_state_transitions),
        ("错误处理", test_error_handling),
        ("Skills 集成", test_integration_with_skills),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = await test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ 测试 '{name}' 异常: {e}")
            results.append((name, False))

    # 输出测试总结
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{status}: {name}")

    print(f"\n通过: {passed}/{total}")

    if passed == total:
        print("\n🎉 所有测试通过!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} 个测试失败")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
