"""
API 功能测试脚本

测试 FastAPI 聊天接口的所有端点
"""
import asyncio
import sys
import httpx
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

BASE_URL = "http://localhost:8000/api/v1"


async def test_health_check():
    """测试健康检查"""
    print("\n" + "="*60)
    print("测试 1: 健康检查")
    print("="*60)

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/health")
            print(f"\n状态码: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print(f"✓ 健康检查通过")
                print(f"  状态: {data.get('status')}")
                print(f"  数据库: {data.get('checks', {}).get('database', {}).get('status')}")
                print(f"  Redis: {data.get('checks', {}).get('redis', {}).get('status')}")
                return True
            else:
                print(f"✗ 健康检查失败")
                return False

    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        return False


async def test_chat_simple():
    """测试简单聊天（非流式）"""
    print("\n" + "="*60)
    print("测试 2: 简单聊天")
    print("="*60)

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            # 测试消息
            request_data = {
                "message": "你好，我是新用户",
                "stream": False
            }

            print(f"\n发送消息: {request_data['message']}")

            response = await client.post(
                f"{BASE_URL}/chat/",
                json=request_data
            )

            print(f"\n状态码: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print(f"✓ 聊天成功")
                print(f"  会话 ID: {data['session_id']}")
                print(f"  意图: {data['intent']}")
                print(f"  置信度: {data['confidence']:.2f}")
                print(f"  使用的 Skills: {data['skills_used']}")
                print(f"  执行时间: {data['execution_time']:.2f}s")
                print(f"  回复: {data['response'][:100]}...")

                # 保存 session_id 用于后续测试
                return data['session_id']
            else:
                print(f"✗ 聊天失败: {response.text}")
                return None

    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_chat_with_session(session_id: str):
    """测试多轮对话（使用现有会话）"""
    print("\n" + "="*60)
    print("测试 3: 多轮对话")
    print("="*60)

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            request_data = {
                "message": "查询最近7天的销售额",
                "session_id": session_id,
                "stream": False
            }

            print(f"\n发送消息: {request_data['message']}")
            print(f"使用会话: {session_id}")

            response = await client.post(
                f"{BASE_URL}/chat/",
                json=request_data
            )

            print(f"\n状态码: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print(f"✓ 多轮对话成功")
                print(f"  意图: {data['intent']}")
                print(f"  使用的 Skills: {data['skills_used']}")
                print(f"  回复: {data['response'][:100]}...")
                return True
            else:
                print(f"✗ 多轮对话失败: {response.text}")
                return False

    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_session_info(session_id: str):
    """测试获取会话信息"""
    print("\n" + "="*60)
    print("测试 4: 获取会话信息")
    print("="*60)

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/chat/sessions/{session_id}")

            print(f"\n状态码: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print(f"✓ 获取会话信息成功")
                print(f"  会话 ID: {data['session_id']}")
                print(f"  消息数量: {data['message_count']}")
                print(f"  创建时间: {data['created_at']}")
                print(f"  更新时间: {data['updated_at']}")
                return True
            else:
                print(f"✗ 获取会话信息失败: {response.text}")
                return False

    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        return False


async def test_session_history(session_id: str):
    """测试获取会话历史"""
    print("\n" + "="*60)
    print("测试 5: 获取会话历史")
    print("="*60)

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BASE_URL}/chat/sessions/{session_id}/history?limit=10"
            )

            print(f"\n状态码: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print(f"✓ 获取会话历史成功")
                print(f"  总消息数: {data['message_count']}")
                print(f"  返回消息数: {len(data['messages'])}")

                print(f"\n最近的消息:")
                for i, msg in enumerate(data['messages'], 1):
                    role = msg['role']
                    content = msg['content'][:50] + "..." if len(msg['content']) > 50 else msg['content']
                    print(f"  {i}. [{role}] {content}")

                return True
            else:
                print(f"✗ 获取会话历史失败: {response.text}")
                return False

    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        return False


async def test_streaming_chat():
    """测试流式聊天"""
    print("\n" + "="*60)
    print("测试 6: 流式聊天 (SSE)")
    print("="*60)

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            request_data = {
                "message": "生成销售报表",
                "stream": True
            }

            print(f"\n发送消息: {request_data['message']}")

            async with client.stream(
                "POST",
                f"{BASE_URL}/chat/stream",
                json=request_data,
                headers={"Accept": "text/event-stream"}
            ) as response:
                print(f"\n状态码: {response.status_code}")

                if response.status_code == 200:
                    print(f"✓ 开始接收流式数据\n")

                    event_count = 0
                    async for line in response.aiter_lines():
                        if line:
                            if line.startswith("event:"):
                                event_type = line[6:].strip()
                                print(f"[Event: {event_type}]")
                            elif line.startswith("data:"):
                                data = line[5:].strip()
                                print(f"  {data[:100]}...")
                                event_count += 1

                    print(f"\n✓ 流式聊天完成，接收 {event_count} 个事件")
                    return True
                else:
                    # 读取错误响应
                    error_text = await response.aread()
                    error_text = error_text.decode('utf-8')
                    print(f"✗ 流式聊天失败: {error_text}")
                    return False

    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_list_sessions():
    """测试列出所有会话"""
    print("\n" + "="*60)
    print("测试 7: 列出所有会话")
    print("="*60)

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/chat/sessions?limit=10")

            print(f"\n状态码: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print(f"✓ 列出会话成功")
                print(f"  会话总数: {data['count']}")

                if data['sessions']:
                    print(f"\n会话列表:")
                    for session in data['sessions'][:5]:
                        print(f"  - {session['session_id']}: "
                              f"{session['message_count']} 条消息, "
                              f"更新于 {session['updated_at']}")
                return True
            else:
                print(f"✗ 列出会话失败: {response.text}")
                return False

    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        return False


async def test_delete_session(session_id: str):
    """测试删除会话"""
    print("\n" + "="*60)
    print("测试 8: 删除会话")
    print("="*60)

    try:
        async with httpx.AsyncClient() as client:
            response = await client.delete(f"{BASE_URL}/chat/sessions/{session_id}")

            print(f"\n状态码: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print(f"✓ 删除会话成功")
                print(f"  {data['message']}")
                return True
            else:
                print(f"✗ 删除会话失败: {response.text}")
                return False

    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        return False


async def main():
    """主测试函数"""
    print("\n" + "="*60)
    print("FastAPI 聊天接口功能测试")
    print("="*60)

    print(f"\nAPI 基础 URL: {BASE_URL}")
    print("请确保 FastAPI 应用正在运行: uvicorn app.main:app --reload")

    # 等待用户确认
    input("\n按 Enter 键开始测试...")

    # 运行所有测试
    tests = [
        ("健康检查", test_health_check),
        ("简单聊天", test_chat_simple),
        ("多轮对话", test_chat_with_session),  # 需要上一个测试返回 session_id
        ("获取会话信息", test_session_info),
        ("获取会话历史", test_session_history),
        ("流式聊天", test_streaming_chat),
        ("列出所有会话", test_list_sessions),
        ("删除会话", test_delete_session),
    ]

    results = []
    session_id = None

    for name, test_func in tests:
        try:
            if name in ["多轮对话", "获取会话信息", "获取会话历史", "删除会话"]:
                # 这些测试需要 session_id
                if session_id is None:
                    print(f"\n⚠️  跳过测试 '{name}'（需要 session_id）")
                    continue
                result = await test_func(session_id)
            else:
                result = await test_func()

            if name == "简单聊天" and isinstance(result, str):
                # 保存 session_id
                session_id = result
                results.append((name, True))
            else:
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
