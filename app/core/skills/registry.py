"""
Skills 注册表

管理所有可用的 Skills，提供 Skill 发现和获取功能
"""
import logging
from typing import Dict, List, Optional
from .query_metrics import (
    QueryMetricsSkill,
    GenerateReportSkill,
    AnalyzeRootCauseSkill
)
from .base import BaseSkill

logger = logging.getLogger(__name__)


class SkillRegistry:
    """
    Skill 注册表

    管理 Skills 的注册、发现和获取
    """

    def __init__(self, mcp_client=None, llm=None):
        """
        初始化注册表

        Args:
            mcp_client: MCP 客户端（用于调用数据库）
            llm: LLM 实例（用于根因分析）
        """
        self.mcp_client = mcp_client
        self.llm = llm
        self.skills: Dict[str, BaseSkill] = {}

        # 注册所有 Skills
        self._register_skills()

    def _register_skills(self):
        """注册所有可用的 Skills"""
        skills_to_register = [
            QueryMetricsSkill(self.mcp_client),
            GenerateReportSkill(self.mcp_client),
            AnalyzeRootCauseSkill(self.mcp_client, self.llm),
        ]

        for skill in skills_to_register:
            self.register(skill)

        logger.info(f"已注册 {len(self.skills)} 个 Skills: {list(self.skills.keys())}")

    def register(self, skill: BaseSkill):
        """
        注册一个 Skill

        Args:
            skill: Skill 实例
        """
        self.skills[skill.name] = skill
        logger.info(f"已注册 Skill: {skill.name}")

    def get(self, skill_name: str) -> Optional[BaseSkill]:
        """
        根据名称获取 Skill

        Args:
            skill_name: Skill 名称

        Returns:
            BaseSkill | None: Skill 实例
        """
        return self.skills.get(skill_name)

    def list_skills(self) -> List[Dict[str, str]]:
        """
        列出所有可用的 Skills

        Returns:
            List[Dict[str, str]]: Skill 信息列表
        """
        return [
            {
                "name": skill.name,
                "description": skill.description,
                "input_schema": skill.input_schema.__name__
            }
            for skill in self.skills.values()
        ]

    def get_langchain_tools(self) -> List:
        """
        将所有 Skills 转换为 LangChain Tools

        Returns:
            List: LangChain Tool 列表
        """
        return [skill.to_langchain_tool() for skill in self.skills.values()]

    async def close(self):
        """关闭所有 Skills 的资源"""
        for skill in self.skills.values():
            if hasattr(skill, 'close'):
                await skill.close()
        logger.info("Skill 注册表已关闭")

    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()
