"""
Skills 基类抽象类

所有业务技能的抽象基类，定义统一的 Skill 接口
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from langchain_core.tools import StructuredTool


class SkillInput(BaseModel):
    """Skill 输入参数的基类"""
    pass


class SkillOutput(BaseModel):
    """Skill 输出结果的基类"""
    success: bool = Field(description="执行是否成功")
    data: Optional[Any] = Field(default=None, description="返回数据")
    error: Optional[str] = Field(default=None, description="错误信息")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")


class BaseSkill(ABC):
    """
    Skill 基类，所有业务技能必须继承此类

    提供统一的能力封装，支持：
    - 声明式定义（名称、描述、参数）
    - 可组合性（多个 Skill 组合完成复杂任务）
    - 上下文感知（访问会话状态和配置）
    - 可观测性（执行日志和性能追踪）
    """

    def __init__(self, mcp_client=None):
        """
        初始化 Skill

        Args:
            mcp_client: MCP 客户端（可选，用于调用 MCP 工具）
        """
        self.mcp_client = mcp_client
        self.name: str = self.__class__.__name__
        self.description: str = ""
        self.input_schema: type[SkillInput] = SkillInput

    @abstractmethod
    async def execute(
        self,
        input_data: SkillInput,
        context: Dict[str, Any]
    ) -> SkillOutput:
        """
        执行 Skill 的核心逻辑

        Args:
            input_data: 经过验证的输入参数
            context: 上下文信息（会话状态、用户信息等）

        Returns:
            SkillOutput: 执行结果
        """
        pass

    def to_langchain_tool(self) -> StructuredTool:
        """
        转换为 LangChain Tool 格式，供 LangGraph 使用

        Returns:
            StructuredTool: LangChain Tool 对象
        """
        return StructuredTool.from_function(
            func=self._wrapper,
            name=self.name,
            description=self.description,
            args_schema=self.input_schema
        )

    async def _wrapper(self, **kwargs) -> Dict[str, Any]:
        """
        内部包装器，处理 LangChain Tool 调用

        Args:
            **kwargs: Tool 参数

        Returns:
            Dict[str, Any]: 序列化的输出结果
        """
        try:
            # 验证输入参数
            input_data = self.input_schema(**kwargs)

            # 执行 Skill
            result = await self.execute(input_data, context={})

            # 返回序列化的结果
            return result.model_dump()

        except Exception as e:
            # 返回错误信息
            return SkillOutput(
                success=False,
                error=str(e)
            ).model_dump()
