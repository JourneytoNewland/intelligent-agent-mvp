"""
健康检查相关的 Pydantic 模型
"""
from pydantic import BaseModel
from typing import Optional


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    version: str
    environment: str
    database: str
    redis: str
    langfuse: Optional[str] = None


class ServiceStatus(BaseModel):
    """服务状态"""
    name: str
    status: str
    latency_ms: Optional[float] = None
    error: Optional[str] = None
