"""
HTTP 请求 MCP 工具

提供异步 HTTP 客户端功能，支持超时、重试和错误处理
"""
import asyncio
import logging
from typing import Any, Dict, Optional
import httpx
from pydantic import Field

from .base import BaseMCPTool, MCPToolInput, MCPToolOutput

logger = logging.getLogger(__name__)


class HttpRequestInput(MCPToolInput):
    """HTTP 请求输入"""
    url: str = Field(description="请求 URL")
    method: str = Field(default="GET", description="HTTP 方法: GET/POST/PUT/DELETE")
    headers: Optional[Dict[str, str]] = Field(default=None, description="请求头")
    body: Optional[str] = Field(default=None, description="请求体")
    timeout: float = Field(default=30.0, description="超时时间（秒）")
    retries: int = Field(default=3, description="重试次数")


class HttpRequestTool(BaseMCPTool):
    """
    HTTP 请求工具

    提供：
    - 异步 HTTP 客户端
    - 超时控制
    - 自动重试（指数退避）
    - 响应日志记录
    """

    def __init__(self):
        super().__init__()
        self.description = "发送 HTTP 请求，支持 GET/POST/PUT/DELETE，自动重试和超时控制"
        self.input_schema = HttpRequestInput
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """获取或创建 HTTP 客户端"""
        if self._client is None:
            # 配置超时和重试限制
            limits = httpx.Limits(
                max_keepalive_connections=10,
                keepalive_expiry=30.0
            )

            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(60.0),
                limits=limits,
                follow_redirects=True
            )
        return self._client

    async def execute(
        self,
        input_data: HttpRequestInput,
        context: Optional[Dict[str, Any]] = None
    ) -> MCPToolOutput:
        """
        执行 HTTP 请求

        Args:
            input_data: 请求输入（URL、方法、头等）
            context: 上下文信息

        Returns:
            MCPToolOutput: 请求结果
        """
        try:
            # 验证输入
            self._validate_input(input_data)

            # 执行请求（带重试）
            response = await self._execute_with_retry(
                input_data.url,
                input_data.method,
                input_data.headers,
                input_data.body,
                input_data.timeout,
                input_data.retries
            )

            # 解析响应
            result = await self._parse_response(response)

            return MCPToolOutput(
                success=True,
                data=result,
                metadata={
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "url": str(response.url)
                }
            )

        except httpx.TimeoutException as e:
            logger.error(f"请求超时: {input_data.url}")
            return MCPToolOutput(
                success=False,
                error=f"请求超时: {str(e)}"
            )
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP 错误: {e.response.status_code}")
            return MCPToolOutput(
                success=False,
                error=f"HTTP 错误: {e.response.status_code} - {e.response.text[:200]}"
            )
        except Exception as e:
            logger.error(f"请求失败: {e}")
            return MCPToolOutput(
                success=False,
                error=f"请求失败: {str(e)}"
            )

    def _validate_input(self, input_data: HttpRequestInput) -> None:
        """
        验证输入参数

        Args:
            input_data: 请求输入

        Raises:
            ValueError: 如果输入不合法
        """
        # 验证 URL
        if not input_data.url.startswith(("http://", "https://")):
            raise ValueError(f"无效的 URL: {input_data.url}")

        # 验证 HTTP 方法
        valid_methods = ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]
        if input_data.method.upper() not in valid_methods:
            raise ValueError(f"不支持的 HTTP 方法: {input_data.method}")

        # 验证超时时间
        if input_data.timeout <= 0 or input_data.timeout > 300:
            raise ValueError("超时时间必须在 1-300 秒之间")

    async def _execute_with_retry(
        self,
        url: str,
        method: str,
        headers: Optional[Dict[str, str]],
        body: Optional[str],
        timeout: float,
        max_retries: int
    ) -> httpx.Response:
        """
        执行 HTTP 请求（带重试）

        Args:
            url: 请求 URL
            method: HTTP 方法
            headers: 请求头
            body: 请求体
            timeout: 超时时间
            max_retries: 最大重试次数

        Returns:
            httpx.Response: HTTP 响应
        """
        client = await self._get_client()
        method = method.upper()

        # 准备请求参数
        request_kwargs = {
            "url": url,
            "method": method,
            "headers": headers or {},
            "timeout": timeout
        }

        # 添加请求体（对于需要的方法）
        if method in ["POST", "PUT", "PATCH"]:
            if body:
                request_kwargs["content"] = body.encode()

        # 执行请求（带重试）
        last_error = None
        for attempt in range(max_retries + 1):
            try:
                response = await client.request(**request_kwargs)

                # 某些状态码可以重试（如 429 Too Many Requests）
                if response.status_code in [429, 502, 503, 504] and attempt < max_retries:
                    retry_after = response.headers.get("Retry-After")
                    if retry_after:
                        wait_time = float(retry_after)
                    else:
                        # 指数退避
                        wait_time = (2 ** attempt) + 1

                    logger.warning(f"请求失败 (状态码: {response.status_code})，{wait_time}秒后重试...")
                    await asyncio.sleep(wait_time)
                    continue

                return response

            except (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.TimeoutException) as e:
                last_error = e
                if attempt < max_retries:
                    wait_time = (2 ** attempt) + 1
                    logger.warning(f"请求超时，{wait_time}秒后重试...")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    raise

        # 所有重试都失败
        raise last_error

    async def _parse_response(self, response: httpx.Response) -> Dict[str, Any]:
        """
        解析 HTTP 响应

        Args:
            response: HTTP 响应

        Returns:
            Dict[str, Any]: 解析后的响应数据
        """
        try:
            # 尝试解析为 JSON
            content_type = response.headers.get("content-type", "")
            if "application/json" in content_type:
                return {
                    "data": response.json(),
                    "content_type": content_type
                }
            else:
                # 返回文本内容
                return {
                    "data": response.text,
                    "content_type": content_type,
                    "size": len(response.content)
                }
        except Exception as e:
            logger.error(f"响应解析失败: {e}")
            return {
                "data": response.text[:1000],  # 限制长度
                "content_type": response.headers.get("content-type", ""),
                "parse_error": str(e)
            }

    async def close(self):
        """关闭 HTTP 客户端"""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()
