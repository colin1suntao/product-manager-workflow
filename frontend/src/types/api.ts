/** API 类型定义 */

/** 工作流状态 */
export type WorkflowStatus =
  | "init"
  | "parsing"
  | "parsed"
  | "generating"
  | "generated"
  | "verifying"
  | "verified"
  | "completed"
  | "failed"
  | "waiting_user_input"
  | "cancelled";

/** 工作流运行 */
export interface WorkflowRun {
  id: string;
  user_id: string;
  title?: string;
  requirement_text?: string;
  status: WorkflowStatus;
  created_at: string;
  updated_at: string;
  completed_steps?: number;
  total_steps?: number;
  structured_require?: Record<string, unknown> | null;
  prototype_url?: string;
  prd_document_url?: string;
  document_url?: string;
  report_url?: string;
  verification_report_url?: string;
  error?: string;
  error_message?: string;
  selected_skills?: string[];
}

/** 工作流列表响应 */
export interface WorkflowListResponse {
  total: number;
  workflows: WorkflowRun[];
}

/** 工作流创建请求 */
export interface CreateWorkflowRequest {
  requirement_text: string;
  llm_provider_id?: string;
  skills?: string[];
}

/** 工作流控制请求 */
export interface WorkflowControlRequest {
  action: "resume" | "cancel";
  feedback?: string;
}

/** 组件状态 */
export type ComponentStatus = "active" | "archived" | "draft";

/** 组件库组件 */
export interface Component {
  id: string;
  name: string;
  description: string;
  category: string;
  status: ComponentStatus;
  tags: string[];
  created_at: string;
  updated_at: string;
  html_preview: string;
  usage_example?: string;
}

/** 组件列表响应 */
export interface ComponentListResponse {
  total: number;
  components: Component[];
}

/** 组件创建请求 */
export interface CreateComponentRequest {
  name: string;
  description: string;
  category: string;
  tags?: string[];
  html_preview: string;
  usage_example?: string;
}

/** 组件更新请求 */
export interface UpdateComponentRequest {
  name?: string;
  description?: string;
  category?: string;
  status?: ComponentStatus;
  tags?: string[];
  html_preview?: string;
  usage_example?: string;
}

/** 集成类型 */
export type IntegrationType =
  | "jira"
  | "trello"
  | "github"
  | "gitlab"
  | "figma"
  | "slack"
  | "feishu";

/** 集成配置 */
export interface IntegrationConfig {
  id: string;
  name: string;
  integration_type: IntegrationType;
  api_endpoint?: string;
  enabled: boolean;
  created_at: string;
  updated_at: string;
  last_sync_at?: string;
}

/** 集成配置列表响应 */
export interface IntegrationConfigListResponse {
  total: number;
  configs: IntegrationConfig[];
}

/** 集成配置创建请求 */
export interface CreateIntegrationConfigRequest {
  name: string;
  integration_type: IntegrationType;
  api_endpoint?: string;
  api_key?: string;
  enabled?: boolean;
}

/** 集成配置更新请求 */
export interface UpdateIntegrationConfigRequest {
  name?: string;
  api_endpoint?: string;
  api_key?: string;
  enabled?: boolean;
}

/** 同步方向 */
export type SyncDirection = "import" | "export";

/** 同步任务状态 */
export type SyncTaskStatus =
  | "pending"
  | "running"
  | "completed"
  | "failed"
  | "cancelled";

/** 同步任务 */
export interface SyncTask {
  id: string;
  integration_id: string;
  direction: SyncDirection;
  status: SyncTaskStatus;
  workflow_id?: string;
  component_id?: string;
  created_at: string;
  updated_at: string;
  completed_at?: string;
  error_message?: string;
}

/** 同步任务列表响应 */
export interface SyncTaskListResponse {
  total: number;
  tasks: SyncTask[];
}

/** 同步任务创建请求 */
export interface CreateSyncTaskRequest {
  direction: SyncDirection;
  workflow_id?: string;
  component_id?: string;
}

/** 验证报告 */
export interface VerificationReport {
  id: string;
  workflow_id: string;
  prototype_issues: Issue[];
  document_issues: Issue[];
  consistency_issues: Issue[];
  overall_score: number;
  status: "pass" | "fail" | "warning";
  generated_at: string;
}

/** 问题 */
export interface Issue {
  id: string;
  type: string;
  severity: "critical" | "major" | "minor" | "info";
  message: string;
  suggestion: string;
  location?: string;
}

/** 组织 */
export interface Organization {
  id: string;
  name: string;
  owner_id: string;
  created_at: string;
  updated_at: string;
}

/** 用户组 */
export interface UserGroup {
  id: string;
  org_id: string;
  name: string;
  description?: string | null;
  created_at: string;
  member_count: number;
}

/** 组成员 */
export interface GroupMember {
  id: string;
  user_id: string;
  email: string;
  username: string;
  created_at: string;
}

/** 菜单权限 */
export interface MenuPermission {
  id: string;
  group_id: string;
  menu_key: string;
  can_access: boolean;
  created_at: string;
}

/** 菜单注册项 */
export interface MenuItem {
  key: string;
  label: string;
  icon: string;
  href: string;
  children?: MenuItem[];
}
