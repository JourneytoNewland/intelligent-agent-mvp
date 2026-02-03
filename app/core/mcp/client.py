"""
MCP 客户端

提供简化的工具调用接口，供 Skills 层使用
"""
import logging
from typing import Any, Dict, List, Optional
from app.config import settings
from app.core.mcp.tools.database import DatabaseQueryTool
from app.core.mcp.tools.http_client import HttpRequestTool

logger = logging.getLogger(__name__)


class MCPClient:
    """
    MCP 客户端

    提供统一的工具调用接口，隐藏 MCP 协议的复杂性
    """

    def __init__(self, database_url: Optional[str] = None):
        """
        初始化 MCP 客户端

        Args:
            database_url: 数据库连接 URL（可选，默认从配置读取）
        """
        self.database_url = database_url or settings.database_url
        self.tools: Dict[str, Any] = {}

        # 注册工具
        self._register_tools()

    def _register_tools(self):
        """注册所有可用的 MCP 工具"""
        # 数据库查询工具
        self.tools["database_query"] = DatabaseQueryTool(self.database_url)

        # HTTP 请求工具
        self.tools["http_request"] = HttpRequestTool()

        logger.info(f"已注册 {len(self.tools)} 个 MCP 工具: {list(self.tools.keys())}")

    async def call_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any]
    ) -> MCPToolOutput:
        """
        调用 MCP 工具

        Args:
            tool_name: 工具名称
            parameters: 工具参数

        Returns:
            MCPToolOutput: 工具执行结果

        Raises:
            ValueError: 如果工具不存在
        """
        if tool_name not in self.tools:
            raise ValueError(f"工具不存在: {tool_name}。可用工具: {list(self.tools.keys())}")

        tool = self.tools[tool_name]

        # 将参数转换为工具的输入 schema
        try:
            input_data = tool.input_schema(**parameters)
        except Exception as e:
            logger.error(f"参数验证失败: {e}")
            return MCPToolOutput(
                success=False,
                error=f"参数验证失败: {str(e)}"
            )

        # 执行工具
        logger.info(f"调用工具: {tool_name}, 参数: {parameters}")
        result = await tool.execute(input_data)

        return result

    def list_tools(self) -> List[Dict[str, Any]]:
        """
        列出所有可用的工具

        Returns:
            List[Dict[str, Any]]: 工具列表
        """
        return [tool.to_dict() for tool in self.tools.values()]

    async def close(self):
        """关闭所有工具的连接"""
        for tool in self.tools.values():
            if hasattr(tool, 'close'):
                await tool.close()
        logger.info("MCP 客户端已关闭")

    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()
