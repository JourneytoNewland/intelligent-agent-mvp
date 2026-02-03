"""
聊天 API 端点

提供 Agent 聊天接口和 SSE 流式接口
"""
import logging
import uuid
import json
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.core.mcp.client import MCPClient
from app.core.skills.registry import SkillRegistry
from app.core.graph.intent import IntentRecognizer
from app.core.graph.agent import AgentGraph
from app.core.session import SessionManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


# 请求/响应模型
class ChatRequest(BaseModel):
    """聊天请求"""
    message: str = Field(..., description="用户消息", min_length=1, max_length=2000)
    session_id: Optional[str] = Field(None, description="会话 ID（可选，不提供则创建新会话）")
    stream: bool = Field(False, description="是否使用流式输出")


class ChatResponse(BaseModel):
    """聊天响应"""
    session_id: str = Field(..., description="会话 ID")
    response: str = Field(..., description="助手回复")
    intent: Optional[str] = Field(None, description="识别的意图")
    confidence: float = Field(..., description="意图识别置信度")
    skills_used: list = Field(default_factory=list, description="使用的 Skills")
    execution_time: float = Field(..., description="执行耗时（秒）")


class SessionInfo(BaseModel):
    """会话信息"""
    session_id: str
    message_count: int
    created_at: str
    updated_at: str


# 依赖注入
async def get_session_manager():
    """获取会话管理器"""
    # 简化实现：每次创建新实例
    # 生产环境应该使用单例
    return SessionManager()


async def get_agent_components():
    """获取 Agent 组件"""
    # 简化实现：每次创建新实例
    mcp_client = MCPClient()
    skill_registry = SkillRegistry(mcp_client=mcp_client)
    intent_recognizer = IntentRecognizer()
    agent = AgentGraph(
        skill_registry=skill_registry,
        intent_recognizer=intent_recognizer
    )
    return agent


@router.post("/", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    agent = Depends(get_agent_components),
    session_manager = Depends(get_session_manager)
):
    """
    聊天接口（非流式）

    处理用户消息并返回完整回复
    """
    try:
        logger.info(f"收到聊天请求: {request.message[:50]}...")

        # 生成或获取会话 ID
        session_id = request.session_id or f"session_{uuid.uuid4().hex}"

        # 如果是新会话，创建会话
        if not request.session_id:
            await session_manager.create_session(
                session_id=session_id,
                user_message=request.message
            )
        else:
            # 添加用户消息到现有会话
            await session_manager.add_user_message(
                session_id=session_id,
                user_message=request.message
            )

        # 执行 Agent
        result = await agent.run(
            session_id=session_id,
            user_message=request.message
        )

        # 更新会话
        await session_manager.update_session(
            session_id=session_id,
            assistant_message=result["final_response"],
            state_update={
                "last_intent": result["intent"],
                "last_confidence": result["intent_confidence"]
            }
        )

        # 构建响应
        response = ChatResponse(
            session_id=session_id,
            response=result["final_response"],
            intent=result["intent"],
            confidence=result["intent_confidence"],
            skills_used=result["selected_skills"],
            execution_time=result["metadata"].get("execution_time", 0.0)
        )

        logger.info(
            f"聊天完成: session={session_id}, "
            f"intent={result['intent']}, "
            f"time={response.execution_time:.2f}s"
        )

        return response

    except Exception as e:
        logger.error(f"聊天处理失败: {e}")
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")


@router.post("/stream")
async def chat_stream(
    request: ChatRequest,
    agent = Depends(get_agent_components),
    session_manager = Depends(get_session_manager)
):
    """
    聊天接口（SSE 流式）

    实时推送 Agent 执行过程
    """
    try:
        logger.info(f"收到流式聊天请求: {request.message[:50]}...")

        # 生成或获取会话 ID
        session_id = request.session_id or f"session_{uuid.uuid4().hex}"

        # 如果是新会话，创建会话
        if not request.session_id:
            await session_manager.create_session(
                session_id=session_id,
                user_message=request.message
            )
        else:
            # 添加用户消息到现有会话
            await session_manager.add_user_message(
                session_id=session_id,
                user_message=request.message
            )

        async def event_generator():
            """SSE 事件生成器"""
            try:
                # 发送会话 ID
                yield f"event: session\ndata: {json.dumps({'session_id': session_id})}\n\n"

                # 初始化状态
                initial_state = {
                    "session_id": session_id,
                    "user_message": request.message,
                    "intent": None,
                    "intent_confidence": 0.0,
                    "selected_skills": [],
                    "skill_results": [],
                    "messages": [],
                    "final_response": None,
                    "metadata": {}
                }

                # 流式执行 Agent
                async for event in agent.stream_events(
                    session_id=session_id,
                    user_message=request.message
                ):
                    # 发送状态更新事件
                    yield f"event: state_update\ndata: {json.dumps(event, default=str)}\n\n"

                # 获取最终结果（需要重新执行以获取完整状态）
                result = await agent.run(
                    session_id=session_id,
                    user_message=request.message
                )

                # 更新会话
                await session_manager.update_session(
                    session_id=session_id,
                    assistant_message=result["final_response"],
                    state_update={
                        "last_intent": result["intent"],
                        "last_confidence": result["intent_confidence"]
                    }
                )

                # 发送最终结果
                final_data = {
                    "session_id": session_id,
                    "response": result["final_response"],
                    "intent": result["intent"],
                    "confidence": result["intent_confidence"],
                    "skills_used": result["selected_skills"],
                    "execution_time": result["metadata"].get("execution_time", 0.0)
                }
                yield f"event: complete\ndata: {json.dumps(final_data, default=str)}\n\n"

                logger.info(f"流式聊天完成: session={session_id}")

            except Exception as e:
                logger.error(f"流式聊天处理失败: {e}")
                error_data = {"error": str(e)}
                yield f"event: error\ndata: {json.dumps(error_data)}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )

    except Exception as e:
        logger.error(f"流式聊天初始化失败: {e}")
        raise HTTPException(status_code=500, detail=f"初始化失败: {str(e)}")


@router.get("/sessions/{session_id}", response_model=SessionInfo)
async def get_session(
    session_id: str,
    session_manager = Depends(get_session_manager)
):
    """
    获取会话信息

    返回会话的基本信息（不包含完整消息历史）
    """
    try:
        session_data = await session_manager.get_session(session_id)

        if not session_data:
            raise HTTPException(status_code=404, detail="会话不存在")

        return SessionInfo(
            session_id=session_data["session_id"],
            message_count=session_data["message_count"],
            created_at=session_data["created_at"],
            updated_at=session_data["updated_at"]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取会话失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)}")


@router.get("/sessions/{session_id}/history")
async def get_session_history(
    session_id: str,
    limit: int = 10,
    session_manager = Depends(get_session_manager)
):
    """
    获取会话历史

    返回会话的消息历史
    """
    try:
        messages = await session_manager.get_session_history(
            session_id=session_id,
            limit=limit
        )

        return {
            "session_id": session_id,
            "message_count": len(messages),
            "messages": messages
        }

    except Exception as e:
        logger.error(f"获取会话历史失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)}")


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    session_manager = Depends(get_session_manager)
):
    """
    删除会话

    删除指定会话及其所有历史记录
    """
    try:
        success = await session_manager.delete_session(session_id)

        if not success:
            raise HTTPException(status_code=404, detail="会话不存在")

        return {
            "success": True,
            "message": f"会话 {session_id} 已删除"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除会话失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")


@router.get("/sessions")
async def list_sessions(
    limit: int = 100,
    session_manager = Depends(get_session_manager)
):
    """
    列出所有会话

    返回所有活跃会话的基本信息
    """
    try:
        sessions = await session_manager.list_sessions(limit=limit)

        # 只返回基本信息，不包含完整消息历史
        session_summaries = [
            {
                "session_id": s["session_id"],
                "message_count": s["message_count"],
                "created_at": s["created_at"],
                "updated_at": s["updated_at"]
            }
            for s in sessions
        ]

        return {
            "count": len(session_summaries),
            "sessions": session_summaries
        }

    except Exception as e:
        logger.error(f"列出会话失败: {e}")
        raise HTTPException(status_code=500, detail=f"列出失败: {str(e)}")
