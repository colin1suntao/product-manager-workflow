# 记忆持久化系统需求文档

## Introduction

记忆持久化系统为 AI Agent 提供多层级记忆管理能力，支持项目级记忆、会话级记忆、长期偏好记忆的自动提取、存储和应用。解决现有 MemoryManager 仅使用内存存储、重启后丢失的问题。

## Glossary

- **项目级记忆**: 针对特定项目的长期记忆，包含项目背景、约束、决策历史、代码模式等
- **会话级记忆**: 针对单个会话的记忆，包含对话历史、上下文、任务状态、中间产物等
- **长期偏好记忆**: 用户跨项目的偏好，包含沟通风格、输出格式、工作流程偏好等
- **记忆提取器**: 从对话、工作流执行、Sandbox 执行中自动提取有价值记忆的组件
- **记忆检索器**: 根据当前上下文检索相关记忆的组件
- **记忆应用器**: 将检索到的记忆注入到 Agent 上下文的组件

## Requirements

### Requirement 1: 多层级记忆模型

**User Story:** AS AI Agent, I want to have memories at different levels, so that I can remember project-specific knowledge, session context, and user preferences separately.

#### Acceptance Criteria

1. WHEN a memory is created, the system SHALL classify it into one of: project_level, session_level, user_level
2. WHEN a project memory is stored, the system SHALL persist it under `.monkeycode/projects/{project_id}/memory/`
3. WHEN a session memory is stored, the system SHALL persist it under `.monkeycode/sessions/{session_id}/memory/`
4. WHEN a user preference is stored, the system SHALL persist it under `.monkeycode/users/{user_id}/preferences/`
5. WHEN retrieving memories, the system SHALL return memories from all levels with appropriate priority

### Requirement 2: 持久化存储

**User Story:** AS System, I want to persist memories to file system, so that memories survive application restart.

#### Acceptance Criteria

1. WHEN a memory is added or updated, the system SHALL immediately save to JSON file
2. WHEN the application starts, the system SHALL load all persisted memories into memory cache
3. WHEN a memory file is corrupted, the system SHALL log error and skip that file
4. WHEN disk space is low, the system SHALL archive old memories with low access_count
5. The system SHALL support atomic write operations to prevent data loss

### Requirement 3: 项目级记忆自动提取

**User Story:** AS AI Agent working on a project, I want the system to automatically extract project knowledge, so that I don't need to manually record important decisions.

#### Acceptance Criteria

1. WHEN a Workflow completes successfully, the system SHALL extract project decisions as project memory
2. WHEN a Sandbox execution creates artifacts, the system SHALL record artifact patterns as project memory
3. WHEN user provides project-specific instructions, the system SHALL save them as project memory
4. WHEN project code patterns are discovered, the system SHALL record them as project memory
5. The system SHALL deduplicate project memories based on content similarity

### Requirement 4: 会话级记忆自动提取

**User Story:** AS AI Agent in a session, I want the system to remember conversation context, so that I can maintain coherent dialogue.

#### Acceptance Criteria

1. WHEN a message is received, the system SHALL extract key entities as session memory
2. WHEN a task is assigned in session, the system SHALL record task context as session memory
3. WHEN an error occurs in session, the system SHALL record the error and resolution as session memory
4. WHEN a file is mentioned in session, the system SHALL record file context as session memory
5. WHEN session ends, the system SHALL archive session memories with importance > threshold

### Requirement 5: 长期偏好记忆自动提取

**User Story:** AS User, I want the system to remember my preferences across projects, so that I don't need to repeat my preferences every time.

#### Acceptance Criteria

1. WHEN user explicitly states a preference, the system SHALL save it as user preference
2. WHEN user repeatedly corrects Agent output format, the system SHALL learn format preference
3. WHEN user consistently uses certain workflow, the system SHALL learn workflow preference
4. WHEN user feedback is received, the system SHALL update relevant preferences
5. The system SHALL validate preference conflicts and ask user to clarify

### Requirement 6: 记忆检索与应用

**User Story:** AS AI Agent starting a new task, I want relevant memories to be automatically loaded, so that I can use past knowledge without manual lookup.

#### Acceptance Criteria

1. WHEN a session starts, the system SHALL load user preferences for that user
2. WHEN a project is opened, the system SHALL load project memories for that project
3. WHEN a task is assigned, the system SHALL search relevant memories by keywords and context
4. WHEN memories are loaded, the system SHALL inject them into Agent context with relevance scores
5. The system SHALL limit injected memories to avoid context overflow (max 20 items)

### Requirement 7: 记忆与 Workflow 集成

**User Story:** AS Workflow orchestrator, I want to record workflow execution history, so that future workflows can learn from past executions.

#### Acceptance Criteria

1. WHEN a workflow step completes, the system SHALL record step result as session memory
2. WHEN a workflow fails, the system SHALL record failure cause and context as session memory
3. WHEN workflow parameters are optimized, the system SHALL record optimization as project memory
4. WHEN workflow artifacts are generated, the system SHALL link memories to artifacts
5. The system SHALL suggest workflow improvements based on past memories

### Requirement 8: 记忆与 Sandbox 集成

**User Story:** AS Sandbox executor, I want to record execution insights, so that Agent can learn from code execution results.

#### Acceptance Criteria

1. WHEN a tool succeeds with novel output, the system SHALL record the pattern as project memory
2. WHEN a tool fails, the system SHALL record failure cause as session memory
3. WHEN Python code runs successfully, the system SHALL record code pattern as project memory
4. WHEN a file is generated, the system SHALL link memory to artifact file
5. The system SHALL suggest tool optimizations based on past execution memories

### Requirement 9: 记忆去重与更新

**User Story:** AS System, I want to avoid duplicate memories, so that memory storage stays clean and efficient.

#### Acceptance Criteria

1. WHEN a new memory is similar to existing memory (>80% similarity), the system SHALL merge them
2. WHEN merging memories, the system SHALL keep the more recent and higher importance one
3. WHEN a memory is accessed, the system SHALL update its access_count and last_accessed
4. WHEN a memory's access_count exceeds threshold, the system SHALL boost its importance
5. The system SHALL periodically scan for outdated memories and mark them for archival

### Requirement 10: 记忆统计与可视化

**User Story:** AS User, I want to see my memory statistics, so that I can understand what the Agent has learned.

#### Acceptance Criteria

1. WHEN user requests memory stats, the system SHALL return counts by level and type
2. WHEN user requests memory list, the system SHALL return paginated list with importance scores
3. WHEN user requests memory timeline, the system SHALL return creation timeline
4. WHEN user requests memory heatmap, the system SHALL return access frequency visualization
5. The system SHALL provide API endpoints for all statistics queries

## Non-Functional Requirements

### NFR 1: Performance
- Memory save SHALL complete within 100ms for single entry
- Memory load SHALL complete within 500ms for all user memories
- Memory search SHALL complete within 200ms with up to 1000 memories
- Memory deduplication SHALL complete within 1s for 100 new memories

### NFR 2: Storage Efficiency
- Memory files SHALL use JSON format with compression for large entries
- Memory storage SHALL not exceed 100MB per user
- Memory archival SHALL move old memories to compressed archive files

### NFR 3: Reliability
- Memory write SHALL use atomic operations (write to temp then rename)
- Memory corruption SHALL be detected and logged without crashing
- Memory backup SHALL be created weekly

### NFR 4: Extensibility
- Memory levels SHALL be configurable via configuration file
- Memory extraction rules SHALL be extensible via plugins
- Memory storage backend SHALL be swappable (filesystem, database)

## Constraints

1. **Technology**: Use Python pathlib for file operations, JSON for serialization
2. **Storage Path**: `.monkeycode/` directory for all persisted memories
3. **Integration**: Must integrate with existing MemoryManager, SoulManager, WorkflowOrchestrator, SandboxEngine

## Out of Scope

1. Cloud storage backend (AWS S3, etc.) - Future consideration
2. Database backend (PostgreSQL, MongoDB) - Future consideration
3. Memory encryption - Not required for current use case
4. Memory sharing between users - Not in scope