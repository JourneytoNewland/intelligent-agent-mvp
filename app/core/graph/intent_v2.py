"""
意图识别 + 参数提取 V2
使用 Function Calling 一次完成意图识别和参数提取
"""

import json
import logging
from typing import Dict, Any, Optional
import zhipuai

from app.core.graph.param_schemas import (
    get_param_schema,
    validate_params,
    FEWSHOT_EXAMPLES
)
from app.config import settings

logger = logging.getLogger(__name__)


class IntentRecognizerV2:
    """
    意图识别器 V2 - 一次 LLM 调用完成意图识别 + 参数提取

    策略：
    1. 优先使用 Function Calling（智谱 GLM-4 tools 参数）
    2. 降级到 Prompt Engineering + Few-shot
    3. 最终降级到规则匹配
    """

    # 意图定义
    INTENTS = {
        "query_metrics": "查询业务指标（销售额、用户数等），支持时间范围和多维度筛选",
        "generate_report": "生成业务报表（按地区、产品等），支持 CSV、JSON、Excel 格式",
        "analyze_root_cause": "分析指标异常原因（节假日、营销活动、系统维护等）",
        "chat": "普通对话，不需要调用 Skills"
    }

    def __init__(self, api_key: Optional[str] = None, model: str = "glm-4"):
        self.api_key = api_key or settings.zhipuai_api_key
        self.model = model
        self.client_available = bool(self.api_key)

        if self.client_available:
            zhipuai.api_key = self.api_key

    async def recognize_with_params(
        self,
        user_message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        识别意图并提取参数（一次完成）

        返回格式：
        {
            "intent": "query_metrics",
            "confidence": 0.95,
            "params": {...},  # 验证后的 Pydantic 模型 dict
            "raw_params": {...},  # 原始 LLM 返回
            "method": "function_calling" | "prompt_engineering" | "rule_based"
        }
        """
        # 方案 1: Function Calling（推荐）
        if self.client_available:
            try:
                result = await self._function_calling_approach(user_message, context)
                logger.info(f"Function Calling 成功: intent={result['intent']}")
                return result
            except Exception as e:
                logger.warning(f"Function Calling 失败: {e}, 降级到 Prompt Engineering")

        # 方案 2: Prompt Engineering + Few-shot
        if self.client_available:
            try:
                result = await self._prompt_engineering_approach(user_message, context)
                logger.info(f"Prompt Engineering 成功: intent={result['intent']}")
                return result
            except Exception as e:
                logger.warning(f"Prompt Engineering 失败: {e}, 降级到规则匹配")

        # 方案 3: 规则匹配（最终降级）
        result = self._rule_based_approach(user_message, context)
        logger.info(f"规则匹配成功: intent={result['intent']}")
        return result

    async def _function_calling_approach(
        self,
        user_message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        使用 Function Calling 识别意图并提取参数

        智谱 GLM-4 Function Calling 文档：
        https://open.bigmodel.cn/dev/api#function_calling
        """
        # 构建 Function Calling tools
        tools = []
        for intent_name, intent_desc in self.INTENTS.items():
            if intent_name == "chat":
                continue  # chat 意图不需要 tool

            param_schema = get_param_schema(intent_name)
            tools.append({
                "type": "function",
                "function": {
                    "name": intent_name,
                    "description": intent_desc,
                    "parameters": param_schema
                }
            })

        # 调用 LLM
        response = zhipuai.model_api.invoke(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": self._build_system_prompt()
                },
                {
                    "role": "user",
                    "content": user_message
                }
            ],
            tools=tools,
            tool_choice="auto",  # 让模型自动选择是否调用工具
            temperature=0.1,
            top_p=0.7
        )

        # 解析响应
        if response.get("code") != 200:
            raise Exception(f"智谱 API 调用失败: {response}")

        resp_data = response["data"]["choices"][0]

        # 检查是否调用了工具
        tool_calls = resp_data.get("message", {}).get("tool_calls")

        if not tool_calls or len(tool_calls) == 0:
            # 没有调用工具，说明是 chat 意图
            return {
                "intent": "chat",
                "confidence": 0.9,
                "params": {},
                "raw_params": {},
                "method": "function_calling"
            }

        # 提取工具调用信息
        tool_call = tool_calls[0]
        function_name = tool_call["function"]["name"]
        function_args = json.loads(tool_call["function"]["arguments"])

        # 验证参数
        try:
            validated_params = validate_params(function_name, function_args)
            params_dict = validated_params.model_dump()
        except Exception as e:
            logger.warning(f"参数验证失败: {e}, 使用原始参数")
            params_dict = function_args

        return {
            "intent": function_name,
            "confidence": 0.95,
            "params": params_dict,
            "raw_params": function_args,
            "method": "function_calling"
        }

    async def _prompt_engineering_approach(
        self,
        user_message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        使用 Prompt Engineering + Few-shot Learning
        """
        # 第一步：识别意图
        intent = await self._identify_intent_via_fewshot(user_message, context)

        if intent == "chat":
            return {
                "intent": "chat",
                "confidence": 0.8,
                "params": {},
                "raw_params": {},
                "method": "prompt_engineering"
            }

        # 第二步：提取参数
        params = await self._extract_params_via_fewshot(
            user_message,
            intent,
            context
        )

        # 验证参数
        try:
            validated_params = validate_params(intent, params)
            params_dict = validated_params.model_dump()
        except Exception as e:
            logger.warning(f"参数验证失败: {e}, 使用原始参数")
            params_dict = params

        return {
            "intent": intent,
            "confidence": 0.85,
            "params": params_dict,
            "raw_params": params,
            "method": "prompt_engineering"
        }

    async def _identify_intent_via_fewshot(
        self,
        user_message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """使用 Few-shot 识别意图"""

        # 构建示例
        examples = []
        for intent, desc in self.INTENTS.items():
            if intent == "chat":
                examples.append(f"用户消息：你好\n意图：chat（普通对话）")
            else:
                example_msgs = FEWSHOT_EXAMPLES.get(intent, [])
                if example_msgs:
                    ex = example_msgs[0]
                    examples.append(f"用户消息：{ex['user_message']}\n意图：{intent}（{desc}）")

        prompt = f"""你是一个意图识别专家。请判断用户消息的意图。

意图定义：
{json.dumps(self.INTENTS, ensure_ascii=False, indent=2)}

识别示例：
{chr(10).join(examples)}

当前用户消息：{user_message}
意图（仅返回 intent 名称）："""

        response = zhipuai.model_api.invoke(
            model=self.model,
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.0
        )

        if response.get("code") == 200:
            intent = response["data"]["choices"][0]["message"]["content"].strip()
            if intent in self.INTENTS:
                return intent

        # 降级：返回默认意图
        return "chat"

    async def _extract_params_via_fewshot(
        self,
        user_message: str,
        intent: str,
        context: Optional[Dict[str, Any]] = None
    ) -> dict:
        """使用 Few-shot 提取参数"""

        examples = FEWSHOT_EXAMPLES.get(intent, [])

        # 获取参数 Schema
        param_schema = get_param_schema(intent)

        prompt = f"""你是一个参数提取专家。请从用户消息中提取 {intent} 的参数。

参数定义：
{json.dumps(param_schema, ensure_ascii=False, indent=2)}

提取示例：
"""
        for ex in examples[:5]:  # 最多使用 5 个示例
            prompt += f"\n用户消息：{ex['user_message']}\n"
            prompt += f"提取结果：{json.dumps(ex['expected_params'], ensure_ascii=False)}\n"

        prompt += f"\n当前用户消息：{user_message}\n"
        prompt += "提取结果（JSON 格式，不要添加其他说明）："

        response = zhipuai.model_api.invoke(
            model=self.model,
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.1
        )

        if response.get("code") == 200:
            content = response["data"]["choices"][0]["message"]["content"].strip()
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                pass

        return {}

    def _rule_based_approach(
        self,
        user_message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """规则匹配降级方案"""

        message = user_message.lower()

        # 意图匹配规则
        intent_rules = {
            "query_metrics": ["查询", "统计", "多少", "查看", "显示"],
            "generate_report": ["报表", "报告", "导出", "生成"],
            "analyze_root_cause": ["分析", "原因", "为什么", "下降", "异常"]
        }

        best_intent = "chat"
        max_matches = 0

        for intent, keywords in intent_rules.items():
            matches = sum(1 for kw in keywords if kw in message)
            if matches > max_matches:
                max_matches = matches
                best_intent = intent

        # 简单参数提取（基于关键词）
        params = self._extract_params_by_rules(user_message, best_intent)

        return {
            "intent": best_intent,
            "confidence": 0.6 if max_matches > 0 else 0.4,
            "params": params,
            "raw_params": params,
            "method": "rule_based"
        }

    def _extract_params_by_rules(self, user_message: str, intent: str) -> dict:
        """基于规则的简单参数提取"""

        params = {}
        message = user_message.lower()

        if intent == "query_metrics":
            # 提取指标
            metrics_keywords = {
                "销售额": "sales",
                "用户数": "user_count",
                "订单量": "order_count",
                "转化率": "conversion_rate"
            }
            for kw, metric in metrics_keywords.items():
                if kw in message:
                    params["metric"] = metric
                    break

            # 提取时间范围
            if "今天" in message or "当日" in message:
                params["time_range"] = "today"
            elif "昨天" in message:
                params["time_range"] = "yesterday"
            elif "7天" in message or "一周" in message:
                params["time_range"] = "7d"
            elif "30天" in message or "一月" in message:
                params["time_range"] = "30d"
            else:
                params["time_range"] = "7d"  # 默认

        return params

    def _build_system_prompt(self) -> str:
        """构建系统提示词"""
        return """你是一个智能数据分析助手的意图识别和参数提取专家。

你的任务是：
1. 理解用户的自然语言请求
2. 识别用户想要执行的操作（意图）
3. 提取执行该操作所需的参数

可用工具：
- query_metrics: 查询业务指标
- generate_report: 生成业务报表
- analyze_root_cause: 分析指标异常原因

如果用户的请求不需要调用任何工具（如打招呼、感谢、闲聊），则不调用任何工具，直接回复用户。

请严格遵循工具的参数定义进行提取。如果参数不明确或缺失，使用合理的默认值。"""
