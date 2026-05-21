"""Sandbox 安全控制器

负责验证命令、文件路径、URL 的安全性，防止危险操作。
"""

import re
import logging
from typing import Optional

from pm_workstation.sandbox.models import (
    SecurityValidation,
    SecurityLevel,
    Workspace,
)

logger = logging.getLogger(__name__)


class SecurityController:
    """安全控制器
    
    验证执行操作的安全性，防止：
    - 危险 Shell 命令（如 rm、sudo、shutdown）
    - 路径穿越攻击（如 ../../../etc/passwd）
    - 内网访问（如 localhost、127.0.0.1、10.x.x.x）
    """
    
    BLOCKED_COMMANDS = [
        "rm", "rmdir", "sudo", "su", "chmod", "chown",
        "iptables", "ip6tables", "nftables", "ufw",
        "shutdown", "reboot", "poweroff", "halt",
        "fdisk", "parted", "gdisk", "mkfs",
        "mount", "umount", "dd", "shred",
        "passwd", "useradd", "userdel", "usermod",
        "groupadd", "groupdel", "groupmod",
        "chroot", "visudo",
        "wget", "curl", "nc", "netcat", "telnet",
        "ssh", "scp", "rsync", "ftp",
        "docker", "kubectl", "podman",
    ]
    
    BLOCKED_COMMAND_PREFIXES = [
        "rm ", "sudo ", "chmod ", "chown ",
        "shutdown", "reboot", "poweroff",
        "fdisk", "mkfs", "mount ",
        "wget ", "curl ", "nc ", "ssh ",
        "docker ", "kubectl ",
    ]
    
    BLOCKED_HOSTS = [
        "localhost",
        "127.0.0.1",
        "0.0.0.0",
        "::1",
    ]
    
    BLOCKED_IP_PATTERNS = [
        r"^10\.",
        r"^172\.16\.",
        r"^172\.17\.",
        r"^172\.18\.",
        r"^172\.19\.",
        r"^172\.20\.",
        r"^172\.21\.",
        r"^172\.22\.",
        r"^172\.23\.",
        r"^172\.24\.",
        r"^172\.25\.",
        r"^172\.26\.",
        r"^172\.27\.",
        r"^172\.28\.",
        r"^172\.29\.",
        r"^172\.30\.",
        r"^172\.31\.",
        r"^192\.168\.",
    ]
    
    DANGEROUS_FILE_PATHS = [
        "/etc/passwd",
        "/etc/shadow",
        "/etc/sudoers",
        "/root/",
        "/home/",
        "/var/log/",
        "/proc/",
        "/sys/",
        "/dev/",
    ]
    
    def validate_command(
        self,
        command: str,
        security_level: SecurityLevel = SecurityLevel.NORMAL,
    ) -> SecurityValidation:
        """验证 Shell 命令安全性
        
        Args:
            command: 要执行的命令
            security_level: 安全级别
            
        Returns:
            SecurityValidation: 验证结果
        """
        command_lower = command.lower().strip()
        
        for blocked in self.BLOCKED_COMMANDS:
            if blocked in command_lower.split():
                return SecurityValidation(
                    valid=False,
                    reason=f"Blocked command detected: {blocked}",
                    severity="high",
                )
        
        for prefix in self.BLOCKED_COMMAND_PREFIXES:
            if command_lower.startswith(prefix):
                blocked_cmd = prefix.strip()
                return SecurityValidation(
                    valid=False,
                    reason=f"Blocked command prefix detected: {blocked_cmd}",
                    severity="high",
                )
        
        dangerous_patterns = [
            r">\s*/etc/",
            r">\s*/root/",
            r">\s*/proc/",
            r">\s*/sys/",
            r">\s*/dev/",
            r";\s*rm",
            r"\|\s*rm",
            r"&&\s*rm",
            r"`.*rm.*`",
            r"\$\('.*rm.*'\)",
            r"\$\(\{.*rm.*\}\)",
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, command_lower):
                return SecurityValidation(
                    valid=False,
                    reason=f"Dangerous pattern detected: {pattern}",
                    severity="critical",
                )
        
        if security_level == SecurityLevel.RESTRICTED:
            restricted_commands = [
                "apt", "yum", "dnf", "pacman", "brew",
                "pip", "npm", "yarn", "gem",
                "git", "svn", "hg",
            ]
            for cmd in restricted_commands:
                if cmd in command_lower.split():
                    return SecurityValidation(
                        valid=False,
                        reason=f"Restricted command in restricted mode: {cmd}",
                        severity="medium",
                    )
        
        return SecurityValidation(valid=True)
    
    def validate_file_path(
        self,
        path: str,
        workspace: Workspace,
    ) -> SecurityValidation:
        """验证文件路径安全性
        
        Args:
            path: 文件路径
            workspace: 工作区
            
        Returns:
            SecurityValidation: 验证结果
        """
        path_normalized = path.strip()
        
        if ".." in path_normalized:
            return SecurityValidation(
                valid=False,
                reason="Path traversal detected: '..' in path",
                severity="critical",
            )
        
        if path_normalized.startswith("/"):
            if not path_normalized.startswith(workspace.path):
                for dangerous_path in self.DANGEROUS_FILE_PATHS:
                    if path_normalized.startswith(dangerous_path):
                        return SecurityValidation(
                            valid=False,
                            reason=f"Access to system path denied: {dangerous_path}",
                            severity="critical",
                        )
                
                return SecurityValidation(
                    valid=False,
                    reason=f"Path outside workspace: {path}",
                    severity="high",
                )
        
        resolved_path = path_normalized
        if not path_normalized.startswith(workspace.path):
            resolved_path = f"{workspace.path}/{path_normalized}"
        
        for dangerous_path in self.DANGEROUS_FILE_PATHS:
            if resolved_path.startswith(dangerous_path):
                return SecurityValidation(
                    valid=False,
                    reason=f"Resolved path access denied: {dangerous_path}",
                    severity="critical",
                )
        
        return SecurityValidation(valid=True)
    
    def validate_url(
        self,
        url: str,
        allow_public_network: bool = True,
    ) -> SecurityValidation:
        """验证 URL 安全性
        
        Args:
            url: URL 字符串
            allow_public_network: 是否允许公网访问
            
        Returns:
            SecurityValidation: 验证结果
        """
        import urllib.parse
        
        try:
            parsed = urllib.parse.urlparse(url)
        except Exception as e:
            return SecurityValidation(
                valid=False,
                reason=f"Invalid URL format: {e}",
                severity="low",
            )
        
        host = parsed.hostname or ""
        
        for blocked_host in self.BLOCKED_HOSTS:
            if host == blocked_host:
                return SecurityValidation(
                    valid=False,
                    reason=f"Blocked host: {host}",
                    severity="high",
                )
        
        for pattern in self.BLOCKED_IP_PATTERNS:
            if re.match(pattern, host):
                return SecurityValidation(
                    valid=False,
                    reason=f"Internal IP range blocked: {host}",
                    severity="high",
                )
        
        if re.match(r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$", host):
            if host.startswith("127.") or host == "0.0.0.0":
                return SecurityValidation(
                    valid=False,
                    reason=f"Local IP blocked: {host}",
                    severity="high",
                )
        
        if not allow_public_network:
            return SecurityValidation(
                valid=False,
                reason="Network access disabled",
                severity="medium",
            )
        
        if parsed.scheme not in ["http", "https"]:
            return SecurityValidation(
                valid=False,
                reason=f"Unsupported protocol: {parsed.scheme}",
                severity="medium",
            )
        
        return SecurityValidation(valid=True)
    
    def validate_python_code(
        self,
        code: str,
        security_level: SecurityLevel = SecurityLevel.NORMAL,
    ) -> SecurityValidation:
        """验证 Python 代码安全性
        
        Args:
            code: Python 代码
            security_level: 安全级别
            
        Returns:
            SecurityValidation: 验证结果
        """
        dangerous_imports = [
            "os.system",
            "os.popen",
            "subprocess.call",
            "subprocess.run",
            "subprocess.Popen",
            "eval",
            "exec",
            "compile",
            "__import__",
            "importlib.import_module",
            "ctypes",
            "multiprocessing",
            "threading.Thread",
        ]
        
        for pattern in dangerous_imports:
            if pattern in code:
                if security_level == SecurityLevel.RESTRICTED:
                    return SecurityValidation(
                        valid=False,
                        reason=f"Dangerous pattern in Python code: {pattern}",
                        severity="high",
                    )
        
        dangerous_builtins = [
            "__builtins__",
            "__import__",
            "eval(",
            "exec(",
            "compile(",
            "open('/etc/",
            "open('/root/",
            "open('/proc/",
            "open('/sys/",
        ]
        
        for pattern in dangerous_builtins:
            if pattern in code:
                return SecurityValidation(
                    valid=False,
                    reason=f"Dangerous builtin usage: {pattern}",
                    severity="high",
                )
        
        return SecurityValidation(valid=True)
    
    def sanitize_command_output(
        self,
        output: str,
        max_length: int = 10000,
    ) -> str:
        """清理命令输出，移除敏感信息
        
        Args:
            output: 原始输出
            max_length: 最大长度
            
        Returns:
            str: 清理后的输出
        """
        if len(output) > max_length:
            output = output[:max_length] + "... [truncated]"
        
        sensitive_patterns = [
            (r"password\s*[=:]\s*\S+", "password=***"),
            (r"token\s*[=:]\s*\S+", "token=***"),
            (r"api_key\s*[=:]\s*\S+", "api_key=***"),
            (r"secret\s*[=:]\s*\S+", "secret=***"),
            (r"Bearer\s+\S+", "Bearer ***"),
        ]
        
        for pattern, replacement in sensitive_patterns:
            output = re.sub(pattern, replacement, output, flags=re.IGNORECASE)
        
        return output


_global_security_controller: Optional[SecurityController] = None


def get_security_controller() -> SecurityController:
    """获取全局安全控制器实例"""
    global _global_security_controller
    if _global_security_controller is None:
        _global_security_controller = SecurityController()
    return _global_security_controller