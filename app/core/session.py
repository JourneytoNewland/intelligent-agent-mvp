"""
会话管理器

使用 Redis 存储会话状态，支持多轮对话
"""
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import redis.asyncio as redis

from app.config import get_settings

logger = logging.getLogger(__name__)


class SessionManager:
    """
    会话管理器

    功能：
    - 创建会话
    - 获取会话
    - 更新会话
    - 删除会话
    - 会话过期清理
    """

    def __init__(self, redis_url: Optional[str] = None):
        """
        初始化会话管理器

        Args:
            redis_url: Redis 连接 URL（可选，默认从配置读取）
        """
        settings = get_settings()
        self.redis_url = redis_url or settings.redis_url
        self.session_ttl = 3600  # 会话过期时间：1 小时

        self._redis: Optional[redis.Redis] = None

    async def _get_redis(self) -> redis.Redis:
        """获取或创建 Redis 连接"""
        if self._redis is None:
            self._redis = await redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
        return self._redis

    async def create_session(
        self,
        session_id: str,
        user_message: str,
        initial_state: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        创建新会话

        Args:
            session_id: 会话 ID
            user_message: 用户消息
            initial_state: 初始状态（可选）

        Returns:
            Dict: 会话信息
        """
        try:
            r = await self._get_redis()

            # 构建会话数据
            session_data = {
                "session_id": session_id,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "message_count": 1,
                "messages": [
                    {
                        "role": "user",
                        "content": user_message,
                        "timestamp": datetime.now().isoformat()
                    }
                ],
                "state": initial_state or {}
            }

            # 存储到 Redis
            key = f"session:{session_id}"
            await r.setex(
                key,
                self.session_ttl,
                json.dumps(session_data)
            )

            logger.info(f"创建会话: {session_id}")
            return session_data

        except Exception as e:
            logger.error(f"创建会话失败: {e}")
            raise

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        获取会话

        Args:
            session_id: 会话 ID

        Returns:
            Dict: 会话数据，如果不存在返回 None
        """
        try:
            r = await self._get_redis()

            key = f"session:{session_id}"
            data = await r.get(key)

            if data:
                session_data = json.loads(data)
                logger.debug(f"获取会话: {session_id}")
                return session_data
            else:
                logger.warning(f"会话不存在: {session_id}")
                return None

        except Exception as e:
            logger.error(f"获取会话失败: {e}")
            raise

    async def update_session(
        self,
        session_id: str,
        assistant_message: str,
        state_update: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        更新会话

        Args:
            session_id: 会话 ID
            assistant_message: 助手回复
            state_update: 状态更新（可选）

        Returns:
            Dict: 更新后的会话数据
        """
        try:
            r = await self._get_redis()

            # 获取现有会话
            session_data = await self.get_session(session_id)
            if not session_data:
                raise ValueError(f"会话不存在: {session_id}")

            # 添加助手消息
            session_data["messages"].append({
                "role": "assistant",
                "content": assistant_message,
                "timestamp": datetime.now().isoformat()
            })

            # 更新消息计数
            session_data["message_count"] = len(session_data["messages"])

            # 更新时间戳
            session_data["updated_at"] = datetime.now().isoformat()

            # 更新状态
            if state_update:
                session_data["state"].update(state_update)

            # 保存到 Redis
            key = f"session:{session_id}"
            await r.setex(
                key,
                self.session_ttl,
                json.dumps(session_data)
            )

            logger.info(f"更新会话: {session_id}")
            return session_data

        except Exception as e:
            logger.error(f"更新会话失败: {e}")
            raise

    async def add_user_message(
        self,
        session_id: str,
        user_message: str
    ) -> Dict[str, Any]:
        """
        添加用户消息到会话

        Args:
            session_id: 会话 ID
            user_message: 用户消息

        Returns:
            Dict: 更新后的会话数据
        """
        try:
            r = await self._get_redis()

            # 获取现有会话
            session_data = await self.get_session(session_id)
            if not session_data:
                raise ValueError(f"会话不存在: {session_id}")

            # 添加用户消息
            session_data["messages"].append({
                "role": "user",
                "content": user_message,
                "timestamp": datetime.now().isoformat()
            })

            # 更新消息计数和时间戳
            session_data["message_count"] = len(session_data["messages"])
            session_data["updated_at"] = datetime.now().isoformat()

            # 保存到 Redis
            key = f"session:{session_id}"
            await r.setex(
                key,
                self.session_ttl,
                json.dumps(session_data)
            )

            logger.info(f"添加用户消息: {session_id}")
            return session_data

        except Exception as e:
            logger.error(f"添加用户消息失败: {e}")
            raise

    async def get_session_history(
        self,
        session_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        获取会话历史

        Args:
            session_id: 会话 ID
            limit: 返回消息数量限制

        Returns:
            List[Dict]: 消息历史
        """
        try:
            session_data = await self.get_session(session_id)
            if not session_data:
                return []

            messages = session_data.get("messages", [])
            # 返回最近的消息
            return messages[-limit:] if limit else messages

        except Exception as e:
            logger.error(f"获取会话历史失败: {e}")
            raise

    async def delete_session(self, session_id: str) -> bool:
        """
        删除会话

        Args:
            session_id: 会话 ID

        Returns:
            bool: 是否删除成功
        """
        try:
            r = await self._get_redis()

            key = f"session:{session_id}"
            result = await r.delete(key)

            if result:
                logger.info(f"删除会话: {session_id}")
                return True
            else:
                logger.warning(f"会话不存在或已删除: {session_id}")
                return False

        except Exception as e:
            logger.error(f"删除会话失败: {e}")
            raise

    async def list_sessions(
        self,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        列出所有会话

        Args:
            limit: 返回数量限制

        Returns:
            List[Dict]: 会话列表
        """
        try:
            r = await self._get_redis()

            # 扫描所有 session: 开头的键
            pattern = "session:*"
            sessions = []

            async for key in r.scan_iter(match=pattern, count=limit):
                data = await r.get(key)
                if data:
                    session_data = json.loads(data)
                    sessions.append(session_data)

            logger.info(f"列出会话: {len(sessions)} 个")
            return sessions

        except Exception as e:
            logger.error(f"列出会话失败: {e}")
            raise

    async def close(self):
        """关闭 Redis 连接"""
        if self._redis:
            await self._redis.close()
            self._redis = None
            logger.info("会话管理器已关闭")

    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()
