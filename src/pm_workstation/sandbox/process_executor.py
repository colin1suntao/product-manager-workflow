"""Sandbox 进程执行器

在安全隔离环境中执行 Shell 命令和 Python 代码。
"""

import asyncio
import json
import logging
import os
import sys
import time
import uuid

from pm_workstation.sandbox.models import (
    CommandResult,
    PythonResult,
)
from pm_workstation.sandbox.resource_monitor import (
    ResourceMonitor,
    get_resource_monitor,
)
from pm_workstation.sandbox.security_controller import (
    SecurityController,
    get_security_controller,
)
from pm_workstation.sandbox.workspace_manager import (
    Workspace,
)

logger = logging.getLogger(__name__)


class ProcessExecutor:
    """进程执行器
    
    在安全隔离环境中执行：
    - Shell 命令
    - Python 代码
    - 脚本文件
    """

    DEFAULT_TIMEOUT = 30
    PYTHON_EXECUTABLE = sys.executable

    def __init__(
        self,
        security_controller: SecurityController | None = None,
        resource_monitor: ResourceMonitor | None = None,
    ):
        self.security_controller = security_controller or get_security_controller()
        self.resource_monitor = resource_monitor or get_resource_monitor()

    async def execute_shell(
        self,
        command: str,
        workspace: Workspace,
        timeout: int = None,
        env: dict | None = None,
        cwd: str | None = None,
    ) -> CommandResult:
        """执行 Shell 命令
        
        Args:
            command: 命令字符串
            workspace: 工作区
            timeout: 超时时间（秒）
            env: 环境变量
            cwd: 工作目录
            
        Returns:
            CommandResult: 命令执行结果
        """
        timeout = timeout or self.DEFAULT_TIMEOUT

        validation = self.security_controller.validate_command(command)
        if not validation.valid:
            logger.warning(f"Command blocked: {validation.reason}")
            return CommandResult(
                command=command,
                exit_code=-1,
                stdout="",
                stderr=f"Command blocked: {validation.reason}",
                timed_out=False,
            )

        start_time = time.time()

        execution_env = os.environ.copy()
        execution_env["PATH"] = "/usr/local/bin:/usr/bin:/bin"
        execution_env["HOME"] = workspace.path
        execution_env["PWD"] = cwd or workspace.path

        if env:
            execution_env.update(env)

        cwd = cwd or workspace.path

        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                env=execution_env,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout,
                )

                exit_code = process.returncode
                timed_out = False

            except TimeoutError:
                process.kill()
                await process.wait()

                stdout = b""
                stderr = f"Command timed out after {timeout}s".encode()
                exit_code = -1
                timed_out = True

                logger.warning(f"Command timed out: {command}")

        except Exception as e:
            logger.error(f"Command execution failed: {e}")
            return CommandResult(
                command=command,
                exit_code=-1,
                stdout="",
                stderr=str(e),
                timed_out=False,
            )

        execution_time_ms = int((time.time() - start_time) * 1000)

        stdout_str = self.security_controller.sanitize_command_output(
            stdout.decode("utf-8", errors="replace")
        )
        stderr_str = self.security_controller.sanitize_command_output(
            stderr.decode("utf-8", errors="replace")
        )

        return CommandResult(
            command=command,
            exit_code=exit_code,
            stdout=stdout_str,
            stderr=stderr_str,
            execution_time_ms=execution_time_ms,
            timed_out=timed_out,
        )

    async def execute_python(
        self,
        code: str,
        workspace: Workspace,
        timeout: int = None,
        input_data: dict | None = None,
        imports: list[str] | None = None,
    ) -> PythonResult:
        """执行 Python 代码
        
        Args:
            code: Python 代码
            workspace: 工作区
            timeout: 超时时间（秒）
            input_data: 输入数据（作为全局变量）
            imports: 预导入的模块列表
            
        Returns:
            PythonResult: Python 执行结果
        """
        timeout = timeout or self.DEFAULT_TIMEOUT

        validation = self.security_controller.validate_python_code(code)
        if not validation.valid:
            logger.warning(f"Python code blocked: {validation.reason}")
            return PythonResult(
                code=code,
                stdout="",
                stderr=f"Code blocked: {validation.reason}",
                exception=None,
                files_created=[],
            )

        start_time = time.time()

        wrapper_code = self._wrap_python_code(code, workspace, input_data, imports)

        script_path = os.path.join(workspace.path, "temp", f"script_{uuid.uuid4().hex[:8]}.py")
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(wrapper_code)

        try:
            process = await asyncio.create_subprocess_exec(
                self.PYTHON_EXECUTABLE,
                script_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=workspace.path,
                env={
                    "PYTHONPATH": workspace.path,
                    "HOME": workspace.path,
                },
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout,
                )

                stdout_str = stdout.decode("utf-8", errors="replace")
                stderr_str = stderr.decode("utf-8", errors="replace")

            except TimeoutError:
                process.kill()
                await process.wait()

                stdout_str = ""
                stderr_str = f"Python execution timed out after {timeout}s"

                logger.warning("Python execution timed out")

        except Exception as e:
            stdout_str = ""
            stderr_str = str(e)

        try:
            os.remove(script_path)
        except OSError:
            pass

        result_path = os.path.join(workspace.path, "temp", f"result_{uuid.uuid4().hex[:8]}.json")
        return_value = None
        exception = None
        files_created = []

        if os.path.exists(result_path):
            try:
                with open(result_path, encoding="utf-8") as f:
                    result_data = json.load(f)
                    return_value = result_data.get("return_value")
                    exception = result_data.get("exception")
                    files_created = result_data.get("files_created", [])
            except json.JSONDecodeError:
                pass

            try:
                os.remove(result_path)
            except OSError:
                pass

        execution_time_ms = int((time.time() - start_time) * 1000)

        return PythonResult(
            code=code,
            stdout=stdout_str,
            stderr=stderr_str,
            return_value=return_value,
            exception=exception,
            execution_time_ms=execution_time_ms,
            files_created=files_created,
        )

    async def execute_script(
        self,
        script_path: str,
        workspace: Workspace,
        args: list[str] = None,
        timeout: int = None,
        interpreter: str | None = None,
    ) -> CommandResult:
        """执行脚本文件
        
        Args:
            script_path: 脚本文件路径
            workspace: 工作区
            args: 参数列表
            timeout: 超时时间
            interpreter: 解释器路径
            
        Returns:
            CommandResult: 执行结果
        """
        timeout = timeout or self.DEFAULT_TIMEOUT

        if not os.path.exists(script_path):
            return CommandResult(
                command=script_path,
                exit_code=-1,
                stdout="",
                stderr=f"Script not found: {script_path}",
            )

        if script_path.endswith(".py"):
            interpreter = interpreter or self.PYTHON_EXECUTABLE
        elif script_path.endswith(".sh"):
            interpreter = interpreter or "/bin/bash"
        elif script_path.endswith(".js"):
            interpreter = interpreter or "node"
        else:
            interpreter = interpreter or "/bin/bash"

        args = args or []

        command_args = [interpreter, script_path] + args

        start_time = time.time()

        try:
            process = await asyncio.create_subprocess_exec(
                *command_args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=workspace.path,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout,
                )

                exit_code = process.returncode

            except TimeoutError:
                process.kill()
                await process.wait()

                exit_code = -1

        except Exception as e:
            return CommandResult(
                command=f"{interpreter} {script_path}",
                exit_code=-1,
                stdout="",
                stderr=str(e),
            )

        execution_time_ms = int((time.time() - start_time) * 1000)

        return CommandResult(
            command=f"{interpreter} {script_path} {args}",
            exit_code=exit_code,
            stdout=stdout.decode("utf-8", errors="replace"),
            stderr=stderr.decode("utf-8", errors="replace"),
            execution_time_ms=execution_time_ms,
        )

    def _wrap_python_code(
        self,
        code: str,
        workspace: Workspace,
        input_data: dict | None = None,
        imports: list[str] | None = None,
    ) -> str:
        """包装 Python 代码以捕获输出和返回值
        
        Args:
            code: 原始代码
            workspace: 工作区
            input_data: 输入数据
            imports: 预导入模块
            
        Returns:
            str: 包装后的代码
        """
        import_lines = ""
        if imports:
            for module in imports:
                import_lines += f"import {module}\n"

        input_setup = ""
        if input_data:
            for key, value in input_data.items():
                if isinstance(value, str):
                    input_setup += f"{key} = '{value}'\n"
                elif isinstance(value, (int, float, bool)):
                    input_setup += f"{key} = {value}\n"
                elif isinstance(value, dict):
                    input_setup += f"{key} = {json.dumps(value)}\n"
                elif isinstance(value, list):
                    input_setup += f"{key} = {json.dumps(value)}\n"
                else:
                    input_setup += f"{key} = None\n"

        result_file = os.path.join(workspace.path, "temp", f"result_{uuid.uuid4().hex[:8]}.json")

        wrapper = f"""
import sys
import os
import json
import traceback

# Set workspace as working directory
os.chdir('{workspace.path}')

# Pre-imports
{import_lines}

# Input data
{input_setup}

# Capture stdout
_original_stdout = sys.stdout
sys.stdout = open(os.path.join('{workspace.path}', 'temp', 'stdout.txt'), 'w')

# Track created files
_initial_files = set(os.listdir('{workspace.path}'))
_created_files = []

# Execute code
_exception = None
_return_value = None

try:
{self._indent_code(code)}
except Exception as e:
    _exception = str(e) + '\\n' + traceback.format_exc()

# Restore stdout
sys.stdout.close()
sys.stdout = _original_stdout

# Find created files
_final_files = set(os.listdir('{workspace.path}'))
_created_files = list(_final_files - _initial_files)

# Save result
result = {{
    'return_value': _return_value,
    'exception': _exception,
    'files_created': _created_files
}}

with open('{result_file}', 'w') as f:
    json.dump(result, f)

# Print stdout content
stdout_file = os.path.join('{workspace.path}', 'temp', 'stdout.txt')
if os.path.exists(stdout_file):
    with open(stdout_file, 'r') as f:
        print(f.read())
    os.remove(stdout_file)
"""

        return wrapper

    def _indent_code(
        self,
        code: str,
        indent: int = 4,
    ) -> str:
        """缩进代码
        
        Args:
            code: 原始代码
            indent: 缩进空格数
            
        Returns:
            str: 缩进后的代码
        """
        indent_str = " " * indent
        lines = code.split("\n")
        indented_lines = []

        for line in lines:
            if line.strip():
                indented_lines.append(indent_str + line)
            else:
                indented_lines.append("")

        return "\n".join(indented_lines)


_global_process_executor: ProcessExecutor | None = None


def get_process_executor() -> ProcessExecutor:
    """获取全局进程执行器实例"""
    global _global_process_executor
    if _global_process_executor is None:
        _global_process_executor = ProcessExecutor()
    return _global_process_executor
