"""
HTTP API 数据源 MCP 工具
支持调用第三方 API 获取数据
"""

import httpx
from typing import Optional, Dict, Any, List
import logging
from datetime import datetime
import json
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ToolResult(BaseModel):
    """工具执行结果"""
    success: bool = Field(..., description="执行是否成功")
    data: Optional[Any] = Field(default=None, description="返回数据")
    message: Optional[str] = Field(default=None, description="执行消息")
    error: Optional[str] = Field(default=None, description="错误信息")


class APIDatasourceTool:
    """
    HTTP API 数据源工具

    功能：
    1. 调用 RESTful API 获取数据
    2. 支持 GET/POST/PUT/DELETE 方法
    3. 自动处理认证（Bearer Token, API Key）
    4. 支持请求/响应转换
    5. 错误重试和超时控制
    """

    name = "api_datasource"
    description = "调用第三方 HTTP API 获取数据"

    def __init__(
        self,
        default_timeout: float = 10.0,
        max_retries: int = 3
    ):
        # super().__init__()
        self.default_timeout = default_timeout
        self.max_retries = max_retries

        # API 配置注册表
        # 格式: {"api_name": {"base_url": "...", "auth_type": "...", "auth_value": "..."}}
        self.api_configs = {}

    def register_api(
        self,
        name: str,
        base_url: str,
        auth_type: Optional[str] = None,
        auth_value: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None
    ):
        """
        注册 API 配置

        Args:
            name: API 名称
            base_url: 基础 URL
            auth_type: 认证类型（bearer/api_key/basic）
            auth_value: 认证值
            headers: 默认请求头
        """
        self.api_configs[name] = {
            "base_url": base_url,
            "auth_type": auth_type,
            "auth_value": auth_value,
            "headers": headers or {}
        }
        logger.info(f"注册 API: {name} -> {base_url}")

    async def call_api(
        self,
        api_name: str,
        endpoint: str,
        method: str = "GET",
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> ToolResult:
        """
        调用已注册的 API

        Args:
            api_name: API 名称（已注册）
            endpoint: 端点路径（如 /users/123）
            method: HTTP 方法
            params: URL 查询参数
            data: 请求体数据
            headers: 额外请求头

        Returns:
            ToolResult: API 响应数据
        """
        if api_name not in self.api_configs:
            return ToolResult(
                success=False,
                error=f"API 未注册: {api_name}"
            )

        config = self.api_configs[api_name]
        url = config["base_url"] + endpoint

        # 构建请求头
        request_headers = config["headers"].copy()
        if headers:
            request_headers.update(headers)

        # 添加认证
        if config["auth_type"] == "bearer":
            request_headers["Authorization"] = f"Bearer {config['auth_value']}"
        elif config["auth_type"] == "api_key":
            request_headers["X-API-Key"] = config["auth_value"]

        return await self._make_request(
            url=url,
            method=method,
            params=params,
            data=data,
            headers=request_headers
        )

    async def call_url(
        self,
        url: str,
        method: str = "GET",
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        auth: Optional[Dict[str, str]] = None
    ) -> ToolResult:
        """
        直接调用 URL

        Args:
            url: 完整 URL
            method: HTTP 方法
            params: 查询参数
            data: 请求体
            headers: 请求头
            auth: 认证信息 {"type": "bearer", "value": "token"}

        Returns:
            ToolResult: API 响应
        """
        request_headers = headers or {}

        # 添加认证
        if auth:
            if auth["type"] == "bearer":
                request_headers["Authorization"] = f"Bearer {auth['value']}"
            elif auth["type"] == "api_key":
                request_headers["X-API-Key"] = auth["value"]

        return await self._make_request(
            url=url,
            method=method,
            params=params,
            data=data,
            headers=request_headers
        )

    async def _make_request(
        self,
        url: str,
        method: str = "GET",
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> ToolResult:
        """
        执行 HTTP 请求（带重试）
        """
        retry_count = 0
        last_error = None

        async with httpx.AsyncClient(timeout=self.default_timeout) as client:
            while retry_count <= self.max_retries:
                try:
                    response = await client.request(
                        method=method,
                        url=url,
                        params=params,
                        json=data,
                        headers=headers
                    )

                    # 尝试解析 JSON 响应
                    try:
                        response_data = response.json()
                    except:
                        response_data = {"text": response.text}

                    # 判断是否成功
                    if 200 <= response.status_code < 300:
                        return ToolResult(
                            success=True,
                            data={
                                "status_code": response.status_code,
                                "data": response_data,
                                "headers": dict(response.headers)
                            },
                            message=f"API 调用成功: {response.status_code}"
                        )
                    else:
                        return ToolResult(
                            success=False,
                            error=f"HTTP {response.status_code}: {response_data}",
                            data={
                                "status_code": response.status_code,
                                "data": response_data
                            }
                        )

                except httpx.TimeoutException as e:
                    last_error = f"请求超时: {e}"
                    retry_count += 1
                    logger.warning(f"请求超时，重试 {retry_count}/{self.max_retries}: {url}")

                except httpx.HTTPError as e:
                    last_error = f"HTTP 错误: {e}"
                    break  # 非 HTTP 错误不重试

                except Exception as e:
                    last_error = f"未知错误: {e}"
                    break

        # 所有重试都失败
        return ToolResult(
            success=False,
            error=last_error or "请求失败"
        )

    async def get(
        self,
        api_name: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None
    ) -> ToolResult:
        """便捷方法：GET 请求"""
        return await self.call_api(
            api_name=api_name,
            endpoint=endpoint,
            method="GET",
            params=params
        )

    async def post(
        self,
        api_name: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None
    ) -> ToolResult:
        """便捷方法：POST 请求"""
        return await self.call_api(
            api_name=api_name,
            endpoint=endpoint,
            method="POST",
            data=data
        )


# ============== 示例：注册常用 API ==============

def setup_common_apis(tool: APIDatasourceTool):
    """
    注册常用的第三方 API

    实际使用时，应该从配置文件或环境变量读取 API Key
    """
    # 示例：天气 API（需替换真实 API Key）
    tool.register_api(
        name="weather",
        base_url="https://api.weather.com/v1",
        auth_type="api_key",
        auth_value="your_api_key_here"
    )

    # 示例：新闻 API
    tool.register_api(
        name="news",
        base_url="https://newsapi.org/v2",
        auth_type="api_key",
        auth_value="your_news_api_key"
    )

    # 示例：内部业务 API
    tool.register_api(
        name="internal_api",
        base_url="http://internal-service/api",
        auth_type="bearer",
        auth_value="internal_token"
    )

    logger.info("常用 API 注册完成")
