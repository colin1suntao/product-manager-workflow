/**
 * 组织管理 API 客户端
 */

import type {
  Organization,
  UserGroup,
  GroupMember,
  MenuPermission,
  MenuItem,
} from "@/types/api";
import { getAccessToken } from "@/lib/auth";

const API_BASE =
  typeof window !== "undefined" ? "" : process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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

export const orgApi = {
  getInfo: () => fetchApi<Organization>("/api/v1/org/info"),

  updateInfo: (name: string) =>
    fetchApi<Organization>("/api/v1/org/info", {
      method: "PUT",
      body: JSON.stringify({ name }),
    }),

  listUsers: () =>
    fetchApi<
      Array<{
        id: string;
        email: string;
        username: string;
        org_id: string;
        role: string;
      }>
    >("/api/v1/org/users"),

  listGroups: () => fetchApi<UserGroup[]>("/api/v1/org/groups"),

  createGroup: (data: { name: string; description?: string }) =>
    fetchApi<UserGroup>("/api/v1/org/groups", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  updateGroup: (groupId: string, data: { name?: string; description?: string }) =>
    fetchApi<UserGroup>(`/api/v1/org/groups/${groupId}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  deleteGroup: (groupId: string) =>
    fetchApi<{ message: string }>(`/api/v1/org/groups/${groupId}`, {
      method: "DELETE",
    }),

  listMembers: (groupId: string) =>
    fetchApi<GroupMember[]>(`/api/v1/org/groups/${groupId}/members`),

  addMember: (groupId: string, userId: string) =>
    fetchApi<{ message: string }>(`/api/v1/org/groups/${groupId}/members`, {
      method: "POST",
      body: JSON.stringify({ user_id: userId }),
    }),

  removeMember: (groupId: string, userId: string) =>
    fetchApi<{ message: string }>(`/api/v1/org/groups/${groupId}/members/${userId}`, {
      method: "DELETE",
    }),

  getGroupPermissions: (groupId: string) =>
    fetchApi<MenuPermission[]>(`/api/v1/org/groups/${groupId}/permissions`),

  setGroupPermissions: (groupId: string, permissions: Array<{ menu_key: string; can_access: boolean }>) =>
    fetchApi<MenuPermission[]>(`/api/v1/org/groups/${groupId}/permissions`, {
      method: "PUT",
      body: JSON.stringify({ permissions }),
    }),

  getMyMenus: () =>
    fetchApi<{ menu_keys: string[] }>("/api/v1/org/menus"),

  getMenuRegistry: () => fetchApi<{ menus: MenuItem[] }>("/api/v1/org/menus/registry"),
};