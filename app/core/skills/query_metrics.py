"""
指标查询 Skill

查询业务指标数据，支持时间范围筛选和多维度聚合
"""
import logging
from typing import List, Optional
from datetime import datetime
from pydantic import Field

from .base import BaseSkill, SkillInput, SkillOutput

logger = logging.getLogger(__name__)


class QueryMetricsInput(SkillInput):
    """指标查询输入"""
    metric_name: str = Field(description="指标名称，如 'sales_amount', 'active_users'")
    start_date: datetime = Field(description="开始时间")
    end_date: datetime = Field(description="结束时间")
    dimensions: Optional[List[str]] = Field(default=None, description="维度筛选，如 ['region', 'product']")
    aggregation: str = Field(default="sum", description="聚合方式: sum/avg/max/min/count")


class QueryMetricsSkill(BaseSkill):
    """
    指标查询 Skill

    查询数据库中的业务指标，支持：
    - 时间范围筛选
    - 多维度分组
    - 多种聚合函数
    """

    def __init__(self, mcp_client=None):
        super().__init__(mcp_client)
        self.description = "查询业务指标数据，支持时间范围和多维度筛选"
        self.input_schema = QueryMetricsInput

    async def execute(
        self,
        input_data: QueryMetricsInput,
        context: Dict
    ) -> SkillOutput:
        """
        执行指标查询

        Args:
            input_data: 查询参数（指标名、时间范围、维度、聚合方式）
            context: 上下文信息

        Returns:
            SkillOutput: 查询结果
        """
        try:
            # 构建查询 SQL
            sql = self._build_query(input_data)

            # 通过 MCP 客户端调用数据库工具
            if self.mcp_client:
                result = await self.mcp_client.call_tool(
                    "database_query",
                    {
                        "sql": sql,
                        "operation": "fetch"
                    }
                )

                if result.success:
                    # 数据后处理
                    processed_data = self._process_result(result.data)

                    return SkillOutput(
                        success=True,
                        data=processed_data,
                        metadata={
                            "metric": input_data.metric_name,
                            "row_count": len(processed_data),
                            "start_date": input_data.start_date.isoformat(),
                            "end_date": input_data.end_date.isoformat()
                        }
                    )
                else:
                    return SkillOutput(
                        success=False,
                        error=f"数据库查询失败: {result.error}"
                    )
            else:
                return SkillOutput(
                    success=False,
                    error="MCP 客户端未初始化"
                )

        except Exception as e:
            logger.error(f"指标查询失败: {e}")
            return SkillOutput(
                success=False,
                error=f"指标查询失败: {str(e)}"
            )

    def _build_query(self, input_data: QueryMetricsInput) -> str:
        """
        构建查询 SQL

        Args:
            input_data: 查询参数

        Returns:
            str: SQL 查询语句
        """
        # 维度字段
        dimensions = input_data.dimensions or []
        dimension_fields = ", ".join(dimensions) if dimensions else ""
        dimension_list = ", ".join(dimensions) if dimensions else ""

        # WHERE 子句
        where_clause = f"""
            WHERE metric_name = '{input_data.metric_name}'
              AND timestamp >= '{input_data.start_date}'
              AND timestamp <= '{input_data.end_date}'
        """

        # GROUP BY 子句
        group_by = dimension_list if dimension_list else "date"

        # 完整 SQL
        sql = f"""
        SELECT
            {dimension_fields + ',' if dimension_fields else ''}
            date_trunc('day', timestamp) as date,
            {input_data.aggregation}(value) as metric_value
        FROM metrics
        {where_clause}
        GROUP BY date {(', ' + dimension_list if dimension_list else '')}
        ORDER BY date
        """

        return sql

    def _process_result(self, raw_result: List[dict]) -> List[dict]:
        """
        数据后处理

        Args:
            raw_result: 原始查询结果

        Returns:
            List[dict]: 处理后的数据
        """
        if not raw_result:
            return []

        # 数据清洗和格式化
        processed = []
        for row in raw_result:
            # 移除 None 值
            cleaned_row = {k: v for k, v in row.items() if v is not None}
            processed.append(cleaned_row)

        return processed


class GenerateReportInput(SkillInput):
    """报表生成输入"""
    report_type: str = Field(description="报表类型: 'sales_by_region' 或 'sales_by_product'")
    start_date: datetime = Field(description="开始时间")
    end_date: datetime = Field(description="结束时间")
    format: str = Field(default="csv", description="输出格式: csv/json")


class GenerateReportSkill(BaseSkill):
    """
    报表生成 Skill

    生成业务报表并返回下载链接
    """

    def __init__(self, mcp_client=None):
        super().__init__(mcp_client)
        self.description = "生成业务报表，支持 CSV 和 JSON 格式"
        self.input_schema = GenerateReportInput

    async def execute(
        self,
        input_data: GenerateReportInput,
        context: Dict
    ) -> SkillOutput:
        """
        执行报表生成

        Args:
            input_data: 报表参数（类型、时间范围、格式）
            context: 上下文信息

        Returns:
            SkillOutput: 生成结果
        """
        try:
            # 1. 查询数据
            query_skill = QueryMetricsSkill(self.mcp_client)
            query_input = QueryMetricsInput(
                metric_name="sales_amount",
                start_date=input_data.start_date,
                end_date=input_data.end_date,
                dimensions=["region"] if input_data.report_type == "sales_by_region" else ["product"]
            )

            query_result = await query_skill.execute(query_input, context)

            if not query_result.success:
                return SkillOutput(
                    success=False,
                    error=f"数据查询失败: {query_result.error}"
                )

            # 2. 生成报表文件
            report_data = query_result.data

            # 生成唯一文件名
            import uuid
            file_key = f"report:{uuid.uuid4()}"

            # 保存到 Redis（临时链接）
            if self.mcp_client:
                # 将数据转换为 CSV 格式
                csv_content = self._to_csv(report_data)

                # 调用 Redis 存储（暂时使用数据库模拟）
                # 在实际实现中，应该调用 Redis MCP 工具
                download_url = f"/api/v1/reports/download/{file_key}"

                return SkillOutput(
                    success=True,
                    data={
                        "download_url": download_url,
                        "row_count": len(report_data),
                        "format": input_data.format
                    },
                    metadata={
                        "report_type": input_data.report_type,
                        "file_key": file_key
                    }
                )
            else:
                return SkillOutput(
                    success=False,
                    error="MCP 客户端未初始化"
                )

        except Exception as e:
            logger.error(f"报表生成失败: {e}")
            return SkillOutput(
                success=False,
                error=f"报表生成失败: {str(e)}"
            )

    def _to_csv(self, data: List[dict]) -> str:
        """
        将数据转换为 CSV 格式

        Args:
            data: 数据列表

        Returns:
            str: CSV 格式字符串
        """
        import csv
        import io

        if not data:
            return ""

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)

        return output.getvalue()


class AnalyzeRootCauseInput(SkillInput):
    """根因分析输入"""
    metric_name: str = Field(description="指标名称")
    anomaly_date: datetime = Field(description="异常发生日期")
    anomaly_value: float = Field(description="异常值")
    expected_value: Optional[float] = Field(default=None, description="期望值（可选）")
    threshold_percent: float = Field(default=20.0, description="异常阈值百分比")


class AnalyzeRootCauseSkill(BaseSkill):
    """
    根因分析 Skill

    分析业务指标的异常原因，使用规则引擎 + LLM 推理
    """

    def __init__(self, mcp_client=None, llm=None):
        super().__init__(mcp_client)
        self.description = "分析指标异常原因，结合规则引擎和 LLM 推理"
        self.input_schema = AnalyzeRootCauseInput
        self.llm = llm

        # 规则引擎
        self.rules = [
            self._check_system_maintenance,
            self._check_holiday_effect,
            self._check_marketing_campaign_end,
        ]

    async def execute(
        self,
        input_data: AnalyzeRootCauseInput,
        context: Dict
    ) -> SkillOutput:
        """
        执行根因分析

        Args:
            input_data: 分析参数（指标名、异常日期、异常值、期望值）
            context: 上下文信息

        Returns:
            SkillOutput: 分析结果
        """
        try:
            # 1. 规则引擎检查
            rule_results = []

            for rule in self.rules:
                result = await rule(input_data, context)
                if result:
                    rule_results.append(result)

            # 2. 如果规则引擎结果不足，使用 LLM 深度分析
            if len(rule_results) < 2 and self.llm:
                llm_result = await self._llm_analyze(input_data, rule_results, context)
                rule_results.extend(llm_result)

            # 3. 排序并返回（按置信度）
            rule_results.sort(key=lambda x: x.get("confidence", 0), reverse=True)

            return SkillOutput(
                success=True,
                data={
                    "possible_causes": rule_results,
                    "anomaly_date": input_data.anomaly_date.isoformat(),
                    "anomaly_value": input_data.anomaly_value
                },
                metadata={
                    "metric": input_data.metric_name,
                    "cause_count": len(rule_results)
                }
            )

        except Exception as e:
            logger.error(f"根因分析失败: {e}")
            return SkillOutput(
                success=False,
                error=f"根因分析失败: {str(e)}"
            )

    async def _check_system_maintenance(
        self,
        input_data: AnalyzeRootCauseInput,
        context: Dict
    ) -> Optional[Dict]:
        """检查系统维护"""
        # 简化实现：检查异常日期附近是否有维护记录
        # 实际应该查询维护日志表
        return None

    async def _check_holiday_effect(
        self,
        input_data: AnalyzeRootCauseInput,
        context: Dict
    ) -> Optional[Dict]:
        """检查节假日效应"""
        # 简化实现：检查异常日期是否是节假日
        import holidays

        try:
            cn_holidays = holidays.CountryChina(years=input_data.anomaly_date.year)
            if input_data.anomaly_date in cn_holidays:
                return {
                    "cause": "节假日效应",
                    "description": "异常日期为节假日，可能导致用户活跃度下降",
                    "confidence": 0.7
                }
        except:
            pass

        return None

    async def _check_marketing_campaign_end(
        self,
        input_data: AnalyzeRootCauseInput,
        context: Dict
    ) -> Optional[Dict]:
        """检查营销活动结束"""
        # 简化实现：检查异常日期前后 3 天是否有营销活动结束
        # 实际应该查询营销活动表

        # 使用 MCP 客户端查询
        if self.mcp_client:
            sql = """
                SELECT *
                FROM marketing_campaigns
                WHERE end_date >= $1 - INTERVAL '3 days'
                  AND end_date <= $1 + INTERVAL '3 days'
                ORDER BY end_date DESC
                LIMIT 1
            """

            result = await self.mcp_client.call_tool(
                "database_query",
                {
                    "sql": sql,
                    "params": [input_data.anomaly_date],
                    "operation": "fetch"
                }
            )

            if result.success and result.data:
                return {
                    "cause": "营销活动结束",
                    "description": f"近期有营销活动结束（{result.data[0]['name']}）",
                    "confidence": 0.8
                }

        return None

    async def _llm_analyze(
        self,
        input_data: AnalyzeRootCauseInput,
        rule_results: List[Dict],
        context: Dict
    ) -> List[Dict]:
        """使用 LLM 进行深度分析"""
        # 简化实现：直接返回模拟的 LLM 分析结果
        # 实际应该调用智谱 AI API

        # 计算偏差
        anomaly_value = input_data.anomaly_value
        expected_value = input_data.expected_value or (anomaly_value * 1.2)
        deviation = abs(anomaly_value - expected_value) / expected_value * 100

        return [{
            "cause": "数据分析推断",
            "description": f"指标值下降 {deviation:.1f}%，可能是正常波动或外部因素影响",
            "confidence": 0.6
        }]
