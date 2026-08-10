"use client";

import { useState, useEffect } from "react";
import { orgApi } from "@/lib/org-api";
import type { UserGroup, MenuPermission, MenuItem } from "@/types/api";

export default function PermissionsPage() {
  const [groups, setGroups] = useState<UserGroup[]>([]);
  const [selectedGroup, setSelectedGroup] = useState<UserGroup | null>(null);
  const [permissions, setPermissions] = useState<MenuPermission[]>([]);
  const [menuRegistry, setMenuRegistry] = useState<MenuItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const loadData = async () => {
    try {
      const [groupsData, menuData] = await Promise.all([
        orgApi.listGroups(),
        orgApi.getMenuRegistry(),
      ]);
      setGroups(groupsData);
      setMenuRegistry(menuData.menus);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "加载失败");
    } finally {
      setLoading(false);
    }
  };

  const loadPermissions = async (groupId: string) => {
    try {
      const data = await orgApi.getGroupPermissions(groupId);
      setPermissions(data);
    } catch {}
  };

  useEffect(() => {
    loadData();
  }, []);

  const getPermission = (menuKey: string): boolean => {
    const perm = permissions.find((p) => p.menu_key === menuKey);
    if (perm === undefined) return true;
    return perm.can_access;
  };

  const togglePermission = async (menuKey: string, currentValue: boolean) => {
    if (!selectedGroup) return;
    setSaving(true);
    try {
      const newPermissions = permissions
        .filter((p) => p.menu_key !== menuKey)
        .concat([{ id: "", group_id: selectedGroup.id, menu_key: menuKey, can_access: !currentValue, created_at: "" }]);
      await orgApi.setGroupPermissions(selectedGroup.id, [
        { menu_key: menuKey, can_access: !currentValue },
      ]);
      setPermissions(
        permissions.map((p) =>
          p.menu_key === menuKey ? { ...p, can_access: !currentValue } : p
        )
      );
      setSuccess("权限已更新");
      setTimeout(() => setSuccess(""), 2000);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "保存失败");
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div className="p-6 text-gray-500">加载中...</div>;

  return (
    <div className="max-w-5xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">权限设置</h1>
        <p className="text-sm text-gray-500 mt-1">管理用户组对各功能模块的访问权限</p>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4">
          {error}
          <button onClick={() => setError("")} className="float-right font-bold">&times;</button>
        </div>
      )}

      {success && (
        <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded mb-4">
          {success}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 用户组列表 */}
        <div className="bg-white rounded-lg shadow lg:col-span-1">
          <div className="p-4 border-b border-gray-200">
            <h2 className="font-semibold text-gray-900">选择用户组</h2>
          </div>
          <div className="divide-y divide-gray-100">
            {groups.map((group) => (
              <button
                key={group.id}
                className={`w-full text-left p-4 hover:bg-gray-50 ${
                  selectedGroup?.id === group.id ? "bg-blue-50" : ""
                }`}
                onClick={() => {
                  setSelectedGroup(group);
                  loadPermissions(group.id);
                }}
              >
                <div className="font-medium text-gray-900">{group.name}</div>
                <div className="text-sm text-gray-500">{group.member_count} 人</div>
              </button>
            ))}
            {groups.length === 0 && (
              <div className="p-6 text-center text-gray-400">暂无用户组</div>
            )}
          </div>
        </div>

        {/* 权限切换 */}
        <div className="bg-white rounded-lg shadow lg:col-span-2">
          {selectedGroup ? (
            <>
              <div className="p-4 border-b border-gray-200">
                <h2 className="font-semibold text-gray-900">
                  {selectedGroup.name} 的权限
                </h2>
                {saving && <span className="text-sm text-blue-500 ml-2">保存中...</span>}
              </div>
              <div className="divide-y divide-gray-100">
                {menuRegistry.map((menu) => {
                  const allowed = getPermission(menu.key);
                  return (
                    <div key={menu.key} className="p-4">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className="text-base">{menu.icon}</span>
                          <span className="font-medium text-gray-900">{menu.label}</span>
                        </div>
                        <label className="relative inline-flex items-center cursor-pointer">
                          <input
                            type="checkbox"
                            checked={allowed}
                            onChange={() => togglePermission(menu.key, allowed)}
                            className="sr-only peer"
                          />
                          <div className="w-9 h-5 bg-gray-200 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-blue-600"></div>
                        </label>
                      </div>
                      {menu.children && (
                        <div className="ml-8 mt-2 space-y-1">
                          {menu.children.map((child) => {
                            const childAllowed = getPermission(child.key);
                            return (
                              <div key={child.key} className="flex items-center justify-between py-1">
                                <span className="text-sm text-gray-600">{child.label}</span>
                                <label className="relative inline-flex items-center cursor-pointer">
                                  <input
                                    type="checkbox"
                                    checked={childAllowed}
                                    onChange={() => togglePermission(child.key, childAllowed)}
                                    className="sr-only peer"
                                  />
                                  <div className="w-8 h-4 bg-gray-200 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[1px] after:left-[1px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-3 after:w-3 after:transition-all peer-checked:bg-blue-600"></div>
                                </label>
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </>
          ) : (
            <div className="p-12 text-center text-gray-400">
              请选择一个用户组以编辑权限
            </div>
          )}
        </div>
      </div>
    </div>
  );
}