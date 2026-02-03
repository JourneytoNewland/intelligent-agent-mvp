"""
依赖注入模块

管理应用的核心依赖，如数据库连接池、Redis 客户端等
"""
from typing import AsyncGenerator
import asyncpg
from redis.asyncio import Redis as AsyncRedis
from app.config import settings, Settings

# Langfuse 是可选的（MVP 阶段不需要，与 Pydantic v2 冲突）
try:
    from langfuse import Langfuse
    LANGFUSE_AVAILABLE = True
except ImportError:
    LANGFUSE_AVAILABLE = False


# ========== 数据库连接池 ==========

async def get_database_pool() -> AsyncGenerator[asyncpg.Pool, None]:
    """
    获取数据库连接池（依赖注入用）

    Yields:
        asyncpg.Pool: 数据库连接池
    """
    pool: asyncpg.Pool = await asyncpg.create_pool(
        settings.database_url,
        min_size=2,
        max_size=settings.database_pool_size,
        command_timeout=60
    )

    try:
        yield pool
    finally:
        await pool.close()


# ========== Redis 客户端 ==========

async def get_redis_client() -> AsyncGenerator[AsyncRedis, None]:
    """
    获取 Redis 客户端（依赖注入用）

    Yields:
        AsyncRedis: Redis 客户端
    """
    redis_client: AsyncRedis = AsyncRedis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
        max_connections=settings.redis_max_connections
    )

    try:
        yield redis_client
    finally:
        await redis_client.close()


# ========== Langfuse 客户端（可选） ==========

def get_langfuse_client():
    """
    获取 Langfuse 客户端（依赖注入用）

    Returns:
        Langfuse | None: Langfuse 客户端，如果未配置或不可用则返回 None
    """
    if not LANGFUSE_AVAILABLE:
        return None

    if not settings.langfuse_public_key or not settings.langfuse_secret_key:
        return None

    return Langfuse(
        public_key=settings.langfuse_public_key,
        secret_key=settings.langfuse_secret_key,
        host=settings.langfuse_host,
        debug=settings.debug
    )


# ========== 配置实例 ==========

def get_config() -> Settings:
    """
    获取配置实例（依赖注入用）

    Returns:
        Settings: 配置实例
    """
    return settings
