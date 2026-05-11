import type {
  WorkflowRun,
  WorkflowListResponse,
  CreateWorkflowRequest,
  WorkflowControlRequest,
  Component,
  ComponentListResponse,
  CreateComponentRequest,
  UpdateComponentRequest,
  IntegrationConfig,
  IntegrationConfigListResponse,
  CreateIntegrationConfigRequest,
  UpdateIntegrationConfigRequest,
  SyncTask,
  SyncTaskListResponse,
  CreateSyncTaskRequest,
  VerificationReport,
} from "@/types/api";
import { getAccessToken } from "@/lib/auth";

const API_BASE =
  typeof window !== "undefined" ? "" : process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchApi<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const url = `${API_BASE}${path}`;
  const token = getAccessToken();
  const baseHeaders: Record<string, string> = {
    "Content-Type": "application/json",
  };

  if (token) {
    baseHeaders["Authorization"] = `Bearer ${token}`;
  }

  if (options.headers) {
    const existingHeaders = options.headers as Record<string, string>;
    Object.assign(baseHeaders, existingHeaders);
  }

  const response = await fetch(url, { ...options, headers: baseHeaders });

  if (!response.ok) {
    const error = await response.json().catch(() => ({
      detail: response.statusText,
    }));
    throw new Error(error.detail || "API request failed");
  }

  return response.json().catch(() => {
    throw new Error("API 响应格式错误");
  });
}

/** 工作流 API */
export const workflowApi = {
  list: (params?: {
    page?: number;
    size?: number;
    status?: string;
  }) => {
    const qs = new URLSearchParams();
    if (params?.page) qs.set("page", String(params.page));
    if (params?.size) qs.set("size", String(params.size));
    if (params?.status) qs.set("status", params.status);
    const query = qs.toString() ? `?${qs.toString()}` : "";
    return fetchApi<WorkflowListResponse>(`/api/v1/workflows${query}`);
  },

  get: (runId: string) =>
    fetchApi<WorkflowRun>(`/api/v1/workflows/${runId}`),

  create: (data: CreateWorkflowRequest) =>
    fetchApi<WorkflowRun>("/api/v1/workflows", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  pause: (runId: string) =>
    fetchApi<WorkflowRun>(`/api/v1/workflows/${runId}/pause`, {
      method: "POST",
      body: JSON.stringify({}),
    }),

  resume: (runId: string, feedback?: string) =>
    fetchApi<WorkflowRun>(`/api/v1/workflows/${runId}/resume`, {
      method: "POST",
      body: JSON.stringify({ action: "resume", feedback } as WorkflowControlRequest),
    }),

cancel: (runId: string) =>
    fetchApi<WorkflowRun>(`/api/v1/workflows/${runId}/cancel`, {
      method: "POST",
      body: JSON.stringify({}),
    }),

  delete: (runId: string) =>
    fetchApi<{ message: string }>(`/api/v1/workflows/${runId}`, {
      method: "DELETE",
    }),
};

/** 组件库 API */
export const componentApi = {
  list: (params?: { page?: number; size?: number; category?: string }) => {
    const qs = new URLSearchParams();
    if (params?.page) qs.set("page", String(params.page));
    if (params?.size) qs.set("size", String(params.size));
    if (params?.category) qs.set("category", params.category);
    const query = qs.toString() ? `?${qs.toString()}` : "";
    return fetchApi<ComponentListResponse>(`/api/v1/components${query}`);
  },

  get: (id: string) => fetchApi<Component>(`/api/v1/components/${id}`),

  create: (data: CreateComponentRequest) =>
    fetchApi<Component>("/api/v1/components", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  update: (id: string, data: UpdateComponentRequest) =>
    fetchApi<Component>(`/api/v1/components/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  delete: (id: string) =>
    fetchApi<void>(`/api/v1/components/${id}`, { method: "DELETE" }),
};

/** 集成配置 API */
export const integrationApi = {
  listConfigs: (params?: { integration_type?: string }) => {
    const qs = new URLSearchParams();
    if (params?.integration_type) qs.set("integration_type", params.integration_type);
    const query = qs.toString() ? `?${qs.toString()}` : "";
    return fetchApi<IntegrationConfigListResponse>(
      `/api/v1/integrations/configs${query}`,
    );
  },

  getConfig: (id: string) =>
    fetchApi<IntegrationConfig>(`/api/v1/integrations/configs/${id}`),

  createConfig: (data: CreateIntegrationConfigRequest) =>
    fetchApi<IntegrationConfig>("/api/v1/integrations/configs", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  updateConfig: (id: string, data: UpdateIntegrationConfigRequest) =>
    fetchApi<IntegrationConfig>(`/api/v1/integrations/configs/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  deleteConfig: (id: string) =>
    fetchApi<void>(`/api/v1/integrations/configs/${id}`, { method: "DELETE" }),

  listSyncTasks: (params?: { integration_id?: string; status?: string }) => {
    const qs = new URLSearchParams();
    if (params?.integration_id) qs.set("integration_id", params.integration_id);
    if (params?.status) qs.set("status", params.status);
    const query = qs.toString() ? `?${qs.toString()}` : "";
    return fetchApi<SyncTaskListResponse>(
      `/api/v1/integrations/sync-tasks${query}`,
    );
  },

  getSyncTask: (id: string) =>
    fetchApi<SyncTask>(`/api/v1/integrations/sync-tasks/${id}`),

  createSyncTask: (configId: string, data: CreateSyncTaskRequest) =>
    fetchApi<SyncTask>(
      `/api/v1/integrations/configs/${configId}/sync-tasks`,
      {
        method: "POST",
        body: JSON.stringify(data),
      },
    ),

  cancelSyncTask: (id: string) =>
    fetchApi<SyncTask>(`/api/v1/integrations/sync-tasks/${id}/cancel`, {
      method: "POST",
      body: JSON.stringify({}),
    }),
};

/** 校验报告 API */
export const reportApi = {
  get: (workflowId: string) =>
    fetchApi<VerificationReport>(
      `/api/v1/workflows/runs/${workflowId}/report`,
    ),
};

/** 市场调研 API */
export const marketResearchApi = {
  create: (data: {
    title?: string;
    requirement_text: string;
    selected_skills: string[];
    template_id?: string;
  }) =>
    fetchApi<{ task_id: string; report_id: string; status: string; message: string }>(
      "/api/v1/market-research/create",
      {
        method: "POST",
        body: JSON.stringify(data),
      },
    ),

  list: () =>
    fetchApi<{ reports: Array<{
      id: string;
      title: string;
      status: string;
      selected_skills: string[];
      created_at: string;
      completed_at: string | null;
    }>; total: number }>("/api/v1/market-research/list"),

  get: (reportId: string) =>
    fetchApi<{
      id: string;
      title: string;
      requirement_text: string;
      selected_skills: string[];
      report_content: string;
      status: string;
      created_at: string;
      completed_at: string | null;
    }>(`/api/v1/market-research/${reportId}`),

  getStatus: (reportId: string) =>
    fetchApi<{
      report_id: string;
      task_id: string;
      status: string;
      started_at: string | null;
      completed_at: string | null;
      error_message: string | null;
    }>(`/api/v1/market-research/${reportId}/status`),

  recommendSkills: (requirementText: string) =>
    fetchApi<{
      recommendations: Array<{
        name: string;
        description: string;
        relevance_score: number;
        category: string;
      }>;
      total: number;
    }>("/api/v1/market-research/recommend-skills", {
      method: "POST",
      body: JSON.stringify({ requirement_text: requirementText }),
    }),

  saveTemplate: (data: {
    name: string;
    description?: string;
    skill_names: string[];
  }) =>
    fetchApi<{ id: string; name: string; description: string; skill_names: string[]; message: string }>(
      "/api/v1/market-research/templates",
      {
        method: "POST",
        body: JSON.stringify(data),
      },
    ),

  listTemplates: () =>
    fetchApi<{
      templates: Array<{
        id: string;
        name: string;
        description: string;
        skill_names: string[];
        created_at: string;
      }>;
      total: number;
    }>("/api/v1/market-research/templates/list"),

  deleteTemplate: (templateId: string) =>
    fetchApi<{ message: string }>(
      `/api/v1/market-research/templates/${templateId}`,
      { method: "DELETE" },
    ),
};

/** 会话交互 API */
export const chatApi = {
  createSession: (title?: string) =>
    fetchApi<{ id: string; title: string; created_at: string; updated_at: string }>(
      "/api/v1/chat/sessions",
      {
        method: "POST",
        body: JSON.stringify({ title }),
      },
    ),

  listSessions: () =>
    fetchApi<{
      sessions: Array<{
        id: string;
        title: string;
        created_at: string;
        updated_at: string;
      }>;
      total: number;
    }>("/api/v1/chat/sessions"),

  getSession: (sessionId: string) =>
    fetchApi<{
      id: string;
      title: string;
      created_at: string;
      updated_at: string;
    }>(`/api/v1/chat/sessions/${sessionId}`),

  deleteSession: (sessionId: string) =>
    fetchApi<{ message: string }>(
      `/api/v1/chat/sessions/${sessionId}`,
      { method: "DELETE" },
    ),

  sendMessage: (
    sessionId: string,
    data: {
      content: string;
      task_mode?: string;
      selected_skills?: string[];
      provider_id?: string;
      model_name?: string;
    }
  ) =>
    fetchApi<{
      user_message: {
        id: string;
        content: string;
        created_at: string;
      };
      assistant_message: {
        id: string;
        content: string;
        task_mode: string | null;
        task_status: string | null;
        artifacts: Array<{ name: string; url: string; type: string }>;
        created_at: string;
      };
    }>(`/api/v1/chat/sessions/${sessionId}/messages`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  getMessages: (sessionId: string) =>
    fetchApi<{
      messages: Array<{
        id: string;
        role: "user" | "assistant" | "system";
        content: string;
        task_mode: string | null;
        task_status: string | null;
        artifacts: Array<{ name: string; url: string; type: string }>;
        created_at: string;
      }>;
      total: number;
    }>(`/api/v1/chat/sessions/${sessionId}/messages`),
};

/** 记忆管理 API */
export const memoryApi = {
  // Soul 管理
  getActiveSoul: () =>
    fetchApi<{
      id: string;
      name: string;
      personality: string;
      values: string[];
      behavior_rules: string[];
      communication_style: string;
      expertise_areas: string[];
      is_active: boolean;
    }>("/api/v1/memory/soul"),

  createSoul: (data: {
    name: string;
    personality: string;
    values: string[];
    behavior_rules: string[];
    communication_style: string;
    expertise_areas: string[];
  }) =>
    fetchApi<{ id: string; name: string; is_active: boolean; created_at: string }>(
      "/api/v1/memory/soul",
      { method: "POST", body: JSON.stringify(data) },
    ),

  updateSoul: (soulId: string, data: Record<string, unknown>) =>
    fetchApi<{ id: string; name: string; updated_at: string }>(
      `/api/v1/memory/soul/${soulId}`,
      { method: "PUT", body: JSON.stringify(data) },
    ),

  listSouls: () =>
    fetchApi<{
      souls: Array<{ id: string; name: string; is_active: boolean; created_at: string }>;
      total: number;
    }>("/api/v1/memory/soul/list"),

  activateSoul: (soulId: string) =>
    fetchApi<{ message: string }>(
      `/api/v1/memory/soul/${soulId}/activate`,
      { method: "POST" },
    ),

  deleteSoul: (soulId: string) =>
    fetchApi<{ message: string }>(
      `/api/v1/memory/soul/${soulId}`,
      { method: "DELETE" },
    ),

  // 偏好管理
  createPreference: (data: { category: string; key: string; value: string }) =>
    fetchApi<{ id: string; category: string; key: string; value: string; created_at: string }>(
      "/api/v1/memory/preferences",
      { method: "POST", body: JSON.stringify(data) },
    ),

  listPreferences: () =>
    fetchApi<{
      preferences: Array<{
        id: string;
        category: string;
        key: string;
        value: string;
        created_at: string;
      }>;
      total: number;
    }>("/api/v1/memory/preferences"),

  updatePreference: (prefId: string, data: { value: string }) =>
    fetchApi<{ message: string }>(
      `/api/v1/memory/preferences/${prefId}`,
      { method: "PUT", body: JSON.stringify(data) },
    ),

  deletePreference: (prefId: string) =>
    fetchApi<{ message: string }>(
      `/api/v1/memory/preferences/${prefId}`,
      { method: "DELETE" },
    ),

  // 记忆管理
  createMemory: (data: {
    memory_type: string;
    content: string;
    summary: string;
    tags?: string[];
    importance?: number;
  }) =>
    fetchApi<{
      id: string;
      memory_type: string;
      summary: string;
      created_at: string;
    }>("/api/v1/memory/entries", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  listMemories: (memoryType?: string) => {
    const params = memoryType ? `?memory_type=${memoryType}` : "";
    return fetchApi<{
      memories: Array<{
        id: string;
        memory_type: string;
        summary: string;
        content: string;
        tags: string[];
        importance: number;
        created_at: string;
      }>;
      total: number;
    }>(`/api/v1/memory/entries${params}`);
  },

  getMemory: (memoryId: string) =>
    fetchApi<{
      id: string;
      memory_type: string;
      summary: string;
      content: string;
      tags: string[];
      importance: number;
      source: string;
      context: Record<string, unknown>;
      created_at: string;
      last_accessed: string;
      access_count: number;
    }>(`/api/v1/memory/entries/${memoryId}`),

  updateMemory: (memoryId: string, data: Record<string, unknown>) =>
    fetchApi<{ message: string }>(
      `/api/v1/memory/entries/${memoryId}`,
      { method: "PUT", body: JSON.stringify(data) },
    ),

  deleteMemory: (memoryId: string) =>
    fetchApi<{ message: string }>(
      `/api/v1/memory/entries/${memoryId}`,
      { method: "DELETE" },
    ),

  searchMemories: (query: string, memoryType?: string) => {
    const params = new URLSearchParams({ q: query });
    if (memoryType) params.set("memory_type", memoryType);
    return fetchApi<{
      results: Array<{
        id: string;
        memory_type: string;
        summary: string;
        relevance_score: number;
        match_reason: string;
      }>;
      total: number;
    }>(`/api/v1/memory/search?${params.toString()}`);
  },

  getStats: () =>
    fetchApi<{
      total_memories: number;
      by_type: Record<string, number>;
      top_tags: Array<[string, number]>;
    }>("/api/v1/memory/stats"),

  // 反思管理
  triggerReflection: () =>
    fetchApi<{
      id: string;
      period_start: string;
      period_end: string;
      total_tasks: number;
      successful_tasks: number;
      failed_tasks: number;
      key_learnings: string[];
      improvement_areas: string[];
      action_items: string[];
      created_at: string;
    }>("/api/v1/memory/reflect", { method: "POST" }),

  listReflections: () =>
    fetchApi<{
      reflections: Array<{
        id: string;
        period_start: string;
        period_end: string;
        total_tasks: number;
        successful_tasks: number;
        failed_tasks: number;
        key_learnings: string[];
        created_at: string;
      }>;
      total: number;
    }>("/api/v1/memory/reflections"),

  getLatestReflection: () =>
    fetchApi<{
      id?: string;
      period_start?: string;
      period_end?: string;
      total_tasks?: number;
      successful_tasks?: number;
      failed_tasks?: number;
      key_learnings?: string[];
      improvement_areas?: string[];
      action_items?: string[];
      created_at?: string;
      message?: string;
    }>("/api/v1/memory/reflections/latest"),
};
