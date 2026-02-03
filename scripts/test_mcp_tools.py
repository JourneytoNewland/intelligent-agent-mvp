#!/usr/bin/env python3
"""
MCP 工具测试脚本

验证 MCP 工具的基本功能
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.mcp.client import MCPClient


async def test_database_tool():
    """测试数据库查询工具"""
    print("\n" + "="*60)
    print("🔍 测试数据库查询工具")
    print("="*60)

    async with MCPClient() as client:
        # 测试 1: 简单查询
        print("\n测试 1: 查询地区数据")
        result = await client.call_tool(
            "database_query",
            {
                "sql": "SELECT * FROM dim_regions LIMIT 3",
                "operation": "fetch"
            }
        )

        if result.success:
            print(f"✅ 查询成功，返回 {len(result.data)} 条记录")
            for row in result.data[:2]:
                print(f"   - {row}")
        else:
            print(f"❌ 查询失败: {result.error}")

        # 测试 2: 参数化查询
        print("\n测试 2: 参数化查询（防注入）")
        result = await client.call_tool(
            "database_query",
            {
                "sql": "SELECT * FROM dim_regions WHERE id = $1",
                "params": [1],
                "operation": "fetch"
            }
        )

        if result.success:
            print(f"✅ 参数化查询成功: {result.data}")
        else:
            print(f"❌ 参数化查询失败: {result.error}")

        # 测试 3: SQL 注入防护
        print("\n测试 3: SQL 注入防护")
        result = await client.call_tool(
            "database_query",
            {
                "sql": "SELECT * FROM dim_regions WHERE name = $1",
                "params": ["'; DROP TABLE dim_regions; --"],
                "operation": "fetch"
            }
        )

        if result.success:
            print(f"✅ 安全，参数正确转义: {result.data}")
        else:
            print(f"❌ 查询失败: {result.error}")


async def test_http_tool():
    """测试 HTTP 请求工具"""
    print("\n" + "="*60)
    print("🌐 测试 HTTP 请求工具")
    print("="*60)

    async with MCPClient() as client:
        # 测试 1: GET 请求
        print("\n测试 1: GET 请求（httpbin.org）")
        result = await client.call_tool(
            "http_request",
            {
                "url": "https://httpbin.org/get",
                "method": "GET",
                "timeout": 10.0
            }
        )

        if result.success:
            print(f"✅ GET 请求成功")
            print(f"   状态码: {result.metadata.get('status_code')}")
            print(f"   URL: {result.metadata.get('url')}")
        else:
            print(f"❌ GET 请求失败: {result.error}")

        # 测试 2: POST 请求
        print("\n测试 2: POST 请求")
        result = await client.call_tool(
            "http_request",
            {
                "url": "https://httpbin.org/post",
                "method": "POST",
                "headers": {"Content-Type": "application/json"},
                "body": '{"test": "data"}',
                "timeout": 10.0
            }
        )

        if result.success:
            print(f"✅ POST 请求成功")
            print(f"   状态码: {result.metadata.get('status_code')}")
        else:
            print(f"❌ POST 请求失败: {result.error}")


async def test_list_tools():
    """测试列出工具"""
    print("\n" + "="*60)
    print("📋 测试列出可用工具")
    print("="*60)

    async with MCPClient() as client:
        tools = client.list_tools()

        print(f"\n可用工具数量: {len(tools)}")
        for tool in tools:
            print(f"\n🔧 {tool['name']}")
            print(f"   描述: {tool['description']}")
            print(f"   参数: {tool['input_schema']['title'] if 'title' in tool['input_schema'] else '...'}")


async def main():
    """主测试流程"""
    print("="*60)
    print("🧪 MCP 工具功能测试")
    print("="*60)

    try:
        # 测试列出工具
        await test_list_tools()

        # 测试数据库工具
        await test_database_tool()

        # 测试 HTTP 工具
        await test_http_tool()

        print("\n" + "="*60)
        print("✅ 所有测试完成")
        print("="*60)

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
