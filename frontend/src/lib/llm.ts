/**
 * LLM Provider API 客户端
 */

import { getAccessToken } from "@/lib/auth";

const API_BASE = typeof window !== "undefined" ? "" : process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface LLMProvider {
  id: string;
  name: string;
  provider_type: string;
  api_key: string;
  base_url?: string;
  default_model: string;
  is_active: boolean;
  is_default: boolean;
  created_at: string;
  updated_at: string;
}

export interface LLMProviderCreate {
  name: string;
  provider_type: "openai" | "anthropic" | "custom";
  api_key: string;
  base_url?: string;
  default_model: string;
  is_active?: boolean;
  is_default?: boolean;
}

export interface LLMProviderUpdate {
  name?: string;
  api_key?: string;
  base_url?: string;
  default_model?: string;
  is_active?: boolean;
  is_default?: boolean;
}

export interface LLMTestResult {
  success: boolean;
  response_time_ms: number;
  model: string;
  message: string;
}

async function fetchApi<T>(path: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE}${path}`;
  const token = getAccessToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...((options.headers as Record<string, string>) || {}),
  };

  const response = await fetch(url, { ...options, headers });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || "API request failed");
  }
  return response.json();
}

export const llmApi = {
  list: () => fetchApi<{ providers: LLMProvider[]; total: number }>("/api/v1/llm/providers"),

  create: (data: LLMProviderCreate) =>
    fetchApi<LLMProvider>("/api/v1/llm/providers", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  update: (id: string, data: LLMProviderUpdate) =>
    fetchApi<LLMProvider>(`/api/v1/llm/providers/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  delete: (id: string) =>
    fetchApi<{ message: string }>(`/api/v1/llm/providers/${id}`, {
      method: "DELETE",
    }),

  test: (id: string) =>
    fetchApi<LLMTestResult>(`/api/v1/llm/providers/${id}/test`, {
      method: "POST",
      body: JSON.stringify({}),
    }),

  setDefault: (id: string) =>
    fetchApi<{ message: string }>(`/api/v1/llm/providers/${id}/set-default`, {
      method: "POST",
      body: JSON.stringify({}),
    }),

  quickTest: (data: {
    provider_type: string;
    api_key: string;
    base_url?: string;
    default_model?: string;
  }) =>
    fetchApi<LLMTestResult>("/api/v1/llm/test-connection", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  listModels: (data: {
    provider_type: string;
    api_key: string;
    base_url?: string;
  }) =>
    fetchApi<{ models: { id: string; object: string }[]; total: number }>("/api/v1/llm/list-models", {
      method: "POST",
      body: JSON.stringify(data),
    }),
};
