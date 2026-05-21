"""Sandbox 执行环境数据模型"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class ExecutionStatus(str, Enum):
    """执行状态"""
    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class ResourceLimits(BaseModel):
    """资源限制"""
    max_cpu_time: int = Field(default=60, description="最大 CPU 时间（秒）")
    max_memory_mb: int = Field(default=512, description="最大内存（MB）")
    max_file_size_mb: int = Field(default=10, description="最大文件大小（MB）")
    max_output_size_mb: int = Field(default=5, description="最大输出大小（MB）")
    max_concurrent_processes: int = Field(default=3, description="最大并发进程数")


class ResourceUsage(BaseModel):
    """资源使用统计"""
    cpu_time_seconds: float = Field(default=0.0, description="已用 CPU 时间")
    memory_mb: float = Field(default=0.0, description="已用内存")
    file_count: int = Field(default=0, description="文件数量")
    total_file_size_bytes: int = Field(default=0, description="文件总大小")


class Workspace(BaseModel):
    """工作区"""
    workspace_id: str
    execution_id: str
    path: str
    created_at: datetime
    file_count: int = Field(default=0)
    total_size_bytes: int = Field(default=0)


class FileInfo(BaseModel):
    """文件信息"""
    file_path: str
    file_name: str
    content_type: str = Field(default="text/plain")
    size_bytes: int
    created_at: datetime
    modified_at: datetime


class FileContent(BaseModel):
    """文件内容"""
    file_path: str
    content: str
    content_type: str
    size_bytes: int


class ToolCategory(str, Enum):
    """工具类别"""
    FILE = "file"
    SHELL = "shell"
    PYTHON = "python"
    HTTP = "http"
    UTILITY = "utility"


class SecurityLevel(str, Enum):
    """安全级别"""
    SAFE = "safe"
    NORMAL = "normal"
    RESTRICTED = "restricted"


class ToolDefinition(BaseModel):
    """工具定义"""
    name: str
    description: str
    parameters: dict = Field(default_factory=dict, description="JSON Schema 格式的参数定义")
    returns: dict = Field(default_factory=dict, description="JSON Schema 格式的返回定义")
    timeout: int = Field(default=30, description="超时时间（秒）")
    category: ToolCategory
    security_level: SecurityLevel = Field(default=SecurityLevel.NORMAL)


class ToolCall(BaseModel):
    """工具调用请求"""
    name: str
    params: dict = Field(default_factory=dict)


class ToolResult(BaseModel):
    """工具执行结果"""
    tool_name: str
    success: bool
    output: Optional[str] = None
    error: Optional[str] = None
    files_created: list[str] = Field(default_factory=list)
    files_modified: list[str] = Field(default_factory=list)
    execution_time_ms: int = Field(default=0)
    metadata: dict = Field(default_factory=dict)


class CommandResult(BaseModel):
    """命令执行结果"""
    command: str
    exit_code: int
    stdout: str
    stderr: str
    execution_time_ms: int = Field(default=0)
    timed_out: bool = Field(default=False)


class PythonResult(BaseModel):
    """Python 执行结果"""
    code: str
    stdout: str
    stderr: str
    return_value: Optional[Any] = None
    exception: Optional[str] = None
    execution_time_ms: int = Field(default=0)
    files_created: list[str] = Field(default_factory=list)


class HTTPResult(BaseModel):
    """HTTP 请求结果"""
    url: str
    method: str
    status_code: int
    body: str
    headers: dict = Field(default_factory=dict)
    execution_time_ms: int = Field(default=0)


class ExecutionEvent(str, Enum):
    """执行事件类型"""
    EXECUTION_STARTED = "execution_started"
    TOOL_STARTED = "tool_started"
    TOOL_PROGRESS = "tool_progress"
    TOOL_COMPLETED = "tool_completed"
    TOOL_FAILED = "tool_failed"
    FILE_CREATED = "file_created"
    FILE_MODIFIED = "file_modified"
    COMMAND_EXECUTED = "command_executed"
    RESOURCE_WARNING = "resource_warning"
    SECURITY_VIOLATION = "security_violation"
    EXECUTION_COMPLETED = "execution_completed"
    EXECUTION_FAILED = "execution_failed"


class SecurityValidation(BaseModel):
    """安全验证结果"""
    valid: bool
    reason: Optional[str] = None
    severity: str = Field(default="low", description="low, medium, high, critical")


class ExecutionContext(BaseModel):
    """执行上下文"""
    execution_id: str
    workspace_path: str
    task_params: dict = Field(default_factory=dict)
    created_at: datetime
    timeout: int = Field(default=60)
    resource_limits: ResourceLimits = Field(default_factory=ResourceLimits)
    status: ExecutionStatus = Field(default=ExecutionStatus.CREATED)
    tool_results: list[ToolResult] = Field(default_factory=list)
    artifacts: list[FileInfo] = Field(default_factory=list)
    error_message: Optional[str] = None
    cpu_time_used: float = Field(default=0.0)
    memory_used_mb: float = Field(default=0.0)


class ExecutionSummary(BaseModel):
    """执行摘要"""
    execution_id: str
    status: ExecutionStatus
    total_tools_called: int
    successful_tools: int
    failed_tools: int
    artifacts_count: int
    total_execution_time_ms: int
    resource_usage: ResourceUsage
    error_message: Optional[str] = None


class ExecutionError(BaseModel):
    """执行错误"""
    error_type: str
    error_message: str
    error_details: dict = Field(default_factory=dict)
    recoverable: bool = Field(default=False)
    partial_results: Optional[list[ToolResult]] = None


class CreateExecutionRequest(BaseModel):
    """创建执行请求"""
    task_params: dict = Field(default_factory=dict)
    timeout: int = Field(default=60)
    resource_limits: Optional[ResourceLimits] = None
    session_id: Optional[str] = None
    workflow_id: Optional[str] = None


class ToolInvocationRequest(BaseModel):
    """工具调用请求"""
    params: dict = Field(default_factory=dict)
    timeout_override: Optional[int] = None


class StreamExecutionRequest(BaseModel):
    """流式执行请求"""
    tool_calls: list[ToolCall]