"""
Agent 状态图定义

使用 LangGraph 构建状态机，编排 Skills 执行流程
"""
import logging
import time
from typing import Dict, Any, List, Literal
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import StateGraph, END

from app.core.graph.state import AgentState, SkillExecutionResult
from app.core.graph.intent import IntentRecognizer
from app.core.skills.registry import SkillRegistry

logger = logging.getLogger(__name__)


class AgentGraph:
    """
    Agent 状态图

    定义完整的对话流程：
    1. start: 接收用户消息
    2. intent_recognition: 识别意图
    3. skill_execution: 调用 Skills
    4. response_generation: 生成回复
    5. end: 返回结果
    """

    def __init__(
        self,
        skill_registry: SkillRegistry,
        intent_recognizer: IntentRecognizer
    ):
        """
        初始化 Agent 状态图

        Args:
            skill_registry: Skill 注册表
            intent_recognizer: 意图识别器
        """
        self.skill_registry = skill_registry
        self.intent_recognizer = intent_recognizer

        # 构建状态图
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """
        构建状态图

        Returns:
            StateGraph: LangGraph 状态图
        """
        # 创建状态图
        workflow = StateGraph(AgentState)

        # 添加节点
        workflow.add_node("intent_recognition", self._intent_recognition_node)
        workflow.add_node("skill_execution", self._skill_execution_node)
        workflow.add_node("response_generation", self._response_generation_node)

        # 设置入口点
        workflow.set_entry_point("intent_recognition")

        # 添加边（状态流转）
        workflow.add_edge("intent_recognition", "skill_execution")
        workflow.add_edge("skill_execution", "response_generation")
        workflow.add_edge("response_generation", END)

        # 编译状态图
        return workflow.compile()

    async def _intent_recognition_node(
        self,
        state: AgentState
    ) -> AgentState:
        """
        意图识别节点

        Args:
            state: 当前状态

        Returns:
            AgentState: 更新后的状态
        """
        logger.info(f"开始意图识别: {state['user_message'][:50]}...")

        try:
            # 调用意图识别器
            result = await self.intent_recognizer.recognize(
                user_message=state["user_message"],
                context=state.get("metadata", {})
            )

            # 更新状态
            state["intent"] = result["intent"]
            state["intent_confidence"] = result["confidence"]
            state["selected_skills"] = self.intent_recognizer.get_skill_mapping(result["intent"])

            # 添加到消息历史
            state["messages"].append(
                AIMessage(
                    content=f"已识别意图: {result['intent']} (置信度: {result['confidence']:.2f})\n"
                           f"推理过程: {result['reasoning']}\n"
                           f"将调用 Skills: {', '.join(state['selected_skills'])}"
                )
            )

            logger.info(
                f"意图识别完成: {result['intent']} "
                f"(置信度: {result['confidence']:.2f}, "
                f"Skills: {state['selected_skills']})"
            )

        except Exception as e:
            logger.error(f"意图识别失败: {e}")
            state["intent"] = "chat"
            state["intent_confidence"] = 0.0
            state["selected_skills"] = []

        return state

    async def _skill_execution_node(
        self,
        state: AgentState
    ) -> AgentState:
        """
        Skill 执行节点

        Args:
            state: 当前状态

        Returns:
            AgentState: 更新后的状态
        """
        logger.info(f"开始执行 Skills: {state['selected_skills']}")

        # 如果没有 Skills 需要执行，直接跳过
        if not state["selected_skills"]:
            logger.info("无需执行 Skills，跳过")
            state["messages"].append(
                AIMessage(content="无需调用 Skills，直接生成回复")
            )
            return state

        # 执行每个 Skill
        for skill_name in state["selected_skills"]:
            try:
                logger.info(f"执行 Skill: {skill_name}")

                # 获取 Skill
                skill = self.skill_registry.get(skill_name)
                if not skill:
                    raise ValueError(f"Skill 不存在: {skill_name}")

                # 构建 Skill 输入（这里需要根据意图生成参数）
                # 简化实现：使用空参数，实际应该从用户消息中提取
                skill_input = self._build_skill_input(
                    skill_name=skill_name,
                    user_message=state["user_message"],
                    intent=state["intent"]
                )

                # 执行 Skill
                start_time = time.time()
                result = await skill.execute(skill_input, context={})
                execution_time = time.time() - start_time

                # 记录结果
                skill_result = SkillExecutionResult(
                    skill_name=skill_name,
                    success=result.success,
                    data=result.data,
                    error=result.error,
                    execution_time=execution_time
                )
                state["skill_results"].append(skill_result)

                # 添加到消息历史
                if result.success:
                    state["messages"].append(
                        AIMessage(
                            content=f"✓ {skill_name} 执行成功\n"
                                   f"数据: {str(result.data)[:200]}..."
                        )
                    )
                else:
                    state["messages"].append(
                        AIMessage(
                            content=f"✗ {skill_name} 执行失败: {result.error}"
                        )
                    )

                logger.info(
                    f"{skill_name} 执行完成: "
                    f"{'成功' if result.success else '失败'} "
                    f"({execution_time:.2f}s)"
                )

            except Exception as e:
                logger.error(f"Skill 执行异常: {skill_name} - {e}")
                skill_result = SkillExecutionResult(
                    skill_name=skill_name,
                    success=False,
                    error=str(e),
                    execution_time=0.0
                )
                state["skill_results"].append(skill_result)

        return state

    async def _response_generation_node(
        self,
        state: AgentState
    ) -> AgentState:
        """
        回复生成节点

        Args:
            state: 当前状态

        Returns:
            AgentState: 更新后的状态
        """
        logger.info("开始生成回复")

        try:
            # 根据 Skill 结果生成回复
            if state["skill_results"]:
                # 有 Skill 执行结果
                successful_results = [r for r in state["skill_results"] if r.success]

                if successful_results:
                    # 构建成功的回复
                    response_parts = []
                    for result in successful_results:
                        response_parts.append(
                            f"✓ {result.skill_name} 执行成功\n"
                            f"  耗时: {result.execution_time:.2f}s\n"
                            f"  结果: {self._format_result(result.data)}"
                        )

                    state["final_response"] = "\n\n".join(response_parts)
                else:
                    # 所有 Skills 都失败了
                    state["final_response"] = "抱歉，执行过程中遇到错误，请稍后重试。"
            else:
                # 无 Skill 执行（普通对话）
                state["final_response"] = self._generate_chat_response(
                    state["user_message"],
                    state["intent"]
                )

            # 添加到消息历史
            state["messages"].append(AIMessage(content=state["final_response"]))

            logger.info(f"回复生成完成: {len(state['final_response'])} 字符")

        except Exception as e:
            logger.error(f"回复生成失败: {e}")
            state["final_response"] = "抱歉，生成回复时遇到错误。"

        return state

    def _build_skill_input(
        self,
        skill_name: str,
        user_message: str,
        intent: str
    ):
        """
        构建 Skill 输入参数

        Args:
            skill_name: Skill 名称
            user_message: 用户消息
            intent: 意图

        Returns:
            SkillInput: Skill 输入参数
        """
        from datetime import datetime, timedelta

        # 简化实现：返回默认参数
        # 实际应该从用户消息中提取参数（使用 LLM 或正则表达式）

        if skill_name == "QueryMetricsSkill":
            from app.core.skills.query_metrics import QueryMetricsInput
            return QueryMetricsInput(
                metric_name="sales_amount",
                start_date=datetime.now() - timedelta(days=7),
                end_date=datetime.now(),
                dimensions=["region_id"],
                aggregation="sum"
            )

        elif skill_name == "GenerateReportSkill":
            from app.core.skills.query_metrics import GenerateReportInput
            return GenerateReportInput(
                report_type="sales_by_region",
                start_date=datetime.now() - timedelta(days=7),
                end_date=datetime.now(),
                format="csv"
            )

        elif skill_name == "AnalyzeRootCauseSkill":
            from app.core.skills.query_metrics import AnalyzeRootCauseInput
            return AnalyzeRootCauseInput(
                metric_name="sales_amount",
                anomaly_date=datetime.now(),
                anomaly_value=50000.0,
                expected_value=100000.0,
                threshold_percent=20.0
            )

        else:
            raise ValueError(f"未知的 Skill: {skill_name}")

    def _format_result(self, data: Any) -> str:
        """
        格式化 Skill 结果

        Args:
            data: Skill 返回数据

        Returns:
            str: 格式化后的字符串
        """
        if isinstance(data, list):
            if len(data) == 0:
                return "无数据"
            elif len(data) <= 3:
                return str(data)
            else:
                return f"共 {len(data)} 条数据，前 3 条: {str(data[:3])}"
        elif isinstance(data, dict):
            return str(data)
        else:
            return str(data)[:200]

    def _generate_chat_response(
        self,
        user_message: str,
        intent: str
    ) -> str:
        """
        生成对话回复（无 Skill 调用）

        Args:
            user_message: 用户消息
            intent: 意图

        Returns:
            str: 回复消息
        """
        # 简化实现：基于规则的回复
        message_lower = user_message.lower()

        if any(word in message_lower for word in ["你好", "嗨", "hello", "hi"]):
            return "您好！我是智能数据分析助手，可以帮您查询指标、生成报表、分析异常。请问有什么可以帮您？"

        elif any(word in message_lower for word in ["谢谢", "感谢"]):
            return "不客气！如果还有其他问题，随时问我。"

        elif any(word in message_lower for word in ["再见", "拜拜"]):
            return "再见！祝您工作顺利！"

        else:
            return f"我收到了您的消息：「{user_message}」\n\n目前我主要支持以下功能：\n1. 查询业务指标\n2. 生成业务报表\n3. 分析异常原因\n\n请问您需要哪方面的帮助？"

    async def run(
        self,
        session_id: str,
        user_message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        运行 Agent 状态图

        Args:
            session_id: 会话 ID
            user_message: 用户消息
            context: 上下文信息

        Returns:
            Dict: 执行结果
        """
        logger.info(f"开始执行 Agent: session={session_id}")

        # 初始化状态
        initial_state: AgentState = {
            "session_id": session_id,
            "user_message": user_message,
            "intent": None,
            "intent_confidence": 0.0,
            "selected_skills": [],
            "skill_results": [],
            "messages": [HumanMessage(content=user_message)],
            "final_response": None,
            "metadata": {
                "start_time": time.time(),
                **(context or {})
            }
        }

        try:
            # 执行状态图
            final_state = await self.graph.ainvoke(initial_state)

            # 计算总耗时
            execution_time = time.time() - final_state["metadata"]["start_time"]
            final_state["metadata"]["execution_time"] = execution_time
            final_state["metadata"]["success"] = True

            logger.info(
                f"Agent 执行完成: "
                f"intent={final_state['intent']}, "
                f"skills={len(final_state['skill_results'])}, "
                f"time={execution_time:.2f}s"
            )

            return final_state

        except Exception as e:
            logger.error(f"Agent 执行失败: {e}")
            return {
                "session_id": session_id,
                "user_message": user_message,
                "intent": "error",
                "intent_confidence": 0.0,
                "selected_skills": [],
                "skill_results": [],
                "messages": initial_state["messages"],
                "final_response": f"抱歉，处理您的请求时遇到错误: {str(e)}",
                "metadata": {
                    "success": False,
                    "error": str(e),
                    "execution_time": time.time() - initial_state["metadata"]["start_time"]
                }
            }

    def stream_events(
        self,
        session_id: str,
        user_message: str,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        流式输出 Agent 执行事件（用于 SSE）

        Args:
            session_id: 会话 ID
            user_message: 用户消息
            context: 上下文信息

        Yields:
            Dict: 事件数据
        """
        import asyncio

        # 初始化状态
        initial_state: AgentState = {
            "session_id": session_id,
            "user_message": user_message,
            "intent": None,
            "intent_confidence": 0.0,
            "selected_skills": [],
            "skill_results": [],
            "messages": [HumanMessage(content=user_message)],
            "final_response": None,
            "metadata": {
                "start_time": time.time(),
                **(context or {})
            }
        }

        try:
            # 异步流式执行
            async def _stream():
                async for event in self.graph.astream(initial_state):
                    # 发送事件
                    yield {
                        "type": "state_update",
                        "data": event
                    }

            # 迭代事件
            loop = asyncio.get_event_loop()
            for event in loop.run_until_complete(_stream()):
                yield event

        except Exception as e:
            logger.error(f"流式执行失败: {e}")
            yield {
                "type": "error",
                "data": {"error": str(e)}
            }
