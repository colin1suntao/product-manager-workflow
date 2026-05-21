# Sandbox 执行环境需求文档

## Introduction

Sandbox 执行环境是一个安全隔离的代码运行环境，使 AI Agent 能够真正执行代码、生成文件、操作文件系统。这是从 "Chat + Skills" 到 "Super Agent" 的关键升级，让 Agent 具备真实的创作和执行能力。

## Glossary

- **Sandbox**: 安全隔离的执行环境，Agent 在其中执行代码和操作文件
- **Workspace**: Sandbox 内的工作目录，用于存储 Agent 生成的文件
- **Execution Context**: 执行上下文，包含任务参数、输入文件、环境变量等
- **Tool**: Agent 可调用的工具，如文件读写、Shell 执行、HTTP 请求等
- **Execution Result**: 执行结果，包含输出内容、产物文件、执行状态等

## Requirements

### Requirement 1: 安全隔离的执行环境

**User Story:** AS AI Agent, I want to execute code in an isolated environment, so that I can perform real tasks without risking the host system.

#### Acceptance Criteria

1. WHEN an execution is initiated, the system SHALL create an isolated execution context with its own workspace directory
2. WHILE an execution is running, the system SHALL prevent access to files outside the designated workspace
3. IF an execution exceeds resource limits (CPU, memory, time), the system SHALL terminate the execution and report the violation
4. WHEN an execution completes, the system SHALL preserve all generated artifacts in the workspace for retrieval

### Requirement 2: 文件操作能力

**User Story:** AS AI Agent, I want to read and write files in the workspace, so that I can create and modify documents, prototypes, and code.

#### Acceptance Criteria

1. WHEN the Agent requests to read a file, the system SHALL provide the file content if the file exists in the workspace
2. WHEN the Agent requests to write a file, the system SHALL create or update the file in the workspace with the specified content
3. WHEN the Agent requests to list files, the system SHALL return all files in the workspace directory
4. IF a file operation fails, the system SHALL return an error message with the cause

### Requirement 3: Shell 命令执行

**User Story:** AS AI Agent, I want to execute shell commands, so that I can run scripts, install dependencies, and perform system operations.

#### Acceptance Criteria

1. WHEN the Agent requests to execute a shell command, the system SHALL run the command in the execution context
2. WHILE a command is executing, the system SHALL capture stdout and stderr streams
3. WHEN a command completes, the system SHALL return the exit code, stdout, and stderr
4. IF a command execution exceeds the timeout limit, the system SHALL terminate the command and report timeout
5. IF a command is blocked by security policy, the system SHALL reject the command and explain the reason

### Requirement 4: Python 代码执行

**User Story:** AS AI Agent, I want to execute Python code, so that I can perform data analysis, generate visualizations, and automate tasks.

#### Acceptance Criteria

1. WHEN the Agent requests to execute Python code, the system SHALL run the code in the execution context with the specified input
2. WHILE Python code is executing, the system SHALL capture print output and return values
3. WHEN Python execution completes, the system SHALL return the output, return value, and any generated files
4. IF Python code raises an exception, the system SHALL capture the exception message and traceback

### Requirement 5: 工具调用接口

**User Story:** AS AI Agent, I want to call predefined tools, so that I can perform common operations without writing code.

#### Acceptance Criteria

1. WHEN the Agent requests to use a tool, the system SHALL invoke the tool with the provided parameters
2. WHILE a tool is executing, the system SHALL track execution progress and intermediate results
3. WHEN a tool completes, the system SHALL return the tool output and any generated artifacts
4. The system SHALL provide built-in tools: file_read, file_write, file_list, shell_execute, python_execute, http_request

### Requirement 6: 与 Sub-Agent 集成

**User Story:** AS Sub-Agent executor, I want to invoke Sandbox for task execution, so that Sub-Agent can perform real operations beyond text generation.

#### Acceptance Criteria

1. WHEN a Sub-Agent execution starts, the system SHALL create a Sandbox execution context linked to the Sub-Agent task
2. WHILE Sub-Agent is running, the system SHALL allow the Sub-Agent to call Sandbox tools through a unified interface
3. WHEN Sub-Agent completes, the system SHALL collect all artifacts from the Sandbox and return them as Sub-Agent output
4. The system SHALL pass Sub-Agent timeout settings to Sandbox execution

### Requirement 7: 与工作流集成

**User Story:** AS Workflow orchestrator, I want to use Sandbox for workflow step execution, so that workflow steps can produce real artifacts.

#### Acceptance Criteria

1. WHEN a workflow step requires Sandbox execution, the system SHALL create a dedicated execution context for the step
2. WHILE a workflow is running, the system SHALL allow steps to access artifacts from previous steps via Sandbox workspace
3. WHEN a workflow step completes, the system SHALL transfer artifacts from Sandbox to ArtifactManager
4. IF a workflow step fails in Sandbox, the system SHALL report the error and allow workflow error handling

### Requirement 8: 产物管理集成

**User Story:** AS Artifact manager, I want to receive artifacts from Sandbox, so that I can version and manage the generated files.

#### Acceptance Criteria

1. WHEN an execution completes with artifacts, the system SHALL register all artifacts in ArtifactManager
2. WHILE registering artifacts, the system SHALL preserve file metadata (name, type, size, created_at)
3. WHEN an artifact is registered, the system SHALL generate preview URL and download URL
4. The system SHALL support artifact types: prototype (HTML), document (Markdown), report (Markdown), code (Python/JS), data (JSON/CSV), image (PNG/SVG)

### Requirement 9: 资源限制和安全策略

**User Story:** AS System administrator, I want to enforce resource limits and security policies, so that Sandbox executions cannot abuse system resources.

#### Acceptance Criteria

1. WHEN an execution starts, the system SHALL apply resource limits: max CPU time (60s), max memory (512MB), max file size (10MB)
2. WHILE an execution is running, the system SHALL monitor resource usage and terminate if limits exceeded
3. The system SHALL block dangerous commands: rm, sudo, chmod, chown, iptables, shutdown, reboot, fdisk, mkfs
4. The system SHALL block network access to sensitive hosts: localhost, 127.0.0.1, internal IPs
5. IF a security violation is detected, the system SHALL terminate execution and log the incident

### Requirement 10: 执行状态跟踪

**User Story:** AS User, I want to track execution progress, so that I know what the Agent is doing and can monitor its progress.

#### Acceptance Criteria

1. WHEN an execution starts, the system SHALL emit a status event: execution_started
2. WHILE executing, the system SHALL emit progress events: tool_invoked, file_written, command_executed
3. WHEN an execution completes, the system SHALL emit a status event: execution_completed with results
4. IF an execution fails, the system SHALL emit a status event: execution_failed with error details
5. The system SHALL provide a query API to get execution status and logs

## Non-Functional Requirements

### NFR 1: Performance

- Single execution response time SHALL be less than 30 seconds for typical tasks
- Concurrent executions SHALL support up to 5 parallel executions per user
- Workspace file operations SHALL complete within 100ms for files under 1MB

### NFR 2: Security

- Sandbox SHALL be isolated from host system (process sandbox or container)
- Network access SHALL be restricted to allowed hosts only
- File system access SHALL be limited to designated workspace only
- Resource limits SHALL be enforced strictly

### NFR 3: Reliability

- Execution failures SHALL be captured and reported, not crash the system
- Workspace files SHALL be persisted even after execution failure
- Timeout handling SHALL guarantee termination within timeout + 5s

### NFR 4: Extensibility

- Tool interface SHALL be extensible for adding new tools
- Execution backend SHALL be configurable (local process, Docker, cloud sandbox)
- Security policy SHALL be configurable via configuration file

## Constraints

1. **Technology Constraint**: Use Python subprocess or Docker for execution isolation
2. **Integration Constraint**: Sandbox must integrate with existing Sub-Agent and Workflow systems
3. **Resource Constraint**: Single Sandbox instance per execution, not shared across executions
4. **Storage Constraint**: Workspace storage SHALL use local filesystem under `/tmp/sandbox/`

## Out of Scope

1. Browser automation (Playwright/Selenium) - Phase 4 feature
2. VSCode Server integration - Phase 4 feature
3. Cloud sandbox backend (AWS Lambda, GCP Cloud Functions) - Future consideration
4. GPU execution - Not needed for PM tasks