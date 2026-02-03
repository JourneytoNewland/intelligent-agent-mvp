"""
配置管理模块

使用 Pydantic Settings 管理应用配置，支持从环境变量加载
"""
from typing import List, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置类"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # ========== 应用配置 ==========
    app_name: str = Field(default="IntelligentAgentMVP", description="应用名称")
    app_version: str = Field(default="0.1.0", description="应用版本")
    environment: str = Field(default="development", description="运行环境")
    debug: bool = Field(default=False, description="调试模式")
    log_level: str = Field(default="INFO", description="日志级别")

    # ========== 服务器配置 ==========
    host: str = Field(default="0.0.0.0", description="服务器地址")
    port: int = Field(default=8000, description="服务器端口")

    # ========== 数据库配置 ==========
    database_url: str = Field(
        default="postgresql://postgres:postgres123@localhost:5432/agent_db",
        description="数据库连接 URL"
    )
    database_pool_size: int = Field(default=10, description="数据库连接池大小")
    database_max_overflow: int = Field(default=20, description="连接池最大溢出")

    # ========== Redis 配置 ==========
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis 连接 URL"
    )
    redis_max_connections: int = Field(default=50, description="Redis 最大连接数")

    # ========== LLM 配置 ==========
    # 智谱 AI
    zhipuai_api_key: Optional[str] = Field(default=None, description="智谱AI API Key")
    zhipuai_model: str = Field(default="glm-4", description="智谱AI 模型名称")

    # OpenAI (可选)
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API Key")
    openai_model: str = Field(default="gpt-4o", description="OpenAI 模型名称")

    # Anthropic (可选)
    anthropic_api_key: Optional[str] = Field(default=None, description="Anthropic API Key")
    anthropic_model: str = Field(
        default="claude-3-5-sonnet-20241022",
        description="Anthropic 模型名称"
    )

    # ========== Langfuse 配置 ==========
    langfuse_public_key: Optional[str] = Field(default=None, description="Langfuse 公钥")
    langfuse_secret_key: Optional[str] = Field(default=None, description="Langfuse 私钥")
    langfuse_host: str = Field(
        default="https://cloud.langfuse.com",
        description="Langfuse 服务器地址"
    )

    # ========== OpenTelemetry 配置 ==========
    otel_exporter_otlp_endpoint: str = Field(
        default="http://localhost:4317",
        description="OpenTelemetry OTLP 导出器端点"
    )
    otel_service_name: str = Field(
        default="intelligent-agent-mvp",
        description="OpenTelemetry 服务名称"
    )
    otel_exporter_otlp_protocol: str = Field(
        default="grpc",
        description="OpenTelemetry 导出协议"
    )

    # ========== 安全配置 ==========
    secret_key: str = Field(
        default="your-secret-key-change-this-in-production",
        description="应用密钥"
    )
    access_token_expire_minutes: int = Field(
        default=30,
        description="访问令牌过期时间（分钟）"
    )

    # ========== CORS 配置 ==========
    cors_origins_str: str = Field(
        default='["http://localhost:3000","http://localhost:8000"]',
        description="CORS 允许的源（JSON 字符串）",
        alias="cors_origins"
    )

    @property
    def cors_origins(self) -> List[str]:
        """解析 CORS 源列表"""
        try:
            import json
            return json.loads(self.cors_origins_str)
        except (json.JSONDecodeError, TypeError):
            return ["http://localhost:3000", "http://localhost:8000"]

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """验证日志级别"""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"日志级别必须是以下之一: {valid_levels}")
        return v.upper()

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """验证运行环境"""
        valid_envs = ["development", "testing", "production"]
        if v not in valid_envs:
            raise ValueError(f"环境必须是以下之一: {valid_envs}")
        return v

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """验证数据库 URL 格式"""
        if not v.startswith(("postgresql://", "postgresql+asyncpg://")):
            raise ValueError("数据库 URL 必须以 postgresql:// 或 postgresql+asyncpg:// 开头")
        return v

    def get_llm_config(self, provider: str = "zhipuai") -> dict:
        """
        获取 LLM 配置

        Args:
            provider: LLM 提供商 (zhipuai, openai, anthropic)

        Returns:
            LLM 配置字典
        """
        configs = {
            "zhipuai": {
                "api_key": self.zhipuai_api_key,
                "model": self.zhipuai_model,
            },
            "openai": {
                "api_key": self.openai_api_key,
                "model": self.openai_model,
            },
            "anthropic": {
                "api_key": self.anthropic_api_key,
                "model": self.anthropic_model,
            }
        }

        config = configs.get(provider)
        if not config or not config.get("api_key"):
            raise ValueError(f"LLM 提供商 '{provider}' 的 API Key 未配置")

        return config


# 全局配置实例
settings = Settings()


def get_settings() -> Settings:
    """
    获取配置实例（依赖注入用）

    Returns:
        Settings: 配置实例
    """
    return settings
