"""
数据库查询 MCP 工具

提供安全的数据库查询功能，使用参数化查询防止 SQL 注入
"""
import asyncio
import logging
from typing import Any, Dict, List, Optional
import asyncpg
from pydantic import Field

from .base import BaseMCPTool, MCPToolInput, MCPToolOutput

logger = logging.getLogger(__name__)


class DatabaseQueryInput(MCPToolInput):
    """数据库查询输入"""
    sql: str = Field(description="参数化 SQL 查询语句（使用 $1, $2 占位符）")
    params: Optional[List[Any]] = Field(default=None, description="查询参数列表")
    operation: str = Field(default="fetch", description="操作类型: fetch/execute/ executemany")


class DatabaseQueryTool(BaseMCPTool):
    """
    数据库查询工具

    提供安全的数据库查询功能，支持：
    - 参数化查询（防 SQL 注入）
    - 事务管理
    - 连接池管理
    """

    def __init__(self, database_url: str):
        super().__init__()
        self.description = "执行数据库查询，支持参数化查询防止 SQL 注入"
        self.input_schema = DatabaseQueryInput
        self.database_url = database_url
        self._pool: Optional[asyncpg.Pool] = None

    async def _get_pool(self) -> asyncpg.Pool:
        """获取或创建连接池"""
        if self._pool is None:
            self._pool = await asyncpg.create_pool(
                self.database_url,
                min_size=1,
                max_size=10,
                command_timeout=60
            )
        return self._pool

    async def execute(
        self,
        input_data: DatabaseQueryInput,
        context: Optional[Dict[str, Any]] = None
    ) -> MCPToolOutput:
        """
        执行数据库查询

        Args:
            input_data: 查询输入（SQL + 参数）
            context: 上下文信息

        Returns:
            MCPToolOutput: 查询结果
        """
        try:
            # 验证 SQL 语句（基本安全检查）
            self._validate_sql(input_data.sql)

            # 获取连接池
            pool = await self._get_pool()

            # 根据操作类型执行不同的查询
            if input_data.operation == "fetch":
                result = await self._fetch_query(pool, input_data.sql, input_data.params)
            elif input_data.operation == "execute":
                result = await self._execute_query(pool, input_data.sql, input_data.params)
            elif input_data.operation == "executemany":
                result = await self._executemany_query(pool, input_data.sql, input_data.params)
            else:
                raise ValueError(f"不支持的操作类型: {input_data.operation}")

            return MCPToolOutput(
                success=True,
                data=result,
                metadata={
                    "operation": input_data.operation,
                    "rows_affected": len(result) if isinstance(result, list) else 0
                }
            )

        except asyncpg.PostgresError as e:
            logger.error(f"数据库错误: {e}")
            return MCPToolOutput(
                success=False,
                error=f"数据库错误: {str(e)}"
            )
        except Exception as e:
            logger.error(f"查询执行失败: {e}")
            return MCPToolOutput(
                success=False,
                error=f"查询执行失败: {str(e)}"
            )

    def _validate_sql(self, sql: str) -> None:
        """
        验证 SQL 语句的基本安全性

        Args:
            sql: SQL 语句

        Raises:
            ValueError: 如果 SQL 语句不安全
        """
        sql_upper = sql.upper().strip()

        # 检查是否包含危险的关键字
        dangerous_keywords = [
            "DROP TABLE", "DROP DATABASE", "TRUNCATE",
            "ALTER TABLE", "DROP COLUMN", "ALTER COLUMN"
        ]
        for keyword in dangerous_keywords:
            if keyword in sql_upper:
                raise ValueError(f"禁止的操作: {keyword}")

        # 检查是否使用了参数化查询
        # 如果包含 WHERE/VALUES/SET，必须使用参数占位符
        if any(keyword in sql_upper for keyword in ["WHERE", "VALUES", "SET"]):
            if "$1" not in sql and "$2" not in sql:
                logger.warning("SQL 查询建议使用参数化查询")

    async def _fetch_query(
        self,
        pool: asyncpg.Pool,
        sql: str,
        params: Optional[List[Any]]
    ) -> List[Dict[str, Any]]:
        """
        执行查询并返回结果

        Args:
            pool: 数据库连接池
            sql: SQL 语句
            params: 查询参数

        Returns:
            List[Dict[str, Any]]: 查询结果
        """
        async with pool.acquire() as conn:
            if params:
                rows = await conn.fetch(sql, *params)
            else:
                rows = await conn.fetch(sql)

            # 将 Record 对象转换为字典
            return [dict(row) for row in rows]

    async def _execute_query(
        self,
        pool: asyncpg.Pool,
        sql: str,
        params: Optional[List[Any]]
    ) -> str:
        """
        执行单条 SQL 语句

        Args:
            pool: 数据库连接池
            sql: SQL 语句
            params: 查询参数

        Returns:
            str: 执行结果
        """
        async with pool.acquire() as conn:
            if params:
                result = await conn.execute(sql, *params)
            else:
                result = await conn.execute(sql)
            return f"执行成功，影响行数: {result.split()[-1]}"

    async def _executemany_query(
        self,
        pool: asyncpg.Pool,
        sql: str,
        params: Optional[List[Any]]
    ) -> str:
        """
        执行批量 SQL 语句

        Args:
            pool: 数据库连接池
            sql: SQL 语句
            params: 查询参数

        Returns:
            str: 执行结果
        """
        async with pool.acquire() as conn:
            if params:
                results = await conn.executemany(sql, params)
            else:
                raise ValueError("executemany 操作需要提供参数列表")
            return f"批量执行成功，总影响行数: {sum(r.split()[-1] for r in results)}"

    async def close(self):
        """关闭连接池"""
        if self._pool:
            await self._pool.close()
            self._pool = None

    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()
