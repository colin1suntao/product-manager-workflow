"use client";

import { useEffect, useState, useCallback } from "react";
import { integrationApi } from "@/lib/api";
import type { IntegrationConfig, SyncTask } from "@/types/api";

const INTEGRATION_TYPES = [
  { value: "jira", label: "Jira" },
  { value: "trello", label: "Trello" },
  { value: "github", label: "GitHub" },
  { value: "gitlab", label: "GitLab" },
  { value: "figma", label: "Figma" },
  { value: "slack", label: "Slack" },
  { value: "feishu", label: "飞书" },
];

const SYNC_STATUS_LABELS: Record<string, string> = {
  pending: "等待中",
  running: "运行中",
  completed: "已完成",
  failed: "失败",
  cancelled: "已取消",
};

const SYNC_STATUS_COLORS: Record<string, string> = {
  pending: "bg-gray-100 text-gray-700",
  running: "bg-blue-100 text-blue-700",
  completed: "bg-green-100 text-green-700",
  failed: "bg-red-100 text-red-700",
  cancelled: "bg-gray-200 text-gray-600",
};

export default function IntegrationsPage() {
  const [configs, setConfigs] = useState<IntegrationConfig[]>([]);
  const [syncTasks, setSyncTasks] = useState<SyncTask[]>([]);
  const [loading, setLoading] = useState(true);
  const [showConfigForm, setShowConfigForm] = useState(false);
  const [editingConfigId, setEditingConfigId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"configs" | "tasks">("configs");

  // Config form
  const [configName, setConfigName] = useState("");
  const [configType, setConfigType] = useState("");
  const [configEndpoint, setConfigEndpoint] = useState("");
  const [configApiKey, setConfigApiKey] = useState("");

  // Task form
  const [taskConfigId, setTaskConfigId] = useState("");
  const [taskDirection, setTaskDirection] = useState<"import" | "export">("import");

  const fetchConfigs = useCallback(async () => {
    try {
      const data = await integrationApi.listConfigs();
      setConfigs(data.configs);
    } catch {
      // ignore
    }
  }, []);

  const fetchSyncTasks = useCallback(async () => {
    try {
      const data = await integrationApi.listSyncTasks();
      setSyncTasks(data.tasks);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchConfigs();
    fetchSyncTasks();
  }, [fetchConfigs, fetchSyncTasks]);

  function resetConfigForm() {
    setConfigName("");
    setConfigType("");
    setConfigEndpoint("");
    setConfigApiKey("");
    setShowConfigForm(false);
    setEditingConfigId(null);
  }

  async function handleConfigSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!configName || !configType) return;

    try {
      if (editingConfigId) {
        await integrationApi.updateConfig(editingConfigId, {
          name: configName,
          api_endpoint: configEndpoint || undefined,
          api_key: configApiKey || undefined,
        });
      } else {
        await integrationApi.createConfig({
          name: configName,
          integration_type: configType as IntegrationConfig["integration_type"],
          api_endpoint: configEndpoint || undefined,
          api_key: configApiKey || undefined,
        });
      }
      resetConfigForm();
      fetchConfigs();
    } catch {
      // ignore
    }
  }

  function handleEditConfig(config: IntegrationConfig) {
    setConfigName(config.name);
    setConfigType(config.integration_type);
    setConfigEndpoint(config.api_endpoint || "");
    setConfigApiKey("");
    setEditingConfigId(config.id);
    setShowConfigForm(true);
  }

  async function handleDeleteConfig(id: string) {
    if (!confirm("确定要删除这个集成配置吗？")) return;
    try {
      await integrationApi.deleteConfig(id);
      fetchConfigs();
    } catch {
      // ignore
    }
  }

  async function handleToggleConfig(config: IntegrationConfig) {
    try {
      await integrationApi.updateConfig(config.id, {
        enabled: !config.enabled,
      });
      fetchConfigs();
    } catch {
      // ignore
    }
  }

  async function handleCreateTask(e: React.FormEvent) {
    e.preventDefault();
    if (!taskConfigId) return;

    try {
      await integrationApi.createSyncTask(taskConfigId, {
        direction: taskDirection,
      });
      setTaskConfigId("");
      fetchSyncTasks();
    } catch {
      // ignore
    }
  }

  async function handleCancelTask(id: string) {
    try {
      await integrationApi.cancelSyncTask(id);
      fetchSyncTasks();
    } catch {
      // ignore
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-gray-500">加载中...</p>
      </div>
    );
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">集成配置</h1>

      {/* 标签页 */}
      <div className="flex gap-1 mb-6 bg-gray-100 rounded-lg p-1 w-fit">
        <button
          onClick={() => setActiveTab("configs")}
          className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
            activeTab === "configs"
              ? "bg-white text-gray-900 shadow"
              : "text-gray-500 hover:text-gray-700"
          }`}
        >
          集成配置
        </button>
        <button
          onClick={() => setActiveTab("tasks")}
          className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
            activeTab === "tasks"
              ? "bg-white text-gray-900 shadow"
              : "text-gray-500 hover:text-gray-700"
          }`}
        >
          同步任务
        </button>
      </div>

      {/* 集成配置 */}
      {activeTab === "configs" && (
        <>
          <div className="flex justify-end mb-4">
            <button
              onClick={() => {
                resetConfigForm();
                setShowConfigForm(true);
              }}
              className="px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm"
            >
              新增集成
            </button>
          </div>

          {showConfigForm && (
            <div className="mb-6 p-4 bg-white rounded-lg border border-gray-200">
              <h2 className="text-lg font-semibold mb-4">
                {editingConfigId ? "编辑集成" : "新增集成"}
              </h2>
              <form onSubmit={handleConfigSubmit} className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      名称 <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="text"
                      value={configName}
                      onChange={(e) => setConfigName(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      类型 <span className="text-red-500">*</span>
                    </label>
                    <select
                      value={configType}
                      onChange={(e) => setConfigType(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                      required
                      disabled={!!editingConfigId}
                    >
                      <option value="">请选择</option>
                      {INTEGRATION_TYPES.map((t) => (
                        <option key={t.value} value={t.value}>
                          {t.label}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    API 地址
                  </label>
                  <input
                    type="text"
                    value={configEndpoint}
                    onChange={(e) => setConfigEndpoint(e.target.value)}
                    placeholder="https://api.example.com"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    API 密钥
                  </label>
                  <input
                    type="password"
                    value={configApiKey}
                    onChange={(e) => setConfigApiKey(e.target.value)}
                    placeholder="留空则不更新密钥"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                  />
                </div>
                <div className="flex gap-3">
                  <button
                    type="submit"
                    className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm"
                  >
                    保存
                  </button>
                  <button
                    type="button"
                    onClick={resetConfigForm}
                    className="px-4 py-2 bg-gray-100 rounded-lg hover:bg-gray-200 text-sm"
                  >
                    取消
                  </button>
                </div>
              </form>
            </div>
          )}

          {configs.length === 0 ? (
            <div className="text-center py-12 bg-white rounded-lg border border-gray-200">
              <p className="text-gray-500">暂无集成配置</p>
            </div>
          ) : (
            <div className="space-y-3">
              {configs.map((config) => (
                <div
                  key={config.id}
                  className="bg-white rounded-lg border border-gray-200 p-4"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div>
                        <h3 className="font-medium">{config.name}</h3>
                        <p className="text-sm text-gray-500">
                          {INTEGRATION_TYPES.find((t) => t.value === config.integration_type)?.label || config.integration_type}
                          {config.api_endpoint && ` · ${config.api_endpoint}`}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <label className="flex items-center gap-2 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={config.enabled}
                          onChange={() => handleToggleConfig(config)}
                          className="w-4 h-4"
                        />
                        <span className="text-sm text-gray-600">
                          {config.enabled ? "已启用" : "已禁用"}
                        </span>
                      </label>
                      <button
                        onClick={() => handleEditConfig(config)}
                        className="px-2 py-1 bg-gray-50 rounded text-xs hover:bg-gray-100"
                      >
                        编辑
                      </button>
                      <button
                        onClick={() => handleDeleteConfig(config.id)}
                        className="px-2 py-1 bg-red-50 text-red-600 rounded text-xs hover:bg-red-100"
                      >
                        删除
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {/* 同步任务 */}
      {activeTab === "tasks" && (
        <>
          <div className="mb-6 p-4 bg-white rounded-lg border border-gray-200">
            <h2 className="text-lg font-semibold mb-4">创建同步任务</h2>
            <form onSubmit={handleCreateTask} className="flex gap-4 items-end">
              <div className="flex-1">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  目标集成
                </label>
                <select
                  value={taskConfigId}
                  onChange={(e) => setTaskConfigId(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                  required
                >
                  <option value="">请选择</option>
                  {configs
                    .filter((c) => c.enabled)
                    .map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.name}
                      </option>
                    ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  方向
                </label>
                <select
                  value={taskDirection}
                  onChange={(e) =>
                    setTaskDirection(e.target.value as "import" | "export")
                  }
                  className="px-3 py-2 border border-gray-300 rounded-lg text-sm"
                >
                  <option value="import">导入</option>
                  <option value="export">导出</option>
                </select>
              </div>
              <button
                type="submit"
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm"
              >
                创建任务
              </button>
            </form>
          </div>

          {syncTasks.length === 0 ? (
            <div className="text-center py-12 bg-white rounded-lg border border-gray-200">
              <p className="text-gray-500">暂无同步任务</p>
            </div>
          ) : (
            <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 border-b border-gray-200">
                  <tr>
                    <th className="px-4 py-3 text-left font-medium text-gray-500">ID</th>
                    <th className="px-4 py-3 text-left font-medium text-gray-500">方向</th>
                    <th className="px-4 py-3 text-left font-medium text-gray-500">状态</th>
                    <th className="px-4 py-3 text-left font-medium text-gray-500">创建时间</th>
                    <th className="px-4 py-3 text-left font-medium text-gray-500">操作</th>
                  </tr>
                </thead>
                <tbody>
                  {syncTasks.map((task) => (
                    <tr key={task.id} className="border-b border-gray-100">
                      <td className="px-4 py-3 font-mono text-xs">{task.id}</td>
                      <td className="px-4 py-3">
                        {task.direction === "import" ? "导入" : "导出"}
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={`px-2 py-0.5 rounded-full text-xs ${SYNC_STATUS_COLORS[task.status]}`}
                        >
                          {SYNC_STATUS_LABELS[task.status] || task.status}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-gray-500">
                        {new Date(task.created_at).toLocaleString("zh-CN")}
                      </td>
                      <td className="px-4 py-3">
                        {(task.status === "pending" || task.status === "running") && (
                          <button
                            onClick={() => handleCancelTask(task.id)}
                            className="px-2 py-1 bg-red-50 text-red-600 rounded text-xs hover:bg-red-100"
                          >
                            取消
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  );
}
