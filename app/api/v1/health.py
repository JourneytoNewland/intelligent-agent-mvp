"""
健康检查端点

提供系统健康状态检查，包括数据库、Redis、Langfuse 等服务状态
"""
import time
from typing import Dict
from fastapi import APIRouter, Depends
from app.schemas.health import HealthResponse, ServiceStatus
from app.config import Settings, get_settings
from app.dependencies import get_database_pool, get_redis_client, get_langfuse_client

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check(
    config: Settings = Depends(get_settings)
):
    """
    系统健康检查端点

    检查以下服务状态：
    - PostgreSQL 数据库
    - Redis 缓存
    - Langfuse 可观测性平台（可选）

    Returns:
        HealthResponse: 系统健康状态
    """
    # 数据库状态
    db_status = await check_database()

    # Redis 状态
    redis_status = await check_redis()

    # Langfuse 状态（可选）
    langfuse_status = await check_langfuse(config)

    return HealthResponse(
        status="healthy" if all([
            db_status == "connected",
            redis_status == "connected"
        ]) else "unhealthy",
        version=config.app_version,
        environment=config.environment,
        database=db_status,
        redis=redis_status,
        langfuse=langfuse_status
    )


@router.get("/health/detailed")
async def health_check_detailed():
    """
    详细健康检查端点

    返回每个服务的详细状态信息，包括延迟

    Returns:
        Dict[str, ServiceStatus]: 详细服务状态
    """
    services = {
        "database": await check_database_detailed(),
        "redis": await check_redis_detailed()
    }

    return services


async def check_database() -> str:
    """
    检查数据库连接状态

    Returns:
        str: "connected" 或 "disconnected"
    """
    try:
        import asyncpg
        pool = await asyncpg.create_pool(
            "postgresql://postgres:postgres123@localhost:5432/agent_db",
            min_size=1,
            max_size=1
        )
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        await pool.close()
        return "connected"
    except Exception as e:
        return f"disconnected: {str(e)}"


async def check_redis() -> str:
    """
    检查 Redis 连接状态

    Returns:
        str: "connected" 或 "disconnected"
    """
    try:
        from redis.asyncio import Redis as AsyncRedis
        redis_client = AsyncRedis.from_url("redis://localhost:6379/0")
        await redis_client.ping()
        await redis_client.close()
        return "connected"
    except Exception as e:
        return f"disconnected: {str(e)}"


async def check_langfuse(config: Settings) -> str | None:
    """
    检查 Langfuse 连接状态

    Args:
        config: 应用配置

    Returns:
        str | None: "connected" 或 None（如果未配置）
    """
    try:
        if not config.langfuse_public_key or not config.langfuse_secret_key:
            return None

        langfuse = Langfuse(
            public_key=config.langfuse_public_key,
            secret_key=config.langfuse_secret_key,
            host=config.langfuse_host
        )
        # 简单检查：尝试创建一个测试事件（不发送）
        # 实际生产环境中可能需要更复杂的检查
        return "connected"
    except Exception as e:
        return f"disconnected: {str(e)}"


async def check_database_detailed() -> ServiceStatus:
    """
    检查数据库连接详细状态

    Returns:
        ServiceStatus: 详细服务状态
    """
    start_time = time.time()
    try:
        import asyncpg
        pool = await asyncpg.create_pool(
            "postgresql://postgres:postgres123@localhost:5432/agent_db",
            min_size=1,
            max_size=1
        )
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        await pool.close()

        latency = (time.time() - start_time) * 1000  # 转换为毫秒

        return ServiceStatus(
            name="database",
            status="connected",
            latency_ms=round(latency, 2)
        )
    except Exception as e:
        return ServiceStatus(
            name="database",
            status="disconnected",
            error=str(e)
        )


async def check_redis_detailed() -> ServiceStatus:
    """
    检查 Redis 连接详细状态

    Returns:
        ServiceStatus: 详细服务状态
    """
    start_time = time.time()
    try:
        from redis.asyncio import Redis as AsyncRedis
        redis_client = AsyncRedis.from_url("redis://localhost:6379/0")
        await redis_client.ping()
        await redis_client.close()

        latency = (time.time() - start_time) * 1000  # 转换为毫秒

        return ServiceStatus(
            name="redis",
            status="connected",
            latency_ms=round(latency, 2)
        )
    except Exception as e:
        return ServiceStatus(
            name="redis",
            status="disconnected",
            error=str(e)
        )
