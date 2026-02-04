"""
用户反馈 API
提供反馈提交、查询和统计接口
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging

from app.core.mcp.tools.feedback import FeedbackTool, FeedbackType
from app.dependencies import get_feedback_tool, get_database_pool
import asyncpg

logger = logging.getLogger(__name__)

router = APIRouter()


# ============== Request/Response Models ==============

class FeedbackRequest(BaseModel):
    """反馈请求"""
    session_id: str = Field(..., description="会话 ID")
    message_id: str = Field(..., description="消息 ID（Agent 回复的唯一标识）")
    feedback_type: FeedbackType = Field(..., description="反馈类型：thumbs_up/thumbs_down")
    user_comment: Optional[str] = Field(None, max_length=1000, description="用户可选评论")
    metadata: Optional[Dict[str, Any]] = Field(None, description="额外元数据")


class FeedbackResponse(BaseModel):
    """反馈响应"""
    success: bool
    action: str = Field(..., description="操作类型：created/updated")
    session_id: str
    message_id: str
    feedback_type: str
    message: str


class FeedbackStatsResponse(BaseModel):
    """反馈统计响应"""
    total: int
    thumbs_up: int
    thumbs_down: int
    satisfaction_rate: float
    by_intent: Dict[str, Dict[str, int]]
    by_skill: Dict[str, Dict[str, int]]


class NegativeFeedbackItem(BaseModel):
    """负面反馈项"""
    session_id: str
    message_id: str
    user_comment: Optional[str]
    metadata: Dict[str, Any]
    created_at: datetime


# ============== API Endpoints ==============

@router.post("/", response_model=FeedbackResponse)
async def submit_feedback(
    request: FeedbackRequest,
    feedback_tool: FeedbackTool = Depends(get_feedback_tool)
):
    """
    提交用户反馈

    用户可以对 Agent 的回复进行点赞或点踩，帮助系统持续优化。

    **反馈类型：**
    - `thumbs_up`: 👍 满意
    - `thumbs_down`: 👎 不满意

    **元数据（metadata）通常包含：**
    - `intent`: 识别的意图
    - `skill_name`: 执行的 Skill
    - `params`: 使用的参数
    - `response`: Agent 的回复内容

    **示例：**
    ```json
    {
      "session_id": "sess_123",
      "message_id": "msg_456",
      "feedback_type": "thumbs_up",
      "user_comment": "回答很准确",
      "metadata": {
        "intent": "query_metrics",
        "skill_name": "query_metrics",
        "params": {"metric": "sales", "time_range": "7d"}
      }
    }
    ```
    """
    result = await feedback_tool.execute(
        session_id=request.session_id,
        message_id=request.message_id,
        feedback_type=request.feedback_type,
        user_comment=request.user_comment,
        metadata=request.metadata
    )

    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)

    return FeedbackResponse(
        success=True,
        action=result.data["action"],
        session_id=result.data["session_id"],
        message_id=result.data["message_id"],
        feedback_type=result.data["feedback_type"],
        message=result.message
    )


@router.get("/stats", response_model=FeedbackStatsResponse)
async def get_feedback_stats(
    session_id: Optional[str] = None,
    intent: Optional[str] = None,
    skill_name: Optional[str] = None,
    limit: int = 100,
    feedback_tool: FeedbackTool = Depends(get_feedback_tool)
):
    """
    获取反馈统计信息

    返回总体统计、按意图分组、按 Skill 分组的数据。

    **查询参数：**
    - `session_id`: 筛选指定会话的反馈
    - `intent`: 筛选指定意图的反馈
    - `skill_name`: 筛选指定 Skill 的反馈
    - `limit`: 返回结果数量（默认 100）

    **示例：**
    - `/api/v1/feedback/stats` - 总体统计
    - `/api/v1/feedback/stats?intent=query_metrics` - 查询指标的反馈统计
    - `/api/v1/feedback/stats?skill_name=QueryMetricsSkill` - 指定 Skill 的统计
    """
    result = await feedback_tool.get_feedback_stats(
        session_id=session_id,
        intent=intent,
        skill_name=skill_name,
        limit=limit
    )

    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)

    summary = result.data["summary"]

    return FeedbackStatsResponse(
        total=summary["total"],
        thumbs_up=summary["thumbs_up"],
        thumbs_down=summary["thumbs_down"],
        satisfaction_rate=summary["satisfaction_rate"],
        by_intent=result.data["by_intent"],
        by_skill=result.data["by_skill"]
    )


@router.get("/negative", response_model=List[NegativeFeedbackItem])
async def get_negative_feedback(
    limit: int = 50,
    intent: Optional[str] = None,
    feedback_tool: FeedbackTool = Depends(get_feedback_tool)
):
    """
    获取负面反馈列表

    返回最近的负面反馈（点踩），用于分析和优化。

    **查询参数：**
    - `limit`: 返回数量（默认 50）
    - `intent`: 筛选指定意图的负面反馈

    **用途：**
    - 分析用户不满意的原因
    - 优化 Prompt 和 Skill 选择策略
    - 发现系统性问题
    """
    result = await feedback_tool.get_negative_feedback(
        limit=limit,
        intent=intent
    )

    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)

    return [
        NegativeFeedbackItem(**item)
        for item in result.data["items"]
    ]


@router.get("/session/{session_id}")
async def get_session_feedback(
    session_id: str,
    feedback_tool: FeedbackTool = Depends(get_feedback_tool)
):
    """
    获取指定会话的所有反馈

    返回该会话中用户提交的所有反馈记录。

    **路径参数：**
    - `session_id`: 会话 ID

    **示例：**
    - `/api/v1/feedback/session/sess_abc123`
    """
    result = await feedback_tool.get_feedback_stats(
        session_id=session_id,
        limit=100
    )

    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)

    return {
        "session_id": session_id,
        "feedback_count": result.data["summary"]["total"],
        "feedbacks": result.data["recent_feedback"]
    }
