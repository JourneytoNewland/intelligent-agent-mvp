"""
参数提取 Pydantic 模型
定义每个 Skill 的参数结构、验证规则和示例
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator
from enum import Enum


class MetricType(str, Enum):
    """指标类型枚举"""
    SALES = "sales"
    USER_COUNT = "user_count"
    ORDER_COUNT = "order_count"
    CONVERSION_RATE = "conversion_rate"
    ARPU = "arpu"
    CHURN_RATE = "churn_rate"


class TimeRange(str, Enum):
    """时间范围枚举"""
    TODAY = "today"
    YESTERDAY = "yesterday"
    LAST_7D = "7d"
    LAST_30D = "30d"
    LAST_90D = "90d"
    THIS_MONTH = "this_month"
    LAST_MONTH = "last_month"
    THIS_QUARTER = "this_quarter"
    THIS_YEAR = "this_year"


class Dimension(str, Enum):
    """维度枚举"""
    REGION = "region"
    PRODUCT = "product"
    CHANNEL = "channel"
    CATEGORY = "category"
    DATE = "date"
    USER_TYPE = "user_type"


class ReportFormat(str, Enum):
    """报表格式"""
    JSON = "json"
    CSV = "csv"
    EXCEL = "excel"


# ============== Skill 参数模型 ==============

class QueryMetricsParams(BaseModel):
    """查询指标参数"""
    metric: MetricType = Field(
        ...,
        description="要查询的指标名称"
    )
    time_range: TimeRange = Field(
        default=TimeRange.LAST_7D,
        description="时间范围"
    )
    dimensions: List[Dimension] = Field(
        default_factory=list,
        description="聚合维度，如按地区、产品分组"
    )
    filters: dict = Field(
        default_factory=dict,
        description="筛选条件，如 {'region': '华东', 'category': '电子产品'}"
    )
    limit: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="返回结果数量限制"
    )

    @field_validator('dimensions')
    @classmethod
    def validate_dimensions(cls, v):
        """验证维度组合的合理性"""
        if len(v) > 3:
            raise ValueError("最多支持3个维度组合")
        return v

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "metric": "sales",
                    "time_range": "7d",
                    "dimensions": ["region"],
                    "filters": {},
                    "limit": 50
                },
                {
                    "metric": "user_count",
                    "time_range": "30d",
                    "dimensions": ["region", "channel"],
                    "filters": {"region": "华东"},
                    "limit": 100
                }
            ]
        }


class GenerateReportParams(BaseModel):
    """生成报表参数"""
    report_type: str = Field(
        ...,
        description="报表类型：sales_report, user_report, product_report"
    )
    time_range: str = Field(
        ...,
        description="时间范围，如 2024-01, 2024-Q1, last_month"
    )
    dimensions: List[str] = Field(
        default_factory=list,
        description="报表包含的维度"
    )
    format: ReportFormat = Field(
        default=ReportFormat.CSV,
        description="导出格式"
    )
    include_charts: bool = Field(
        default=False,
        description="是否包含图表"
    )

    @field_validator('time_range')
    @classmethod
    def validate_time_range(cls, v):
        """验证时间范围格式"""
        # 支持格式：YYYY-MM, YYYY-QN, last_Nd, this_month 等
        import re
        patterns = [
            r'^\d{4}-\d{2}$',  # 2024-01
            r'^\d{4}-Q[1-4]$',  # 2024-Q1
            r'^last_(\d+)d$',  # last_7d
            r'^this_month$',  # this_month
        ]
        if not any(re.match(p, v) for p in patterns):
            raise ValueError(f"时间范围格式不支持: {v}")
        return v

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "report_type": "sales_report",
                    "time_range": "2024-01",
                    "dimensions": ["date", "product"],
                    "format": "csv",
                    "include_charts": True
                }
            ]
        }


class AnalyzeRootCauseParams(BaseModel):
    """根因分析参数"""
    metric: str = Field(
        ...,
        description="要分析的指标"
    )
    anomaly_time: str = Field(
        ...,
        description="异常时间点，如 yesterday, 2024-01-15"
    )
    baseline: str = Field(
        default="recent_avg",
        description="基准线计算方式：recent_avg, same_period_last_year, custom"
    )
    baseline_value: Optional[float] = Field(
        default=None,
        description="自定义基准值（当 baseline=custom 时使用）"
    )
    depth: int = Field(
        default=3,
        ge=1,
        le=5,
        description="分析深度（层级）"
    )

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "metric": "sales",
                    "anomaly_time": "yesterday",
                    "baseline": "recent_avg",
                    "depth": 3
                }
            ]
        }


# ============== Few-shot 示例库 ==============

FEWSHOT_EXAMPLES = {
    "query_metrics": [
        {
            "user_message": "查询最近7天的销售额",
            "expected_params": {
                "metric": "sales",
                "time_range": "7d",
                "dimensions": [],
                "filters": {}
            }
        },
        {
            "user_message": "过去30天按地区统计的用户数",
            "expected_params": {
                "metric": "user_count",
                "time_range": "30d",
                "dimensions": ["region"],
                "filters": {}
            }
        },
        {
            "user_message": "查看上季度华东地区的销售额，按产品分类",
            "expected_params": {
                "metric": "sales",
                "time_range": "this_quarter",
                "dimensions": ["region", "product"],
                "filters": {"region": "华东"}
            }
        },
        {
            "user_message": "今天的订单量是多少？",
            "expected_params": {
                "metric": "order_count",
                "time_range": "today",
                "dimensions": [],
                "filters": {}
            }
        },
        {
            "user_message": "本月的转化率，按渠道分组",
            "expected_params": {
                "metric": "conversion_rate",
                "time_range": "this_month",
                "dimensions": ["channel"],
                "filters": {}
            }
        }
    ],

    "generate_report": [
        {
            "user_message": "生成2024年1月的销售报表",
            "expected_params": {
                "report_type": "sales_report",
                "time_range": "2024-01",
                "dimensions": ["date", "product"],
                "format": "csv"
            }
        },
        {
            "user_message": "导出上季度用户分析报告到Excel",
            "expected_params": {
                "report_type": "user_report",
                "time_range": "last_quarter",
                "dimensions": ["region", "user_type"],
                "format": "excel"
            }
        }
    ],

    "analyze_root_cause": [
        {
            "user_message": "分析昨天销售额下降的原因",
            "expected_params": {
                "metric": "sales",
                "anomaly_time": "yesterday",
                "baseline": "recent_avg",
                "depth": 3
            }
        },
        {
            "user_message": "为什么2024-01-15的转化率突然降低？",
            "expected_params": {
                "metric": "conversion_rate",
                "anomaly_time": "2024-01-15",
                "baseline": "recent_avg",
                "depth": 3
            }
        }
    ]
}


# ============== 映射表 ==============

INTENT_TO_MODEL = {
    "query_metrics": QueryMetricsParams,
    "generate_report": GenerateReportParams,
    "analyze_root_cause": AnalyzeRootCauseParams,
}


def get_param_schema(intent: str) -> dict:
    """获取意图对应的参数 Schema（用于 Function Calling）"""
    model_class = INTENT_TO_MODEL.get(intent)
    if model_class:
        return model_class.model_json_schema()
    return {}


def validate_params(intent: str, params: dict) -> BaseModel:
    """验证并转换参数为 Pydantic 模型"""
    model_class = INTENT_TO_MODEL.get(intent)
    if not model_class:
        raise ValueError(f"未知的意图: {intent}")

    try:
        return model_class(**params)
    except Exception as e:
        raise ValueError(f"参数验证失败: {str(e)}")
