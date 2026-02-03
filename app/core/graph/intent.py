"""
意图识别模块

使用 LLM 识别用户意图，路由到不同的 Skills
"""
import logging
import json
from typing import Dict, Any, Optional

# zhipuai 的旧版 API
import zhipuai

from app.config import get_settings

logger = logging.getLogger(__name__)


class IntentRecognizer:
    """
    意图识别器

    使用智谱 AI GLM-4 识别用户意图
    """

    # 支持的意图类型
    INTENTS = {
        "query_metrics": "查询业务指标（销售额、用户数等），支持时间范围和维度筛选",
        "generate_report": "生成业务报表（按地区、产品等），支持 CSV 和 JSON 格式",
        "analyze_root_cause": "分析指标异常原因（节假日、营销活动、系统维护等）",
        "chat": "普通对话，不需要调用 Skills"
    }

    def __init__(self, api_key: Optional[str] = None):
        """
        初始化意图识别器

        Args:
            api_key: 智谱 AI API Key（可选，默认从配置读取）
        """
        settings = get_settings()
        self.api_key = api_key or settings.zhipuai_api_key
        self.model = settings.zhipuai_model

        if self.api_key:
            # 设置 API Key
            zhipuai.api_key = self.api_key
            self.client_available = True
        else:
            self.client_available = False
            logger.warning("智谱 AI API Key 未配置，意图识别将使用规则匹配")

    async def recognize(
        self,
        user_message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        识别用户意图

        Args:
            user_message: 用户消息
            context: 上下文信息

        Returns:
            Dict: {
                "intent": str,  # 意图类型
                "confidence": float,  # 置信度 (0-1)
                "parameters": Dict,  # 提取的参数
                "reasoning": str  # 推理过程
            }
        """
        # 如果未配置 API Key，使用规则匹配
        if not self.client_available:
            return self._rule_based_recognition(user_message, context)

        # 使用 LLM 识别意图
        try:
            return await self._llm_recognition(user_message, context)
        except Exception as e:
            logger.error(f"LLM 意图识别失败: {e}")
            # 降级到规则匹配
            return self._rule_based_recognition(user_message, context)

    async def _llm_recognition(
        self,
        user_message: str,
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        使用 LLM 识别意图

        Args:
            user_message: 用户消息
            context: 上下文信息

        Returns:
            Dict: 意图识别结果
        """
        # 构建提示词
        intent_descriptions = "\n".join([
            f"- {intent}: {description}"
            for intent, description in self.INTENTS.items()
        ])

        prompt = f"""你是一个智能客服助手的意图识别器。请分析用户消息并识别其意图。

支持的意图类型:
{intent_descriptions}

用户消息: {user_message}

请以 JSON 格式返回结果:
{{
    "intent": "意图类型",
    "confidence": 0.0-1.0,
    "parameters": {{"key": "value"}},
    "reasoning": "推理过程"
}}

注意:
1. confidence 必须在 0-1 之间
2. parameters 应该提取用户提到的参数（如时间范围、指标名称等）
3. reasoning 简要说明为什么选择这个意图
"""

        try:
            # 调用智谱 AI API（旧版）
            response = zhipuai.model_api.invoke(
                model=self.model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,  # 低温度以获得确定性结果
                top_p=0.7,
            )

            # 检查响应状态
            if response['code'] != 200:
                raise ValueError(f"智谱 AI API 错误: {response.get('msg', 'Unknown error')}")

            # 解析响应
            result_text = response['data']['choices'][0]['message']['content'].strip()

            # 移除可能的 markdown 代码块标记
            if result_text.startswith("```json"):
                result_text = result_text[7:]
            if result_text.startswith("```"):
                result_text = result_text[3:]
            if result_text.endswith("```"):
                result_text = result_text[:-3]

            result = json.loads(result_text)

            # 验证返回值
            if result.get("intent") not in self.INTENTS:
                raise ValueError(f"无效的意图: {result.get('intent')}")

            confidence = float(result.get("confidence", 0.5))
            confidence = max(0.0, min(1.0, confidence))  # 限制在 0-1 之间

            logger.info(f"LLM 意图识别: {result.get('intent')} (置信度: {confidence})")

            return {
                "intent": result.get("intent"),
                "confidence": confidence,
                "parameters": result.get("parameters", {}),
                "reasoning": result.get("reasoning", "")
            }

        except Exception as e:
            logger.error(f"LLM 意图识别失败: {e}")
            raise

    def _rule_based_recognition(
        self,
        user_message: str,
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        基于规则的意图识别（降级方案）

        Args:
            user_message: 用户消息
            context: 上下文信息

        Returns:
            Dict: 意图识别结果
        """
        message_lower = user_message.lower()

        # 关键词匹配
        keywords = {
            "query_metrics": ["查询", "指标", "销售额", "用户数", "订单量", "多少", "统计"],
            "generate_report": ["报表", "导出", "csv", "json", "生成", "下载"],
            "analyze_root_cause": ["异常", "下降", "上涨", "原因", "分析", "为什么", "根因"],
            "chat": ["你好", "谢谢", "再见", "哈哈", "嗯"]
        }

        # 计算每个意图的匹配分数
        scores = {}
        for intent, words in keywords.items():
            score = sum(1 for word in words if word in message_lower)
            scores[intent] = score

        # 选择最高分的意图
        max_score = max(scores.values())
        if max_score == 0:
            intent = "chat"
            confidence = 0.3
        else:
            # 找到最高分的意图
            intent = max(scores, key=scores.get)
            # 归一化置信度 (0.5-0.9)
            confidence = min(0.9, 0.5 + (max_score / len(keywords[intent])) * 0.4)

        logger.info(f"规则匹配意图识别: {intent} (置信度: {confidence})")

        return {
            "intent": intent,
            "confidence": confidence,
            "parameters": {},
            "reasoning": f"基于关键词匹配，得分: {max_score}"
        }

    def get_skill_mapping(self, intent: str) -> list:
        """
        根据意图获取需要调用的 Skills

        Args:
            intent: 意图类型

        Returns:
            List[str]: Skill 名称列表
        """
        mapping = {
            "query_metrics": ["QueryMetricsSkill"],
            "generate_report": ["GenerateReportSkill"],
            "analyze_root_cause": ["AnalyzeRootCauseSkill"],
            "chat": []
        }

        return mapping.get(intent, [])
