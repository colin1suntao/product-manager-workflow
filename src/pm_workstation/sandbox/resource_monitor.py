"""Sandbox 资源监控器

监控执行过程中的 CPU、内存、文件大小等资源使用。
"""

import asyncio
import logging
import os
import time

import psutil

from pm_workstation.sandbox.models import (
    ExecutionContext,
    ResourceLimits,
    ResourceUsage,
)

logger = logging.getLogger(__name__)


class ResourceMonitor:
    """资源监控器
    
    监控执行过程的资源使用：
    - CPU 时间
    - 内存使用
    - 文件大小
    - 输出大小
    """

    DEFAULT_LIMITS = ResourceLimits(
        max_cpu_time=60,
        max_memory_mb=512,
        max_file_size_mb=10,
        max_output_size_mb=5,
        max_concurrent_processes=3,
    )

    def __init__(self):
        self._monitored_processes: dict[str, psutil.Process] = {}
        self._start_times: dict[str, float] = {}
        self._resource_usages: dict[str, ResourceUsage] = {}

    def start_monitoring(
        self,
        context: ExecutionContext,
        limits: ResourceLimits | None = None,
    ) -> None:
        """开始监控执行
        
        Args:
            context: 执行上下文
            limits: 资源限制（可选）
        """
        execution_id = context.execution_id
        self._start_times[execution_id] = time.time()
        self._resource_usages[execution_id] = ResourceUsage()

        logger.info(f"Started monitoring execution: {execution_id}")

    def register_process(
        self,
        context: ExecutionContext,
        pid: int,
    ) -> None:
        """注册进程进行监控
        
        Args:
            context: 执行上下文
            pid: 进程 ID
        """
        try:
            process = psutil.Process(pid)
            self._monitored_processes[context.execution_id] = process
        except psutil.NoSuchProcess:
            logger.warning(f"Process {pid} not found for monitoring")

    def check_limits(
        self,
        context: ExecutionContext,
        limits: ResourceLimits | None = None,
    ) -> tuple[bool, str | None]:
        """检查是否超出资源限制
        
        Args:
            context: 执行上下文
            limits: 资源限制
            
        Returns:
            tuple: (是否超出, 原因)
        """
        limits = limits or self.DEFAULT_LIMITS
        execution_id = context.execution_id

        start_time = self._start_times.get(execution_id, time.time())
        elapsed_time = time.time() - start_time

        if elapsed_time > limits.max_cpu_time:
            return True, f"CPU time exceeded: {elapsed_time:.1f}s > {limits.max_cpu_time}s"

        process = self._monitored_processes.get(execution_id)
        if process:
            try:
                memory_info = process.memory_info()
                memory_mb = memory_info.rss / (1024 * 1024)

                if memory_mb > limits.max_memory_mb:
                    return True, f"Memory exceeded: {memory_mb:.1f}MB > {limits.max_memory_mb}MB"
            except psutil.NoSuchProcess:
                pass

        workspace_path = context.workspace_path
        if os.path.exists(workspace_path):
            total_size = 0
            file_count = 0

            for root, dirs, files in os.walk(workspace_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        size = os.path.getsize(file_path)
                        total_size += size
                        file_count += 1

                        file_size_mb = size / (1024 * 1024)
                        if file_size_mb > limits.max_file_size_mb:
                            return True, f"File size exceeded: {file_path} ({file_size_mb:.1f}MB)"
                    except OSError:
                        pass

            total_size_mb = total_size / (1024 * 1024)
            usage = self._resource_usages.get(execution_id, ResourceUsage())
            usage.cpu_time_seconds = elapsed_time
            usage.file_count = file_count
            usage.total_file_size_bytes = total_size
            self._resource_usages[execution_id] = usage

        return False, None

    def get_usage_stats(
        self,
        context: ExecutionContext,
    ) -> ResourceUsage:
        """获取资源使用统计
        
        Args:
            context: 执行上下文
            
        Returns:
            ResourceUsage: 资源使用统计
        """
        execution_id = context.execution_id

        start_time = self._start_times.get(execution_id, time.time())
        elapsed_time = time.time() - start_time

        usage = self._resource_usages.get(execution_id, ResourceUsage())
        usage.cpu_time_seconds = elapsed_time

        process = self._monitored_processes.get(execution_id)
        if process:
            try:
                memory_info = process.memory_info()
                usage.memory_mb = memory_info.rss / (1024 * 1024)
            except psutil.NoSuchProcess:
                pass

        return usage

    async def monitor_loop(
        self,
        context: ExecutionContext,
        limits: ResourceLimits,
        check_interval: float = 1.0,
    ) -> None:
        """持续监控循环
        
        Args:
            context: 执行上下文
            limits: 资源限制
            check_interval: 检查间隔（秒）
        """
        while context.status == "running":
            exceeded, reason = self.check_limits(context, limits)

            if exceeded:
                logger.warning(f"Resource limit exceeded for {context.execution_id}: {reason}")
                self.terminate_execution(context, reason)
                break

            await asyncio.sleep(check_interval)

    def terminate_execution(
        self,
        context: ExecutionContext,
        reason: str,
    ) -> bool:
        """终止执行
        
        Args:
            context: 执行上下文
            reason: 终止原因
            
        Returns:
            bool: 是否成功终止
        """
        execution_id = context.execution_id
        process = self._monitored_processes.get(execution_id)

        if process:
            try:
                process.terminate()
                time.sleep(0.5)

                if process.is_running():
                    process.kill()
                    logger.warning(f"Force killed process for {execution_id}")

                logger.info(f"Terminated execution {execution_id}: {reason}")
                return True
            except psutil.NoSuchProcess:
                return True
            except Exception as e:
                logger.error(f"Failed to terminate process: {e}")
                return False

        return False

    def stop_monitoring(
        self,
        context: ExecutionContext,
    ) -> ResourceUsage:
        """停止监控并返回使用统计
        
        Args:
            context: 执行上下文
            
        Returns:
            ResourceUsage: 最终资源使用统计
        """
        execution_id = context.execution_id

        final_usage = self.get_usage_stats(context)

        self._monitored_processes.pop(execution_id, None)
        self._start_times.pop(execution_id, None)
        self._resource_usages.pop(execution_id, None)

        logger.info(f"Stopped monitoring execution: {execution_id}")

        return final_usage


_global_resource_monitor: ResourceMonitor | None = None


def get_resource_monitor() -> ResourceMonitor:
    """获取全局资源监控器实例"""
    global _global_resource_monitor
    if _global_resource_monitor is None:
        _global_resource_monitor = ResourceMonitor()
    return _global_resource_monitor
