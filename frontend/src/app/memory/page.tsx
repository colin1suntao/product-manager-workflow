"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { memoryApi } from "@/lib/api";

interface Soul {
  id: string;
  name: string;
  personality: string;
  values: string[];
  behavior_rules: string[];
  communication_style: string;
  expertise_areas: string[];
  is_active: boolean;
}

interface Preference {
  id: string;
  category: string;
  key: string;
  value: string;
  created_at: string;
}

interface Memory {
  id: string;
  memory_type: string;
  summary: string;
  content: string;
  tags: string[];
  importance: number;
  created_at: string;
}

interface Reflection {
  id: string;
  period_start: string;
  period_end: string;
  total_tasks: number;
  successful_tasks: number;
  failed_tasks: number;
  key_learnings: string[];
  improvement_areas?: string[];
  action_items?: string[];
  created_at: string;
}

const MEMORY_TYPE_LABELS: Record<string, string> = {
  soul: "Soul",
  preference: "偏好",
  experience: "经验",
  mistake: "教训",
  learning: "学习",
  user_feedback: "反馈",
};

const MEMORY_TYPE_COLORS: Record<string, string> = {
  soul: "bg-purple-100 text-purple-700",
  preference: "bg-blue-100 text-blue-700",
  experience: "bg-green-100 text-green-700",
  mistake: "bg-red-100 text-red-700",
  learning: "bg-yellow-100 text-yellow-700",
  user_feedback: "bg-gray-100 text-gray-700",
};

type TabType = "soul" | "preferences" | "memories" | "reflections";

function ConfirmDialog({ open, title, message, onConfirm, onCancel }: {
  open: boolean;
  title: string;
  message: string;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
      <div className="bg-white rounded-lg shadow-xl p-6 max-w-sm w-full mx-4">
        <h3 className="text-lg font-semibold text-gray-900 mb-2">{title}</h3>
        <p className="text-sm text-gray-600 mb-6">{message}</p>
        <div className="flex justify-end gap-2">
          <button onClick={onCancel} className="px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-100 text-sm">
            取消
          </button>
          <button onClick={onConfirm} className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 text-sm">
            确认删除
          </button>
        </div>
      </div>
    </div>
  );
}

export default function MemoryPage() {
  const [activeTab, setActiveTab] = useState<TabType>("soul");
  const [soul, setSoul] = useState<Soul | null>(null);
  const [preferences, setPreferences] = useState<Preference[]>([]);
  const [memories, setMemories] = useState<Memory[]>([]);
  const [reflections, setReflections] = useState<Reflection[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Soul 编辑状态
  const [editingSoul, setEditingSoul] = useState<Partial<Soul>>({});

  // 偏好编辑状态
  const [newPref, setNewPref] = useState({ category: "", key: "", value: "" });

  // 记忆筛选（客户端过滤）
  const [memoryFilter, setMemoryFilter] = useState<string>("");
  const [filteredMemories, setFilteredMemories] = useState<Memory[]>([]);

  // 记忆分页
  const [memoryPage, setMemoryPage] = useState(1);
  const [memoryTotal, setMemoryTotal] = useState(0);
  const PAGE_SIZE = 10;

  // 各 tab 的加载状态
  const [soulLoading, setSoulLoading] = useState(false);
  const [prefLoading, setPrefLoading] = useState(false);
  const [memLoading, setMemLoading] = useState(false);
  const [reflLoading, setReflLoading] = useState(false);

  // 删除确认
  const [deleteTarget, setDeleteTarget] = useState<{ type: "preference" | "memory"; id: string } | null>(null);

  const successTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const showSuccess = useCallback((msg: string) => {
    setSuccess(msg);
    if (successTimer.current) clearTimeout(successTimer.current);
    successTimer.current = setTimeout(() => setSuccess(null), 3000);
  }, []);

  const showError = useCallback((msg: string) => {
    setError(msg);
    if (successTimer.current) clearTimeout(successTimer.current);
    successTimer.current = setTimeout(() => setError(null), 5000);
  }, []);

  // Tab 切换时懒加载
  useEffect(() => {
    if (activeTab === "soul" && !soul) loadSoul();
    if (activeTab === "preferences" && preferences.length === 0) loadPreferences();
    if (activeTab === "memories") loadMemories();
    if (activeTab === "reflections" && reflections.length === 0) loadReflections();
  }, [activeTab]);

  const loadSoul = async () => {
    setSoulLoading(true);
    try {
      const data = await memoryApi.getActiveSoul();
      setSoul(data);
      setEditingSoul(data);
    } catch (err) {
      console.error("Failed to load soul:", err);
    } finally {
      setSoulLoading(false);
    }
  };

  const loadPreferences = async () => {
    setPrefLoading(true);
    try {
      const data = await memoryApi.listPreferences();
      setPreferences(data.preferences);
    } catch (err) {
      console.error("Failed to load preferences:", err);
    } finally {
      setPrefLoading(false);
    }
  };

  const loadMemories = async (page = memoryPage) => {
    setMemLoading(true);
    try {
      const data = await memoryApi.listMemories(memoryFilter || undefined, page, PAGE_SIZE);
      setMemories(data.memories);
      setMemoryTotal(data.total);
      setMemoryPage(page);
      setFilteredMemories(data.memories);
    } catch (err) {
      console.error("Failed to load memories:", err);
    } finally {
      setMemLoading(false);
    }
  };

  const loadReflections = async () => {
    setReflLoading(true);
    try {
      const data = await memoryApi.listReflections();
      setReflections(data.reflections);
    } catch (err) {
      console.error("Failed to load reflections:", err);
    } finally {
      setReflLoading(false);
    }
  };

  const handleSaveSoul = async () => {
    try {
      setLoading(true);
      if (soul?.id && soul.id !== "default") {
        await memoryApi.updateSoul(soul.id, editingSoul);
      } else {
        await memoryApi.createSoul(editingSoul as any);
      }
      showSuccess("Soul 已保存");
      await loadSoul();
    } catch (err) {
      showError("保存 Soul 失败");
    } finally {
      setLoading(false);
    }
  };

  const handleAddPreference = async () => {
    if (!newPref.category || !newPref.key || !newPref.value) {
      showError("请填写完整的偏好信息");
      return;
    }
    try {
      await memoryApi.createPreference(newPref);
      showSuccess("偏好已添加");
      setNewPref({ category: "", key: "", value: "" });
      await loadPreferences();
    } catch (err) {
      showError("添加偏好失败");
    }
  };

  const handleDeletePreference = async (prefId: string) => {
    try {
      await memoryApi.deletePreference(prefId);
      showSuccess("偏好已删除");
      await loadPreferences();
    } catch (err) {
      showError("删除偏好失败");
    }
  };

  const handleDeleteMemory = async (memoryId: string) => {
    try {
      await memoryApi.deleteMemory(memoryId);
      showSuccess("记忆已删除");
      await loadMemories();
    } catch (err) {
      showError("删除记忆失败");
    }
  };

  const handleTriggerReflection = async () => {
    try {
      setLoading(true);
      await memoryApi.triggerReflection();
      showSuccess("反思已完成");
      await loadReflections();
    } catch (err) {
      showError("触发反思失败");
    } finally {
      setLoading(false);
    }
  };

  // 客户端过滤
  const handleMemoryFilterChange = (type: string) => {
    setMemoryFilter(type);
    setMemoryPage(1);
    // 直接用 API 过滤
    loadMemories(1);
  };

  const tabs = [
    { id: "soul" as TabType, label: "Agent Soul" },
    { id: "preferences" as TabType, label: "用户偏好" },
    { id: "memories" as TabType, label: "记忆库" },
    { id: "reflections" as TabType, label: "反思记录" },
  ];

  return (
    <div className="min-h-screen bg-gray-50">
      <ConfirmDialog
        open={deleteTarget !== null}
        title="确认删除"
        message="删除后无法恢复，确定要删除吗？"
        onConfirm={() => {
          if (!deleteTarget) return;
          if (deleteTarget.type === "preference") handleDeletePreference(deleteTarget.id);
          else handleDeleteMemory(deleteTarget.id);
          setDeleteTarget(null);
        }}
        onCancel={() => setDeleteTarget(null)}
      />

      <div className="max-w-7xl mx-auto px-4 py-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-8">记忆管理</h1>

        {/* Tabs */}
        <div className="flex space-x-1 mb-6 bg-white rounded-lg shadow-sm p-1">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${
                activeTab === tab.id
                  ? "bg-blue-600 text-white shadow-sm"
                  : "text-gray-600 hover:text-gray-900 hover:bg-gray-100"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Messages */}
        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm flex items-center justify-between">
            <span>{error}</span>
            <button onClick={() => setError(null)} className="ml-2 text-red-500 hover:text-red-700 font-medium">关闭</button>
          </div>
        )}
        {success && (
          <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded-lg text-green-700 text-sm flex items-center justify-between">
            <span>{success}</span>
            <button onClick={() => setSuccess(null)} className="ml-2 text-green-500 hover:text-green-700 font-medium">关闭</button>
          </div>
        )}

        {/* Soul Tab */}
        {activeTab === "soul" && (
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold mb-4">Agent Soul 配置</h2>
            <p className="text-gray-600 mb-6">
              定义 Agent 的个性特征、价值观和行为准则，让 Agent 以您期望的方式进行交互。
            </p>

            {soulLoading ? (
              <div className="flex items-center justify-center py-12 text-gray-400">
                <svg className="animate-spin h-5 w-5 mr-2" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"/><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
                加载中...
              </div>
            ) : (
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">名称</label>
                  <input type="text" value={editingSoul.name || ""} onChange={(e) => setEditingSoul({ ...editingSoul, name: e.target.value })} className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500" placeholder="给你的 Agent 起个名字" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">性格特征</label>
                  <textarea value={editingSoul.personality || ""} onChange={(e) => setEditingSoul({ ...editingSoul, personality: e.target.value })} className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500" rows={3} placeholder="描述 Agent 的性格特征，如：专业、友好、高效" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">核心价值观（每行一个）</label>
                  <textarea value={(editingSoul.values || []).join("\n")} onChange={(e) => setEditingSoul({ ...editingSoul, values: e.target.value.split("\n").filter((v) => v.trim()) })} className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500" rows={3} placeholder="准确性&#10;用户至上&#10;持续学习" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">行为准则（每行一条）</label>
                  <textarea value={(editingSoul.behavior_rules || []).join("\n")} onChange={(e) => setEditingSoul({ ...editingSoul, behavior_rules: e.target.value.split("\n").filter((v) => v.trim()) })} className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500" rows={4} placeholder="回答问题前先理解用户意图&#10;不确定时主动询问&#10;承认错误并及时纠正" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">沟通风格</label>
                  <input type="text" value={editingSoul.communication_style || ""} onChange={(e) => setEditingSoul({ ...editingSoul, communication_style: e.target.value })} className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500" placeholder="清晰简洁，使用专业但易懂的语言" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">专业领域（逗号分隔）</label>
                  <input type="text" value={(editingSoul.expertise_areas || []).join(", ")} onChange={(e) => setEditingSoul({ ...editingSoul, expertise_areas: e.target.value.split(",").map((v) => v.trim()).filter(Boolean) })} className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500" placeholder="产品管理, 需求分析, 项目管理" />
                </div>
                <button onClick={handleSaveSoul} disabled={loading} className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50">
                  {loading ? "保存中..." : "保存 Soul"}
                </button>
              </div>
            )}
          </div>
        )}

        {/* Preferences Tab */}
        {activeTab === "preferences" && (
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold mb-4">用户偏好</h2>
            <p className="text-gray-600 mb-6">设置您的个人偏好，Agent 会记住这些偏好并在交互中应用。</p>

            <div className="mb-6 p-4 bg-gray-50 rounded-lg">
              <h3 className="text-sm font-medium text-gray-700 mb-3">添加新偏好</h3>
              <div className="grid grid-cols-3 gap-3">
                <input type="text" value={newPref.category} onChange={(e) => setNewPref({ ...newPref, category: e.target.value })} className="px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500" placeholder="分类（如 language）" />
                <input type="text" value={newPref.key} onChange={(e) => setNewPref({ ...newPref, key: e.target.value })} className="px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500" placeholder="键（如 reply_style）" />
                <div className="flex gap-2">
                  <input type="text" value={newPref.value} onChange={(e) => setNewPref({ ...newPref, value: e.target.value })} className="flex-1 px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500" placeholder="值（如 简洁）" />
                  <button onClick={handleAddPreference} className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">添加</button>
                </div>
              </div>
            </div>

            {prefLoading ? (
              <div className="flex items-center justify-center py-8 text-gray-400">
                <svg className="animate-spin h-5 w-5 mr-2" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"/><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
                加载中...
              </div>
            ) : preferences.length === 0 ? (
              <div className="text-center py-8 text-gray-500">暂无偏好设置</div>
            ) : (
              <div className="space-y-3">
                {preferences.map((pref) => (
                  <div key={pref.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <div>
                      <span className="px-2 py-1 bg-blue-100 text-blue-700 rounded text-xs mr-2">{pref.category}</span>
                      <span className="font-medium">{pref.key}</span>
                      <span className="text-gray-500 mx-2">:</span>
                      <span>{pref.value}</span>
                    </div>
                    <button onClick={() => setDeleteTarget({ type: "preference", id: pref.id })} className="text-red-600 hover:text-red-800 text-sm">删除</button>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Memories Tab */}
        {activeTab === "memories" && (
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold mb-4">记忆库</h2>
            <p className="text-gray-600 mb-6">Agent 的长期记忆，包括经验、教训和学习记录。</p>

            <div className="mb-4 flex gap-2">
              {["", "experience", "mistake", "learning"].map((type) => (
                <button
                  key={type}
                  onClick={() => handleMemoryFilterChange(type)}
                  className={`px-3 py-1 rounded-full text-sm ${
                    memoryFilter === type ? "bg-blue-600 text-white" : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                  }`}
                >
                  {type ? MEMORY_TYPE_LABELS[type] : "全部"}
                </button>
              ))}
            </div>

            {memLoading ? (
              <div className="flex items-center justify-center py-8 text-gray-400">
                <svg className="animate-spin h-5 w-5 mr-2" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"/><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
                加载中...
              </div>
            ) : memories.length === 0 ? (
              <div className="text-center py-8 text-gray-500">暂无记忆</div>
            ) : (
              <>
                <div className="space-y-3">
                  {filteredMemories.map((memory) => (
                    <div key={memory.id} className="p-4 border rounded-lg">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-2">
                            <span className={`px-2 py-1 rounded text-xs ${MEMORY_TYPE_COLORS[memory.memory_type] || "bg-gray-100 text-gray-700"}`}>
                              {MEMORY_TYPE_LABELS[memory.memory_type] || memory.memory_type}
                            </span>
                            <span className="text-xs text-gray-400">重要性: {Math.round(memory.importance * 100)}%</span>
                          </div>
                          <p className="text-gray-900">{memory.summary}</p>
                          <p className="text-sm text-gray-600 mt-1">{memory.content}</p>
                          {memory.tags.length > 0 && (
                            <div className="flex gap-1 mt-2">
                              {memory.tags.map((tag) => (
                                <span key={tag} className="px-2 py-0.5 bg-gray-100 text-gray-600 rounded text-xs">{tag}</span>
                              ))}
                            </div>
                          )}
                        </div>
                        <button onClick={() => setDeleteTarget({ type: "memory", id: memory.id })} className="text-red-600 hover:text-red-800 ml-4 text-sm">删除</button>
                      </div>
                    </div>
                  ))}
                </div>

                {/* 分页 */}
                {memoryTotal > PAGE_SIZE && (
                  <div className="flex items-center justify-center gap-2 mt-6">
                    <button
                      onClick={() => loadMemories(memoryPage - 1)}
                      disabled={memoryPage <= 1}
                      className="px-3 py-1 text-sm border rounded hover:bg-gray-100 disabled:opacity-50"
                    >
                      上一页
                    </button>
                    <span className="text-sm text-gray-500">
                      第 {memoryPage} / {Math.ceil(memoryTotal / PAGE_SIZE)} 页（共 {memoryTotal} 条）
                    </span>
                    <button
                      onClick={() => loadMemories(memoryPage + 1)}
                      disabled={memoryPage >= Math.ceil(memoryTotal / PAGE_SIZE)}
                      className="px-3 py-1 text-sm border rounded hover:bg-gray-100 disabled:opacity-50"
                    >
                      下一页
                    </button>
                  </div>
                )}
              </>
            )}
          </div>
        )}

        {/* Reflections Tab */}
        {activeTab === "reflections" && (
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-semibold">反思记录</h2>
              <button onClick={handleTriggerReflection} disabled={loading} className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50">
                {loading ? "反思中..." : "触发反思"}
              </button>
            </div>
            <p className="text-gray-600 mb-6">Agent 定期反思历史工作，总结经验教训，改进表现。</p>

            {reflLoading ? (
              <div className="flex items-center justify-center py-8 text-gray-400">
                <svg className="animate-spin h-5 w-5 mr-2" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"/><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
                加载中...
              </div>
            ) : reflections.length === 0 ? (
              <div className="text-center py-8 text-gray-500">暂无反思记录，点击上方按钮触发反思</div>
            ) : (
              <div className="space-y-6">
                {reflections.map((reflection) => (
                  <div key={reflection.id} className="p-4 border rounded-lg">
                    <div className="mb-3">
                      <span className="text-sm text-gray-500">
                        {new Date(reflection.period_start).toLocaleDateString()} - {new Date(reflection.period_end).toLocaleDateString()}
                      </span>
                    </div>
                    <div className="grid grid-cols-3 gap-4 mb-4">
                      <div className="text-center p-3 bg-gray-50 rounded"><div className="text-2xl font-bold">{reflection.total_tasks}</div><div className="text-sm text-gray-500">总任务</div></div>
                      <div className="text-center p-3 bg-green-50 rounded"><div className="text-2xl font-bold text-green-600">{reflection.successful_tasks}</div><div className="text-sm text-gray-500">成功</div></div>
                      <div className="text-center p-3 bg-red-50 rounded"><div className="text-2xl font-bold text-red-600">{reflection.failed_tasks}</div><div className="text-sm text-gray-500">失败</div></div>
                    </div>
                    {reflection.key_learnings.length > 0 && (
                      <div className="mb-3">
                        <h4 className="text-sm font-medium text-gray-700 mb-1">关键学习</h4>
                        <ul className="list-disc list-inside text-sm text-gray-600">{reflection.key_learnings.map((l, i) => <li key={i}>{l}</li>)}</ul>
                      </div>
                    )}
                    {reflection.improvement_areas && reflection.improvement_areas.length > 0 && (
                      <div className="mb-3">
                        <h4 className="text-sm font-medium text-gray-700 mb-1">改进领域</h4>
                        <ul className="list-disc list-inside text-sm text-gray-600">{reflection.improvement_areas.map((a, i) => <li key={i}>{a}</li>)}</ul>
                      </div>
                    )}
                    {reflection.action_items && reflection.action_items.length > 0 && (
                      <div>
                        <h4 className="text-sm font-medium text-gray-700 mb-1">行动项</h4>
                        <ul className="list-disc list-inside text-sm text-gray-600">{reflection.action_items.map((item, i) => <li key={i}>{item}</li>)}</ul>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
