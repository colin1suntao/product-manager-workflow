/**
 * 认证 API 客户端
 */

import { getAccessToken, getRefreshToken, clearTokens } from "@/lib/auth";

const API_BASE = typeof window !== "undefined" ? "" : process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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
  return response.json().catch(() => {
    throw new Error("API 响应格式错误");
  });
}

export const authApi = {
  logout: async () => {
    const refreshToken = getRefreshToken();
    if (refreshToken) {
      try {
        await fetchApi<{ message: string }>("/api/v1/auth/logout", {
          method: "POST",
          body: JSON.stringify({ refresh_token: refreshToken }),
        });
      } catch {
        // 即使服务器登出失败，也清除本地 token
      }
    }
    clearTokens();
  },

  changePassword: (data: { old_password: string; new_password: string }) =>
    fetchApi<{ message: string }>("/api/v1/auth/password", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  
  login: async (email: string, password: string) => {
    const response = await fetch(`${API_BASE}/api/v1/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || "登录失败");
    }
    return response.json();
  },
  
  register: async (email: string, password: string) => {
    const response = await fetch(`${API_BASE}/api/v1/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || "注册失败");
    }
    return response.json();
  },
};
