"""
Pytest 配置文件

定义测试 fixtures 和通用测试配置
"""
import pytest
import asyncio
from typing import AsyncGenerator, Generator
import os
import sys

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """
    创建事件循环（session 级别）

    Yields:
        asyncio.AbstractEventLoop: 事件循环
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def test_config():
    """
    测试配置 fixture

    Returns:
        Settings: 测试环境配置
    """
    from app.config import Settings

    # 设置测试环境变量
    os.environ["ENVIRONMENT"] = "testing"
    os.environ["DEBUG"] = "true"
    os.environ["DATABASE_URL"] = "postgresql://postgres:postgres123@localhost:5432/agent_db_test"
    os.environ["REDIS_URL"] = "redis://localhost:6379/1"

    return Settings()


@pytest.fixture
async def test_database_pool(test_config):
    """
    测试数据库连接池 fixture

    Args:
        test_config: 测试配置

    Yields:
        asyncpg.Pool: 数据库连接池
    """
    import asyncpg

    pool = await asyncpg.create_pool(
        test_config.database_url,
        min_size=1,
        max_size=5
    )

    yield pool

    await pool.close()


@pytest.fixture
async def test_redis_client(test_config):
    """
    测试 Redis 客户端 fixture

    Args:
        test_config: 测试配置

    Yields:
        AsyncRedis: Redis 客户端
    """
    from redis.asyncio import Redis as AsyncRedis

    redis_client = AsyncRedis.from_url(
        test_config.redis_url,
        encoding="utf-8",
        decode_responses=True
    )

    yield redis_client

    await redis_client.close()


@pytest.fixture
def mock_llm_response():
    """
    Mock LLM 响应 fixture

    Returns:
        str: Mock 的 LLM 响应
    """
    return "这是一个测试响应"


# Pytest 配置
def pytest_configure(config):
    """Pytest 配置"""
    config.addinivalue_line(
        "markers", "unit: 单元测试标记"
    )
    config.addinivalue_line(
        "markers", "integration: 集成测试标记"
    )
    config.addinivalue_line(
        "markers", "e2e: 端到端测试标记"
    )
    config.addinivalue_line(
        "markers", "slow: 慢速测试标记"
    )
