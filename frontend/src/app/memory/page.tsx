"use client";

import { useState, useEffect } from "react";
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

  // 记忆筛选
  const [memoryFilter, setMemoryFilter] = useState<string>("");

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      await Promise.all([
        loadSoul(),
        loadPreferences(),
        loadMemories(),
        loadReflections(),
      ]);
    } catch (err) {
      setError("加载数据失败");
    } finally {
      setLoading(false);
    }
  };

  const loadSoul = async () => {
    try {
      const data = await memoryApi.getActiveSoul();
      setSoul(data);
      setEditingSoul(data);
    } catch (err) {
      console.error("Failed to load soul:", err);
    }
  };

  const loadPreferences = async () => {
    try {
      const data = await memoryApi.listPreferences();
      setPreferences(data.preferences);
    } catch (err) {
      console.error("Failed to load preferences:", err);
    }
  };

  const loadMemories = async () => {
    try {
      const data = await memoryApi.listMemories(memoryFilter || undefined);
      setMemories(data.memories);
    } catch (err) {
      console.error("Failed to load memories:", err);
    }
  };

  const loadReflections = async () => {
    try {
      const data = await memoryApi.listReflections();
      setReflections(data.reflections);
    } catch (err) {
      console.error("Failed to load reflections:", err);
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
      setSuccess("Soul 已保存");
      await loadSoul();
    } catch (err) {
      setError("保存 Soul 失败");
    } finally {
      setLoading(false);
    }
  };

  const handleAddPreference = async () => {
    if (!newPref.category || !newPref.key || !newPref.value) {
      setError("请填写完整的偏好信息");
      return;
    }

    try {
      await memoryApi.createPreference(newPref);
      setSuccess("偏好已添加");
      setNewPref({ category: "", key: "", value: "" });
      await loadPreferences();
    } catch (err) {
      setError("添加偏好失败");
    }
  };

  const handleDeletePreference = async (prefId: string) => {
    try {
      await memoryApi.deletePreference(prefId);
      setSuccess("偏好已删除");
      await loadPreferences();
    } catch (err) {
      setError("删除偏好失败");
    }
  };

  const handleDeleteMemory = async (memoryId: string) => {
    try {
      await memoryApi.deleteMemory(memoryId);
      setSuccess("记忆已删除");
      await loadMemories();
    } catch (err) {
      setError("删除记忆失败");
    }
  };

  const handleTriggerReflection = async () => {
    try {
      setLoading(true);
      await memoryApi.triggerReflection();
      setSuccess("反思已完成");
      await loadReflections();
    } catch (err) {
      setError("触发反思失败");
    } finally {
      setLoading(false);
    }
  };

  const tabs = [
    { id: "soul", label: "Agent Soul", icon: "🤖" },
    { id: "preferences", label: "用户偏好", icon: "⚙️" },
    { id: "memories", label: "记忆库", icon: "🧠" },
    { id: "reflections", label: "反思记录", icon: "📝" },
  ];

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 py-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-8">记忆管理</h1>

        {/* Tabs */}
        <div className="flex space-x-4 mb-6">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as TabType)}
              className={`px-4 py-2 rounded-lg flex items-center gap-2 ${
                activeTab === tab.id
                  ? "bg-blue-600 text-white"
                  : "bg-white text-gray-700 hover:bg-gray-100"
              }`}
            >
              <span>{tab.icon}</span>
              {tab.label}
            </button>
          ))}
        </div>

        {/* Messages */}
        {error && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
            {error}
            <button onClick={() => setError(null)} className="ml-2 underline">
              关闭
            </button>
          </div>
        )}
        {success && (
          <div className="mb-4 p-4 bg-green-50 border border-green-200 rounded-lg text-green-700">
            {success}
            <button onClick={() => setSuccess(null)} className="ml-2 underline">
              关闭
            </button>
          </div>
        )}

        {/* Soul Tab */}
        {activeTab === "soul" && (
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold mb-4">Agent Soul 配置</h2>
            <p className="text-gray-600 mb-6">
              定义 Agent 的个性特征、价值观和行为准则，让 Agent 以您期望的方式进行交互。
            </p>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  名称
                </label>
                <input
                  type="text"
                  value={editingSoul.name || ""}
                  onChange={(e) => setEditingSoul({ ...editingSoul, name: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                  placeholder="给你的 Agent 起个名字"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  性格特征
                </label>
                <textarea
                  value={editingSoul.personality || ""}
                  onChange={(e) => setEditingSoul({ ...editingSoul, personality: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                  rows={3}
                  placeholder="描述 Agent 的性格特征，如：专业、友好、高效"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  核心价值观（每行一个）
                </label>
                <textarea
                  value={(editingSoul.values || []).join("\n")}
                  onChange={(e) =>
                    setEditingSoul({
                      ...editingSoul,
                      values: e.target.value.split("\n").filter((v) => v.trim()),
                    })
                  }
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                  rows={3}
                  placeholder="准确性&#10;用户至上&#10;持续学习"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  行为准则（每行一条）
                </label>
                <textarea
                  value={(editingSoul.behavior_rules || []).join("\n")}
                  onChange={(e) =>
                    setEditingSoul({
                      ...editingSoul,
                      behavior_rules: e.target.value.split("\n").filter((v) => v.trim()),
                    })
                  }
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                  rows={4}
                  placeholder="回答问题前先理解用户意图&#10;不确定时主动询问&#10;承认错误并及时纠正"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  沟通风格
                </label>
                <input
                  type="text"
                  value={editingSoul.communication_style || ""}
                  onChange={(e) =>
                    setEditingSoul({ ...editingSoul, communication_style: e.target.value })
                  }
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                  placeholder="清晰简洁，使用专业但易懂的语言"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  专业领域（逗号分隔）
                </label>
                <input
                  type="text"
                  value={(editingSoul.expertise_areas || []).join(", ")}
                  onChange={(e) =>
                    setEditingSoul({
                      ...editingSoul,
                      expertise_areas: e.target.value.split(",").map((v) => v.trim()).filter(Boolean),
                    })
                  }
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                  placeholder="产品管理, 需求分析, 项目管理"
                />
              </div>

              <button
                onClick={handleSaveSoul}
                disabled={loading}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                {loading ? "保存中..." : "保存 Soul"}
              </button>
            </div>
          </div>
        )}

        {/* Preferences Tab */}
        {activeTab === "preferences" && (
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold mb-4">用户偏好</h2>
            <p className="text-gray-600 mb-6">
              设置您的个人偏好，Agent 会记住这些偏好并在交互中应用。
            </p>

            {/* Add Preference Form */}
            <div className="mb-6 p-4 bg-gray-50 rounded-lg">
              <h3 className="text-sm font-medium text-gray-700 mb-3">添加新偏好</h3>
              <div className="grid grid-cols-3 gap-3">
                <input
                  type="text"
                  value={newPref.category}
                  onChange={(e) => setNewPref({ ...newPref, category: e.target.value })}
                  className="px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                  placeholder="分类（如 language）"
                />
                <input
                  type="text"
                  value={newPref.key}
                  onChange={(e) => setNewPref({ ...newPref, key: e.target.value })}
                  className="px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                  placeholder="键（如 reply_style）"
                />
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={newPref.value}
                    onChange={(e) => setNewPref({ ...newPref, value: e.target.value })}
                    className="flex-1 px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                    placeholder="值（如 简洁）"
                  />
                  <button
                    onClick={handleAddPreference}
                    className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                  >
                    添加
                  </button>
                </div>
              </div>
            </div>

            {/* Preferences List */}
            {preferences.length === 0 ? (
              <div className="text-center py-8 text-gray-500">暂无偏好设置</div>
            ) : (
              <div className="space-y-3">
                {preferences.map((pref) => (
                  <div
                    key={pref.id}
                    className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                  >
                    <div>
                      <span className="px-2 py-1 bg-blue-100 text-blue-700 rounded text-xs mr-2">
                        {pref.category}
                      </span>
                      <span className="font-medium">{pref.key}</span>
                      <span className="text-gray-500 mx-2">:</span>
                      <span>{pref.value}</span>
                    </div>
                    <button
                      onClick={() => handleDeletePreference(pref.id)}
                      className="text-red-600 hover:text-red-800"
                    >
                      删除
                    </button>
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
            <p className="text-gray-600 mb-6">
              Agent 的长期记忆，包括经验、教训和学习记录。
            </p>

            {/* Filter */}
            <div className="mb-4 flex gap-2">
              {["", "experience", "mistake", "learning"].map((type) => (
                <button
                  key={type}
                  onClick={() => {
                    setMemoryFilter(type);
                    loadMemories();
                  }}
                  className={`px-3 py-1 rounded-full text-sm ${
                    memoryFilter === type
                      ? "bg-blue-600 text-white"
                      : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                  }`}
                >
                  {type ? MEMORY_TYPE_LABELS[type] : "全部"}
                </button>
              ))}
            </div>

            {/* Memories List */}
            {memories.length === 0 ? (
              <div className="text-center py-8 text-gray-500">暂无记忆</div>
            ) : (
              <div className="space-y-3">
                {memories.map((memory) => (
                  <div key={memory.id} className="p-4 border rounded-lg">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-2">
                          <span
                            className={`px-2 py-1 rounded text-xs ${
                              MEMORY_TYPE_COLORS[memory.memory_type] || "bg-gray-100 text-gray-700"
                            }`}
                          >
                            {MEMORY_TYPE_LABELS[memory.memory_type] || memory.memory_type}
                          </span>
                          <span className="text-xs text-gray-400">
                            重要性: {Math.round(memory.importance * 100)}%
                          </span>
                        </div>
                        <p className="text-gray-900">{memory.summary}</p>
                        <p className="text-sm text-gray-600 mt-1">{memory.content}</p>
                        {memory.tags.length > 0 && (
                          <div className="flex gap-1 mt-2">
                            {memory.tags.map((tag) => (
                              <span
                                key={tag}
                                className="px-2 py-0.5 bg-gray-100 text-gray-600 rounded text-xs"
                              >
                                {tag}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                      <button
                        onClick={() => handleDeleteMemory(memory.id)}
                        className="text-red-600 hover:text-red-800 ml-4"
                      >
                        删除
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Reflections Tab */}
        {activeTab === "reflections" && (
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-semibold">反思记录</h2>
              <button
                onClick={handleTriggerReflection}
                disabled={loading}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                {loading ? "反思中..." : "触发反思"}
              </button>
            </div>
            <p className="text-gray-600 mb-6">
              Agent 定期反思历史工作，总结经验教训，改进表现。
            </p>

            {reflections.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                暂无反思记录，点击上方按钮触发反思
              </div>
            ) : (
              <div className="space-y-6">
                {reflections.map((reflection) => (
                  <div key={reflection.id} className="p-4 border rounded-lg">
                    <div className="mb-3">
                      <span className="text-sm text-gray-500">
                        {new Date(reflection.period_start).toLocaleDateString()} -{" "}
                        {new Date(reflection.period_end).toLocaleDateString()}
                      </span>
                    </div>

                    <div className="grid grid-cols-3 gap-4 mb-4">
                      <div className="text-center p-3 bg-gray-50 rounded">
                        <div className="text-2xl font-bold">{reflection.total_tasks}</div>
                        <div className="text-sm text-gray-500">总任务</div>
                      </div>
                      <div className="text-center p-3 bg-green-50 rounded">
                        <div className="text-2xl font-bold text-green-600">
                          {reflection.successful_tasks}
                        </div>
                        <div className="text-sm text-gray-500">成功</div>
                      </div>
                      <div className="text-center p-3 bg-red-50 rounded">
                        <div className="text-2xl font-bold text-red-600">
                          {reflection.failed_tasks}
                        </div>
                        <div className="text-sm text-gray-500">失败</div>
                      </div>
                    </div>

                    {reflection.key_learnings.length > 0 && (
                      <div className="mb-3">
                        <h4 className="text-sm font-medium text-gray-700 mb-1">关键学习</h4>
                        <ul className="list-disc list-inside text-sm text-gray-600">
                          {reflection.key_learnings.map((learning, idx) => (
                            <li key={idx}>{learning}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {reflection.improvement_areas && reflection.improvement_areas.length > 0 && (
                      <div className="mb-3">
                        <h4 className="text-sm font-medium text-gray-700 mb-1">改进领域</h4>
                        <ul className="list-disc list-inside text-sm text-gray-600">
                          {reflection.improvement_areas.map((area, idx) => (
                            <li key={idx}>{area}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {reflection.action_items && reflection.action_items.length > 0 && (
                      <div>
                        <h4 className="text-sm font-medium text-gray-700 mb-1">行动项</h4>
                        <ul className="list-disc list-inside text-sm text-gray-600">
                          {reflection.action_items.map((item, idx) => (
                            <li key={idx}>{item}</li>
                          ))}
                        </ul>
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
