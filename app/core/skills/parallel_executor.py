"""
Skill 并行执行器
支持无依赖 Skills 的并发执行，提升系统吞吐量
"""

import asyncio
from typing import List, Dict, Any, Set, Optional
from datetime import datetime
import logging
from pydantic import BaseModel, Field

from app.core.skills.base import BaseSkill, SkillOutput
from app.core.skills.registry import SkillRegistry

logger = logging.getLogger(__name__)


class SkillExecutionResult(BaseModel):
    """Skill 执行结果（扩展版）"""
    skill_name: str = Field(..., description="Skill 名称")
    success: bool = Field(..., description="执行是否成功")
    data: Optional[Any] = Field(default=None, description="返回数据")
    message: Optional[str] = Field(default=None, description="执行消息")
    error: Optional[str] = Field(default=None, description="错误信息")
    execution_time: float = Field(..., description="执行耗时（秒）")


class ParallelSkillExecutor:
    """
    并行 Skill 执行器

    核心能力：
    1. 依赖分析 - 判断哪些 Skills 可以并行
    2. 并发执行 - 使用 asyncio.gather 并行调用
    3. 错误隔离 - 单个 Skill 失败不影响其他 Skills
    4. 超时控制 - 防止单个 Skill 阻塞太久
    """

    def __init__(
        self,
        registry: SkillRegistry,
        max_concurrency: int = 5,
        default_timeout: float = 30.0
    ):
        self.registry = registry
        self.max_concurrency = max_concurrency
        self.default_timeout = default_timeout

        # Skill 依赖关系配置
        # format: {skill_name: [depends_on_skill_names]}
        self.dependency_graph = {
            "analyze_root_cause": ["query_metrics"],  # 根因分析依赖查询指标
        }

    async def execute_skills(
        self,
        skill_requests: List[Dict[str, Any]],
        session_id: str
    ) -> List[SkillExecutionResult]:
        """
        执行多个 Skills，自动并行化无依赖的 Skills

        Args:
            skill_requests: Skill 请求列表
                [
                    {"skill": "query_metrics", "params": {...}},
                    {"skill": "generate_report", "params": {...}}
                ]
            session_id: 会话 ID

        Returns:
            List[SkillExecutionResult]: 执行结果列表（按请求顺序）
        """
        if not skill_requests:
            return []

        # 1. 分析依赖关系，构建执行批次
        batches = self._build_execution_batches(skill_requests)

        logger.info(f"Skill 执行计划: {len(skill_requests)} 个 Skills, 分 {len(batches)} 批")

        # 2. 按批次执行
        all_results = []
        for batch_idx, batch in enumerate(batches, 1):
            logger.info(f"执行第 {batch_idx}/{len(batches)} 批: {[s['skill'] for s in batch]}")

            # 并行执行当前批次
            batch_results = await self._execute_batch(batch, session_id)
            all_results.extend(batch_results)

        # 3. 按原始请求顺序排序结果
        result_map = {r.skill_name: r for r in all_results}
        ordered_results = []
        for req in skill_requests:
            skill_name = req["skill"]
            if skill_name in result_map:
                ordered_results.append(result_map[skill_name])
            else:
                # 失败的情况，返回错误结果
                ordered_results.append(SkillExecutionResult(
                    skill_name=skill_name,
                    success=False,
                    error=f"Skill {skill_name} 未找到或执行失败",
                    execution_time=0.0
                ))

        return ordered_results

    def _build_execution_batches(self, skill_requests: List[Dict]) -> List[List[Dict]]:
        """
        根据依赖关系构建执行批次

        使用拓扑排序算法：
        - Batch 1: 无依赖的 Skills
        - Batch 2: 仅依赖 Batch 1 的 Skills
        - Batch 3: 仅依赖 Batch 1-2 的 Skills
        ...
        """
        # 提取所有涉及的 Skill 名称
        requested_skills = [req["skill"] for req in skill_requests]

        # 构建依赖映射
        dependency_map = {}
        for skill_name in requested_skills:
            dependencies = self.dependency_graph.get(skill_name, [])
            # 只保留在当前请求列表中的依赖
            valid_deps = [d for d in dependencies if d in requested_skills]
            dependency_map[skill_name] = valid_deps

        # 拓扑排序构建批次
        batches = []
        remaining = set(requested_skills)

        while remaining:
            # 找出当前可以执行的 Skills（无依赖或依赖已满足）
            ready_skills = []
            for skill_name in remaining:
                deps = dependency_map.get(skill_name, [])
                if all(dep not in remaining for dep in deps):
                    ready_skills.append(skill_name)

            if not ready_skills:
                # 存在循环依赖，强制执行剩余的
                logger.warning(f"检测到可能的循环依赖: {remaining}")
                ready_skills = list(remaining)

            # 构建当前批次
            batch = [
                req for req in skill_requests
                if req["skill"] in ready_skills
            ]
            batches.append(batch)

            # 从剩余集合中移除已处理的
            remaining -= set(ready_skills)

        return batches

    async def _execute_batch(
        self,
        batch: List[Dict],
        session_id: str
    ) -> List[SkillExecutionResult]:
        """
        并行执行一批 Skills

        使用 asyncio.TaskGroup (Python 3.11+) 或 asyncio.gather
        """
        # 创建并发任务
        tasks = []
        for req in batch:
            task = self._execute_single_skill(req, session_id)
            tasks.append(task)

        # 并发执行，限制并发数
        if len(tasks) <= self.max_concurrency:
            results = await asyncio.gather(*tasks, return_exceptions=True)
        else:
            # 分批执行以控制并发数
            results = []
            for i in range(0, len(tasks), self.max_concurrency):
                batch_tasks = tasks[i:i + self.max_concurrency]
                batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                results.extend(batch_results)

        # 处理异常结果
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                skill_name = batch[i]["skill"]
                logger.error(f"Skill {skill_name} 执行异常: {result}")
                final_results.append(SkillExecutionResult(
                    skill_name=skill_name,
                    success=False,
                    error=str(result),
                    execution_time=0.0
                ))
            else:
                final_results.append(result)

        return final_results

    async def _execute_single_skill(
        self,
        req: Dict,
        session_id: str
    ) -> SkillExecutionResult:
        """
        执行单个 Skill（带超时控制）
        """
        skill_name = req["skill"]
        params = req.get("params", {})

        start_time = datetime.now()

        try:
            # 获取 Skill 实例
            skill = self.registry.get_skill(skill_name)
            if not skill:
                raise ValueError(f"Skill {skill_name} 未找到")

            # 执行（带超时）
            result = await asyncio.wait_for(
                skill.execute(params, session_id),
                timeout=self.default_timeout
            )

            execution_time = (datetime.now() - start_time).total_seconds()

            logger.info(
                f"Skill {skill_name} 执行成功: "
                f"耗时 {execution_time:.2f}s"
            )

            return SkillExecutionResult(
                skill_name=skill_name,
                success=True,
                data=result.get("data"),
                message=result.get("message"),
                execution_time=execution_time
            )

        except asyncio.TimeoutError:
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"Skill {skill_name} 执行超时 ({self.default_timeout}s)")

            return SkillExecutionResult(
                skill_name=skill_name,
                success=False,
                error=f"执行超时 ({self.default_timeout}s)",
                execution_time=execution_time
            )

        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"Skill {skill_name} 执行失败: {e}")

            return SkillExecutionResult(
                skill_name=skill_name,
                success=False,
                error=str(e),
                execution_time=execution_time
            )

    async def execute_parallel(
        self,
        skill_requests: List[Dict],
        session_id: str
    ) -> List[SkillExecutionResult]:
        """
        简化版并行执行（跳过依赖分析）

        适用于确定可以并行执行的场景
        """
        return await self._execute_batch(skill_requests, session_id)

    def add_dependency(self, skill_name: str, depends_on: List[str]):
        """
        动态添加依赖关系

        Args:
            skill_name: Skill 名称
            depends_on: 该 Skill 依赖的其他 Skills 列表
        """
        self.dependency_graph[skill_name] = depends_on
        logger.info(f"添加依赖关系: {skill_name} -> {depends_on}")

    def get_dependency_graph(self) -> Dict[str, List[str]]:
        """获取当前依赖关系图（用于调试和可视化）"""
        return self.dependency_graph.copy()


# ============== 使用示例 ==============

async def example_usage():
    """使用示例"""
    from app.core.skills.registry import get_global_registry

    registry = get_global_registry()
    executor = ParallelSkillExecutor(
        registry=registry,
        max_concurrency=3,
        default_timeout=30.0
    )

    # 示例 1: 无依赖并行执行
    requests = [
        {"skill": "query_metrics", "params": {"metric": "sales", "time_range": "7d"}},
        {"skill": "generate_report", "params": {"report_type": "sales", "time_range": "2024-01"}},
    ]
    results = await executor.execute_parallel(requests, session_id="test")
    print(f"并行执行结果: {len(results)} 个 Skills")

    # 示例 2: 有依赖的顺序执行
    requests = [
        {"skill": "query_metrics", "params": {"metric": "sales", "time_range": "7d"}},
        {"skill": "analyze_root_cause", "params": {"metric": "sales", "anomaly_time": "yesterday"}},
    ]
    results = await executor.execute_skills(requests, session_id="test")
    print(f"智能调度执行结果: {len(results)} 个 Skills")
