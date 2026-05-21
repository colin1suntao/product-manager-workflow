"""HTTP 请求工具

提供 HTTP GET/POST 请求能力，支持公网访问。
"""

import asyncio
import logging
import time
from typing import Optional

import aiohttp

from pm_workstation.sandbox.models import (
    ToolCategory,
    ToolDefinition,
    ToolResult,
    Workspace,
)
from pm_workstation.sandbox.security_controller import (
    SecurityController,
    get_security_controller,
)

logger = logging.getLogger(__name__)


class HTTPTools:
    """HTTP 请求工具集合"""
    
    TOOLS = [
        ToolDefinition(
            name="http_get",
            description="发送 HTTP GET 请求",
            parameters={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "请求 URL"},
                    "headers": {"type": "object", "description": "请求头"},
                    "timeout": {"type": "integer", "description": "超时时间（秒）"},
                },
                "required": ["url"],
            },
            returns={
                "type": "object",
                "properties": {
                    "status": {"type": "integer"},
                    "body": {"type": "string"},
                },
            },
            timeout=30,
            category=ToolCategory.HTTP,
        ),
        ToolDefinition(
            name="http_post",
            description="发送 HTTP POST 请求",
            parameters={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "请求 URL"},
                    "body": {"type": "object", "description": "请求体"},
                    "headers": {"type": "object", "description": "请求头"},
                    "timeout": {"type": "integer", "description": "超时时间（秒）"},
                },
                "required": ["url", "body"],
            },
            returns={
                "type": "object",
                "properties": {
                    "status": {"type": "integer"},
                    "body": {"type": "string"},
                },
            },
            timeout=30,
            category=ToolCategory.HTTP,
        ),
    ]
    
    DEFAULT_TIMEOUT = 30
    MAX_RESPONSE_SIZE = 5 * 1024 * 1024
    
    def __init__(
        self,
        security_controller: Optional[SecurityController] = None,
    ):
        self.security_controller = security_controller or get_security_controller()
    
    async def get(
        self,
        workspace: Workspace,
        params: dict,
    ) -> ToolResult:
        """发送 GET 请求"""
        start_time = time.time()
        
        url = params.get("url", "")
        headers = params.get("headers", {})
        timeout = params.get("timeout", self.DEFAULT_TIMEOUT)
        
        validation = self.security_controller.validate_url(url, allow_public_network=True)
        if not validation.valid:
            return ToolResult(
                tool_name="http_get",
                success=False,
                error=f"URL blocked: {validation.reason}",
                execution_time_ms=int((time.time() - start_time) * 1000),
            )
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=timeout),
                ) as response:
                    status = response.status
                    
                    content = await response.content.read()
                    
                    if len(content) > self.MAX_RESPONSE_SIZE:
                        content = content[:self.MAX_RESPONSE_SIZE]
                        body = content.decode("utf-8", errors="replace") + "... [truncated]"
                    else:
                        try:
                            body = content.decode("utf-8")
                        except UnicodeDecodeError:
                            body = f"Binary content ({len(content)} bytes)"
                    
                    return ToolResult(
                        tool_name="http_get",
                        success=status < 400,
                        output=f"Status: {status}\nBody: {body[:2000]}",
                        metadata={
                            "status": status,
                            "body": body,
                            "headers": dict(response.headers),
                            "url": url,
                        },
                        execution_time_ms=int((time.time() - start_time) * 1000),
                    )
        
        except asyncio.TimeoutError:
            return ToolResult(
                tool_name="http_get",
                success=False,
                error=f"Request timed out after {timeout}s",
                execution_time_ms=int((time.time() - start_time) * 1000),
            )
        except aiohttp.ClientError as e:
            logger.error(f"http_get failed: {e}")
            return ToolResult(
                tool_name="http_get",
                success=False,
                error=f"Request failed: {str(e)}",
                execution_time_ms=int((time.time() - start_time) * 1000),
            )
        except Exception as e:
            logger.error(f"http_get failed: {e}")
            return ToolResult(
                tool_name="http_get",
                success=False,
                error=str(e),
                execution_time_ms=int((time.time() - start_time) * 1000),
            )
    
    async def post(
        self,
        workspace: Workspace,
        params: dict,
    ) -> ToolResult:
        """发送 POST 请求"""
        start_time = time.time()
        
        url = params.get("url", "")
        body = params.get("body", {})
        headers = params.get("headers", {})
        timeout = params.get("timeout", self.DEFAULT_TIMEOUT)
        
        validation = self.security_controller.validate_url(url, allow_public_network=True)
        if not validation.valid:
            return ToolResult(
                tool_name="http_post",
                success=False,
                error=f"URL blocked: {validation.reason}",
                execution_time_ms=int((time.time() - start_time) * 1000),
            )
        
        if "Content-Type" not in headers:
            headers["Content-Type"] = "application/json"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=body,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=timeout),
                ) as response:
                    status = response.status
                    
                    content = await response.content.read()
                    
                    if len(content) > self.MAX_RESPONSE_SIZE:
                        content = content[:self.MAX_RESPONSE_SIZE]
                        response_body = content.decode("utf-8", errors="replace") + "... [truncated]"
                    else:
                        try:
                            response_body = content.decode("utf-8")
                        except UnicodeDecodeError:
                            response_body = f"Binary content ({len(content)} bytes)"
                    
                    return ToolResult(
                        tool_name="http_post",
                        success=status < 400,
                        output=f"Status: {status}\nResponse: {response_body[:2000]}",
                        metadata={
                            "status": status,
                            "body": response_body,
                            "headers": dict(response.headers),
                            "url": url,
                            "request_body": body,
                        },
                        execution_time_ms=int((time.time() - start_time) * 1000),
                    )
        
        except asyncio.TimeoutError:
            return ToolResult(
                tool_name="http_post",
                success=False,
                error=f"Request timed out after {timeout}s",
                execution_time_ms=int((time.time() - start_time) * 1000),
            )
        except aiohttp.ClientError as e:
            logger.error(f"http_post failed: {e}")
            return ToolResult(
                tool_name="http_post",
                success=False,
                error=f"Request failed: {str(e)}",
                execution_time_ms=int((time.time() - start_time) * 1000),
            )
        except Exception as e:
            logger.error(f"http_post failed: {e}")
            return ToolResult(
                tool_name="http_post",
                success=False,
                error=str(e),
                execution_time_ms=int((time.time() - start_time) * 1000),
            )


_global_http_tools: Optional[HTTPTools] = None


def get_http_tools() -> HTTPTools:
    """获取全局 HTTP 工具实例"""
    global _global_http_tools
    if _global_http_tools is None:
        _global_http_tools = HTTPTools()
    return _global_http_tools