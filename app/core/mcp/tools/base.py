"""
MCP 工具基类

所有 MCP 工具的抽象基类，定义统一的工具接口
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class MCPToolInput(BaseModel):
    """MCP 工具输入参数的基类"""
    pass


class MCPToolOutput(BaseModel):
    """MCP 工具输出结果的基类"""
    success: bool = Field(description="执行是否成功")
    data: Optional[Any] = Field(default=None, description="返回数据")
    error: Optional[str] = Field(default=None, description="错误信息")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")


class BaseMCPTool(ABC):
    """
    MCP 工具基类

    所有 MCP 工具都必须继承此类并实现 execute 方法
    """

    def __init__(self):
        self.name: str = self.__class__.__name__
        self.description: str = ""
        self.input_schema: type[MCPToolInput] = MCPToolInput

    @abstractmethod
    async def execute(
        self,
        input_data: MCPToolInput,
        context: Optional[Dict[str, Any]] = None
    ) -> MCPToolOutput:
        """
        执行工具的核心逻辑

        Args:
            input_data: 经过验证的输入参数
            context: 上下文信息（会话状态、用户信息等）

        Returns:
            MCPToolOutput: 执行结果
        """
        pass

    def to_dict(self) -> Dict[str, Any]:
        """
        将工具转换为字典格式（用于工具注册）

        Returns:
            Dict[str, Any]: 工具的字典表示
        """
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema.model_json_schema()
        }
