"""
Agent 状态定义

定义 LangGraph 状态机的状态结构
"""
from typing import List, Dict, Any, Optional, TypedDict
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from pydantic import BaseModel, Field


class AgentInput(BaseModel):
    """Agent 输入参数"""
    session_id: str = Field(description="会话 ID")
    message: str = Field(description="用户消息")
    context: Optional[Dict[str, Any]] = Field(default=None, description="额外上下文信息")


class AgentOutput(BaseModel):
    """Agent 输出结果"""
    success: bool = Field(description="执行是否成功")
    response: str = Field(description="最终回复消息")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")
    error: Optional[str] = Field(default=None, description="错误信息")


class SkillExecutionResult(BaseModel):
    """Skill 执行结果"""
    skill_name: str = Field(description="Skill 名称")
    success: bool = Field(description="执行是否成功")
    data: Any = Field(default=None, description="返回数据")
    error: Optional[str] = Field(default=None, description="错误信息")
    execution_time: float = Field(description="执行耗时（秒）")


class AgentState(TypedDict):
    """
    Agent 状态图的状态定义

    包含状态流转过程中的所有中间状态
    """
    # 输入
    session_id: str  # 会话 ID
    user_message: str  # 用户原始消息

    # 意图识别
    intent: Optional[str]  # 识别的意图: query_metrics, generate_report, analyze_root_cause, chat
    intent_confidence: float  # 意图识别置信度 (0-1)

    # Skill 执行
    selected_skills: List[str]  # 选择的 Skills 列表
    skill_results: List[SkillExecutionResult]  # Skill 执行结果列表

    # 消息历史 (用于 LLM 上下文)
    messages: List[BaseMessage]  # LangChain 消息列表

    # 输出
    final_response: Optional[str]  # 最终回复

    # 元数据
    metadata: Dict[str, Any]  # 执行元数据（时间戳、错误等）
