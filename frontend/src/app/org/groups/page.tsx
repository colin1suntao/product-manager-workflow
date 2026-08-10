"use client";

import { useState, useEffect, FormEvent } from "react";
import { orgApi } from "@/lib/org-api";
import type { UserGroup, GroupMember } from "@/types/api";

export default function GroupsPage() {
  const [groups, setGroups] = useState<UserGroup[]>([]);
  const [users, setUsers] = useState<Array<{ id: string; email: string; username: string }>>([]);
  const [selectedGroup, setSelectedGroup] = useState<UserGroup | null>(null);
  const [members, setMembers] = useState<GroupMember[]>([]);
  const [showCreate, setShowCreate] = useState(false);
  const [groupName, setGroupName] = useState("");
  const [groupDesc, setGroupDesc] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadGroups = async () => {
    try {
      const data = await orgApi.listGroups();
      setGroups(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "加载失败");
    } finally {
      setLoading(false);
    }
  };

  const loadUsers = async () => {
    try {
      const data = await orgApi.listUsers();
      setUsers(data);
    } catch {}
  };

  const loadMembers = async (groupId: string) => {
    try {
      const data = await orgApi.listMembers(groupId);
      setMembers(data);
    } catch {}
  };

  useEffect(() => {
    loadGroups();
    loadUsers();
  }, []);

  const handleCreate = async (e: FormEvent) => {
    e.preventDefault();
    try {
      await orgApi.createGroup({ name: groupName, description: groupDesc });
      setGroupName("");
      setGroupDesc("");
      setShowCreate(false);
      await loadGroups();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "创建失败");
    }
  };

  const handleDelete = async (groupId: string) => {
    if (!confirm("确定删除此用户组？")) return;
    try {
      await orgApi.deleteGroup(groupId);
      if (selectedGroup?.id === groupId) {
        setSelectedGroup(null);
        setMembers([]);
      }
      await loadGroups();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "删除失败");
    }
  };

  const handleAddMember = async (userId: string) => {
    if (!selectedGroup) return;
    try {
      await orgApi.addMember(selectedGroup.id, userId);
      await loadMembers(selectedGroup.id);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "添加失败");
    }
  };

  const handleRemoveMember = async (userId: string) => {
    if (!selectedGroup) return;
    if (!confirm("确定移除此成员？")) return;
    try {
      await orgApi.removeMember(selectedGroup.id, userId);
      await loadMembers(selectedGroup.id);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "移除失败");
    }
  };

  const availableUsers = users.filter(
    (u) => !members.some((m) => m.user_id === u.id)
  );

  if (loading) return <div className="p-6 text-gray-500">加载中...</div>;

  return (
    <div className="max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">用户组管理</h1>
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm"
        >
          {showCreate ? "取消" : "新建用户组"}
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4">
          {error}
          <button onClick={() => setError("")} className="float-right font-bold">&times;</button>
        </div>
      )}

      {showCreate && (
        <form onSubmit={handleCreate} className="bg-white rounded-lg shadow p-4 mb-6">
          <div className="space-y-3">
            <input
              type="text"
              value={groupName}
              onChange={(e) => setGroupName(e.target.value)}
              placeholder="用户组名称"
              required
              className="w-full px-4 py-2 border border-gray-300 rounded-md"
            />
            <input
              type="text"
              value={groupDesc}
              onChange={(e) => setGroupDesc(e.target.value)}
              placeholder="描述（可选）"
              className="w-full px-4 py-2 border border-gray-300 rounded-md"
            />
            <button
              type="submit"
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm"
            >
              创建
            </button>
          </div>
        </form>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 用户组列表 */}
        <div className="bg-white rounded-lg shadow">
          <div className="p-4 border-b border-gray-200">
            <h2 className="font-semibold text-gray-900">用户组 ({groups.length})</h2>
          </div>
          <div className="divide-y divide-gray-100">
            {groups.map((group) => (
              <div
                key={group.id}
                className={`p-4 cursor-pointer hover:bg-gray-50 ${
                  selectedGroup?.id === group.id ? "bg-blue-50" : ""
                }`}
                onClick={() => {
                  setSelectedGroup(group);
                  loadMembers(group.id);
                }}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <div className="font-medium text-gray-900">{group.name}</div>
                    {group.description && (
                      <div className="text-sm text-gray-500 mt-0.5">{group.description}</div>
                    )}
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-sm text-gray-400">{group.member_count} 人</span>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDelete(group.id);
                      }}
                      className="text-red-500 hover:text-red-700 text-sm"
                    >
                      删除
                    </button>
                  </div>
                </div>
              </div>
            ))}
            {groups.length === 0 && (
              <div className="p-6 text-center text-gray-400">暂无用户组</div>
            )}
          </div>
        </div>

        {/* 组成员管理 */}
        {selectedGroup && (
          <div className="bg-white rounded-lg shadow">
            <div className="p-4 border-b border-gray-200">
              <h2 className="font-semibold text-gray-900">
                {selectedGroup.name} - 成员 ({members.length})
              </h2>
            </div>

            {/* 添加成员 */}
            {availableUsers.length > 0 && (
              <div className="p-4 border-b border-gray-100">
                <select
                  className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                  value=""
                  onChange={(e) => {
                    if (e.target.value) handleAddMember(e.target.value);
                  }}
                >
                  <option value="">添加成员...</option>
                  {availableUsers.map((u) => (
                    <option key={u.id} value={u.id}>
                      {u.email} ({u.username})
                    </option>
                  ))}
                </select>
              </div>
            )}

            <div className="divide-y divide-gray-100">
              {members.map((member) => (
                <div key={member.id} className="p-4 flex items-center justify-between">
                  <div>
                    <div className="font-medium text-gray-900">{member.email}</div>
                    <div className="text-sm text-gray-500">{member.username}</div>
                  </div>
                  <button
                    onClick={() => handleRemoveMember(member.user_id)}
                    className="text-red-500 hover:text-red-700 text-sm"
                  >
                    移除
                  </button>
                </div>
              ))}
              {members.length === 0 && (
                <div className="p-6 text-center text-gray-400">暂无成员</div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}