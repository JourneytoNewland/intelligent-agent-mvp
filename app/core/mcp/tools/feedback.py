"""
用户反馈 MCP 工具
收集用户对 Agent 回复的反馈（👍/👎），用于持续优化
"""

import asyncpg
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging
from enum import Enum

from app.core.mcp.tools.base import BaseMCPTool, MCPToolOutput as ToolResult

logger = logging.getLogger(__name__)


class FeedbackType(str, Enum):
    """反馈类型"""
    THUMBS_UP = "thumbs_up"    # 👍
    THUMBS_DOWN = "thumbs_down"  # 👎


class FeedbackTool(BaseMCPTool):
    """
    用户反馈工具

    功能：
    1. 记录用户对 Agent 回复的反馈
    2. 存储反馈元数据（意图、Skill、参数等）
    3. 支持反馈统计和分析
    4. 为后续优化提供数据支持
    """

    name = "feedback"
    description = "记录用户对 Agent 回复的反馈（点赞/点踩）"

    def __init__(self, db_pool: asyncpg.Pool):
        super().__init__()
        self.db_pool = db_pool

    async def execute(
        self,
        session_id: str,
        message_id: str,
        feedback_type: FeedbackType,
        user_comment: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ToolResult:
        """
        记录用户反馈

        Args:
            session_id: 会话 ID
            message_id: 消息 ID（Agent 回复的唯一标识）
            feedback_type: 反馈类型（thumbs_up/thumbs_down）
            user_comment: 用户可选的评论
            metadata: 额外元数据（意图、Skill、参数等）

        Returns:
            ToolResult: 反馈记录结果
        """
        try:
            async with self.db_pool.acquire() as conn:
                # 检查是否已存在反馈（允许修改）
                existing = await conn.fetchrow(
                    """
                    SELECT id, feedback_type FROM user_feedback
                    WHERE session_id = $1 AND message_id = $2
                    """,
                    session_id, message_id
                )

                if existing:
                    # 更新现有反馈
                    await conn.execute(
                        """
                        UPDATE user_feedback
                        SET feedback_type = $1,
                            user_comment = $2,
                            metadata = $3,
                            updated_at = $4
                        WHERE session_id = $5 AND message_id = $6
                        """,
                        feedback_type.value,
                        user_comment,
                        metadata or {},
                        datetime.now(),
                        session_id,
                        message_id
                    )

                    logger.info(
                        f"更新反馈: session={session_id}, "
                        f"message={message_id}, feedback={feedback_type.value}"
                    )

                    return ToolResult(
                        success=True,
                        data={
                            "action": "updated",
                            "session_id": session_id,
                            "message_id": message_id,
                            "feedback_type": feedback_type.value
                        },
                        message="反馈已更新"
                    )
                else:
                    # 插入新反馈
                    await conn.execute(
                        """
                        INSERT INTO user_feedback (
                            session_id, message_id, feedback_type,
                            user_comment, metadata, created_at
                        ) VALUES ($1, $2, $3, $4, $5, $6)
                        """,
                        session_id,
                        message_id,
                        feedback_type.value,
                        user_comment,
                        metadata or {},
                        datetime.now()
                    )

                    logger.info(
                        f"记录反馈: session={session_id}, "
                        f"message={message_id}, feedback={feedback_type.value}"
                    )

                    return ToolResult(
                        success=True,
                        data={
                            "action": "created",
                            "session_id": session_id,
                            "message_id": message_id,
                            "feedback_type": feedback_type.value
                        },
                        message="反馈已记录"
                    )

        except Exception as e:
            logger.error(f"记录反馈失败: {e}")
            return ToolResult(
                success=False,
                error=str(e)
            )

    async def get_feedback_stats(
        self,
        session_id: Optional[str] = None,
        intent: Optional[str] = None,
        skill_name: Optional[str] = None,
        limit: int = 100
    ) -> ToolResult:
        """
        获取反馈统计信息

        Args:
            session_id: 筛选指定会话
            intent: 筛选指定意图
            skill_name: 筛选指定 Skill
            limit: 返回结果数量

        Returns:
            ToolResult: 统计数据
        """
        try:
            async with self.db_pool.acquire() as conn:
                # 构建查询条件
                conditions = []
                params = []
                param_idx = 1

                if session_id:
                    conditions.append(f"session_id = ${param_idx}")
                    params.append(session_id)
                    param_idx += 1

                if intent:
                    conditions.append(f"metadata->>'intent' = ${param_idx}")
                    params.append(intent)
                    param_idx += 1

                if skill_name:
                    conditions.append(f"metadata->>'skill_name' = ${param_idx}")
                    params.append(skill_name)
                    param_idx += 1

                where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

                # 查询反馈记录
                rows = await conn.fetch(
                    f"""
                    SELECT
                        session_id,
                        message_id,
                        feedback_type,
                        user_comment,
                        metadata,
                        created_at
                    FROM user_feedback
                    {where_clause}
                    ORDER BY created_at DESC
                    LIMIT ${param_idx}
                    """,
                    *params, limit
                )

                # 统计汇总
                thumbs_up_count = sum(1 for r in rows if r["feedback_type"] == "thumbs_up")
                thumbs_down_count = sum(1 for r in rows if r["feedback_type"] == "thumbs_down")

                # 按意图统计
                intent_stats = {}
                for row in rows:
                    intent_name = row["metadata"].get("intent", "unknown")
                    if intent_name not in intent_stats:
                        intent_stats[intent_name] = {"thumbs_up": 0, "thumbs_down": 0}

                    if row["feedback_type"] == "thumbs_up":
                        intent_stats[intent_name]["thumbs_up"] += 1
                    else:
                        intent_stats[intent_name]["thumbs_down"] += 1

                # 按 Skill 统计
                skill_stats = {}
                for row in rows:
                    skill = row["metadata"].get("skill_name", "unknown")
                    if skill not in skill_stats:
                        skill_stats[skill] = {"thumbs_up": 0, "thumbs_down": 0}

                    if row["feedback_type"] == "thumbs_up":
                        skill_stats[skill]["thumbs_up"] += 1
                    else:
                        skill_stats[skill]["thumbs_down"] += 1

                return ToolResult(
                    success=True,
                    data={
                        "summary": {
                            "total": len(rows),
                            "thumbs_up": thumbs_up_count,
                            "thumbs_down": thumbs_down_count,
                            "satisfaction_rate": thumbs_up_count / len(rows) if rows else 0
                        },
                        "by_intent": intent_stats,
                        "by_skill": skill_stats,
                        "recent_feedback": [dict(r) for r in rows]
                    }
                )

        except Exception as e:
            logger.error(f"获取反馈统计失败: {e}")
            return ToolResult(
                success=False,
                error=str(e)
            )

    async def get_negative_feedback(
        self,
        limit: int = 50,
        intent: Optional[str] = None
    ) -> ToolResult:
        """
        获取负面反馈（用于分析和优化）

        Args:
            limit: 返回数量
            intent: 筛选指定意图

        Returns:
            ToolResult: 负面反馈列表
        """
        try:
            async with self.db_pool.acquire() as conn:
                params = []
                param_idx = 1
                conditions = ["feedback_type = 'thumbs_down'"]

                if intent:
                    conditions.append(f"metadata->>'intent' = ${param_idx}")
                    params.append(intent)
                    param_idx += 1

                where_clause = f"WHERE {' AND '.join(conditions)}"

                rows = await conn.fetch(
                    f"""
                    SELECT
                        session_id,
                        message_id,
                        user_comment,
                        metadata,
                        created_at
                    FROM user_feedback
                    {where_clause}
                    ORDER BY created_at DESC
                    LIMIT ${param_idx}
                    """,
                    *params, limit
                )

                return ToolResult(
                    success=True,
                    data={
                        "negative_feedback_count": len(rows),
                        "items": [dict(r) for r in rows]
                    }
                )

        except Exception as e:
            logger.error(f"获取负面反馈失败: {e}")
            return ToolResult(
                success=False,
                error=str(e)
            )


# ============== 数据库表初始化 ==============

FEEDBACK_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS user_feedback (
    id BIGSERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    message_id VARCHAR(255) NOT NULL,
    feedback_type VARCHAR(20) NOT NULL CHECK (feedback_type IN ('thumbs_up', 'thumbs_down')),
    user_comment TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP,
    UNIQUE(session_id, message_id)
);

CREATE INDEX IF NOT EXISTS idx_feedback_session ON user_feedback(session_id);
CREATE INDEX IF NOT EXISTS idx_feedback_intent ON user_feedback((metadata->>'intent'));
CREATE INDEX IF NOT EXISTS idx_feedback_skill ON user_feedback((metadata->>'skill_name'));
CREATE INDEX IF NOT EXISTS idx_feedback_type ON user_feedback(feedback_type);
CREATE INDEX IF NOT EXISTS idx_feedback_created ON user_feedback(created_at DESC);
"""
