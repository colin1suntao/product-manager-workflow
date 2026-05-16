"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { getAccessToken } from "@/lib/auth";
import { skillsApi } from "@/lib/api";

interface PMSkill {
  name: string;
  description: string;
  type: string;
  best_for: string[];
  scenarios: string[];
  estimated_time: string;
}

interface SkillDetail {
  name: string;
  description: string;
  intent: string;
  type: string;
  best_for: string[];
  scenarios: string[];
  estimated_time: string;
  system_prompt: string;
  steps: string[];
}

const SKILL_TYPE_LABELS: Record<string, string> = {
  component: "组件技能",
  interactive: "交互技能",
  workflow: "工作流技能",
  native: "原生技能",
};

const SKILL_TYPE_BADGES: Record<string, { bg: string; text: string; dot: string }> = {
  component: { bg: "bg-blue-50", text: "text-blue-700", dot: "bg-blue-500" },
  interactive: { bg: "bg-emerald-50", text: "text-emerald-700", dot: "bg-emerald-500" },
  workflow: { bg: "bg-violet-50", text: "text-violet-700", dot: "bg-violet-500" },
  native: { bg: "bg-gray-50", text: "text-gray-600", dot: "bg-gray-400" },
};

const TYPE_ICONS: Record<string, string> = {
  component: "🧩",
  interactive: "🔄",
  workflow: "⚙️",
  native: "📦",
};

const NEW_SKILL_TYPE_OPTIONS = [
  { value: "component", label: "组件技能" },
  { value: "interactive", label: "交互技能" },
  { value: "workflow", label: "工作流技能" },
];

const FILTER_TABS = [
  { value: "", label: "全部" },
  { value: "component", label: "组件技能" },
  { value: "interactive", label: "交互技能" },
  { value: "workflow", label: "工作流技能" },
];

export default function SkillsPage() {
  const router = useRouter();
  const [skills, setSkills] = useState<PMSkill[]>([]);
  const [selectedSkill, setSelectedSkill] = useState<SkillDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [filterType, setFilterType] = useState<string>("");
  const [searchQuery, setSearchQuery] = useState("");

  const [showNewModal, setShowNewModal] = useState(false);
  const [showImportModal, setShowImportModal] = useState(false);
  const [importTab, setImportTab] = useState<"paste" | "upload">("paste");
  const [importContent, setImportContent] = useState("");
  const [importFile, setImportFile] = useState<File | null>(null);
  const [importing, setImporting] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [successMsg, setSuccessMsg] = useState("");

  const [newForm, setNewForm] = useState({
    name: "",
    description: "",
    system_prompt: "",
    type: "component",
    steps: "",
    best_for: "",
    scenarios: "",
    estimated_time: "",
  });

  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!getAccessToken()) {
      router.push("/auth/login");
      return;
    }
    loadSkills();
  }, [router, filterType]);

  const loadSkills = async () => {
    setLoading(true);
    try {
      const token = getAccessToken();
      const query = filterType ? `?skill_type=${filterType}` : "";
      const response = await fetch(`/api/v1/skills/list${query}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        const data = await response.json();
        setSkills(data.skills);
      }
    } catch (error) {
      console.error("Failed to load skills:", error);
    } finally {
      setLoading(false);
    }
  };

  const loadSkillDetail = async (skillName: string) => {
    try {
      const token = getAccessToken();
      const response = await fetch(`/api/v1/skills/${skillName}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        const data = await response.json();
        setSelectedSkill(data);
      }
    } catch (error) {
      console.error("Failed to load skill detail:", error);
    }
  };

  const filteredSkills = skills.filter(
    (skill) =>
      skill.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      skill.description.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const typeCounts = skills.reduce<Record<string, number>>((acc, s) => {
    const t = s.type || "native";
    acc[t] = (acc[t] || 0) + 1;
    return acc;
  }, {});

  const handleCreateSkill = async () => {
    if (!newForm.name.trim()) {
      setError("技能名称不能为空");
      return;
    }
    setSaving(true);
    setError("");
    try {
      await skillsApi.import({
        name: newForm.name.trim(),
        description: newForm.description.trim(),
        system_prompt: newForm.system_prompt.trim(),
        type: newForm.type,
        steps: newForm.steps.split("\n").map((s) => s.trim()).filter(Boolean),
        best_for: newForm.best_for.split("\n").map((s) => s.trim()).filter(Boolean),
        scenarios: newForm.scenarios.split("\n").map((s) => s.trim()).filter(Boolean),
        estimated_time: newForm.estimated_time.trim() || undefined,
      });
      setShowNewModal(false);
      setNewForm({ name: "", description: "", system_prompt: "", type: "component", steps: "", best_for: "", scenarios: "", estimated_time: "" });
      setSuccessMsg("技能创建成功");
      setTimeout(() => setSuccessMsg(""), 3000);
      loadSkills();
    } catch (err) {
      setError(err instanceof Error ? err.message : "创建失败");
    } finally {
      setSaving(false);
    }
  };

  const handleImportPaste = async () => {
    if (!importContent.trim()) {
      setError("请输入 SKILL.md 格式内容");
      return;
    }
    setImporting(true);
    setError("");
    try {
      await skillsApi.import({ content: importContent.trim() });
      setShowImportModal(false);
      setImportContent("");
      setSuccessMsg("技能导入成功");
      setTimeout(() => setSuccessMsg(""), 3000);
      loadSkills();
    } catch (err) {
      setError(err instanceof Error ? err.message : "导入失败");
    } finally {
      setImporting(false);
    }
  };

  const handleImportFile = async () => {
    if (!importFile) {
      setError("请选择文件");
      return;
    }
    setImporting(true);
    setError("");
    try {
      await skillsApi.importFile(importFile);
      setShowImportModal(false);
      setImportFile(null);
      setSuccessMsg("技能导入成功");
      setTimeout(() => setSuccessMsg(""), 3000);
      loadSkills();
    } catch (err) {
      setError(err instanceof Error ? err.message : "导入失败");
    } finally {
      setImporting(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 p-8">
      <div className="max-w-7xl mx-auto">
        {/* 标题栏 + 操作按钮 */}
        <div className="flex items-start justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 tracking-tight">PM Skills 技能库</h1>
            <p className="mt-1.5 text-gray-500">
              基于 Product-Manager-Skills 的 47 个专业产品经理技能，帮助你生成更专业、更精细的产品文档
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => { setError(""); setShowImportModal(true); }}
              className="inline-flex items-center gap-2 px-4 py-2.5 bg-white text-gray-700 border border-gray-300 rounded-xl text-sm font-medium hover:bg-gray-50 hover:border-gray-400 transition-all shadow-sm"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" /></svg>
              导入技能
            </button>
            <button
              onClick={() => { setError(""); setShowNewModal(true); }}
              className="inline-flex items-center gap-2 px-4 py-2.5 bg-gradient-to-r from-blue-600 to-blue-700 text-white rounded-xl text-sm font-medium hover:from-blue-700 hover:to-blue-800 transition-all shadow-sm shadow-blue-200"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" /></svg>
              新建技能
            </button>
          </div>
        </div>

        {successMsg && (
          <div className="mb-5 p-4 bg-emerald-50 border border-emerald-200 text-emerald-700 rounded-xl text-sm flex items-center gap-2">
            <svg className="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
            {successMsg}
          </div>
        )}

        {error && (
          <div className="mb-5 p-4 bg-red-50 border border-red-200 text-red-700 rounded-xl text-sm flex items-center gap-2">
            <svg className="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
            {error}
          </div>
        )}

        {/* 统计概览 */}
        <div className="grid grid-cols-5 gap-3 mb-6">
          {FILTER_TABS.map((tab) => {
            const count = tab.value ? (typeCounts[tab.value] || 0) : skills.length;
            const isActive = filterType === tab.value;
            const badge = tab.value ? SKILL_TYPE_BADGES[tab.value] : null;
            return (
              <button
                key={tab.value}
                onClick={() => setFilterType(tab.value)}
                className={`relative flex flex-col items-center gap-1 p-4 rounded-xl border transition-all ${
                  isActive
                    ? "bg-white border-blue-200 shadow-sm shadow-blue-100"
                    : "bg-white/80 border-gray-200 hover:border-gray-300 hover:shadow-sm"
                }`}
              >
                {badge && <span className={`w-2 h-2 rounded-full ${badge.dot}`} />}
                <span className={`text-sm font-medium ${isActive ? "text-blue-700" : "text-gray-600"}`}>
                  {tab.label}
                </span>
                <span className={`text-2xl font-bold ${isActive ? "text-blue-600" : "text-gray-800"}`}>
                  {count}
                </span>
              </button>
            );
          })}
        </div>

        {/* 搜索框 */}
        <div className="relative mb-6">
          <svg className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            type="text"
            placeholder="搜索技能名称或描述..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-11 pr-4 py-3 bg-white border border-gray-200 rounded-xl text-sm focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400 transition-all shadow-sm"
          />
        </div>

        {/* 主内容区 */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* 技能列表 */}
          <div className="lg:col-span-2">
            {loading ? (
              <div className="bg-white rounded-2xl border border-gray-200 p-16 text-center shadow-sm">
                <div className="animate-spin rounded-full h-10 w-10 border-[3px] border-blue-100 border-t-blue-600 mx-auto"></div>
                <p className="mt-4 text-gray-400 text-sm">加载技能列表...</p>
              </div>
            ) : filteredSkills.length === 0 ? (
              <div className="bg-white rounded-2xl border border-gray-200 p-16 text-center shadow-sm">
                <p className="text-gray-400">未找到匹配的技能</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {filteredSkills.map((skill) => {
                  const badge = SKILL_TYPE_BADGES[skill.type] || SKILL_TYPE_BADGES.native;
                  return (
                    <div
                      key={skill.name}
                      onClick={() => loadSkillDetail(skill.name)}
                      className={`group bg-white rounded-xl border p-4 cursor-pointer transition-all hover:shadow-md ${
                        selectedSkill?.name === skill.name
                          ? "border-blue-300 ring-2 ring-blue-100 shadow-sm"
                          : "border-gray-200 hover:border-gray-300"
                      }`}
                    >
                      <div className="flex items-start justify-between mb-2">
                        <div className="flex items-center gap-2 min-w-0">
                          <span className="text-lg shrink-0">{TYPE_ICONS[skill.type] || "📄"}</span>
                          <h3 className="font-semibold text-gray-900 text-sm truncate">{skill.name}</h3>
                        </div>
                        <span className={`shrink-0 px-2.5 py-1 rounded-lg text-[11px] font-medium ${badge.bg} ${badge.text}`}>
                          {SKILL_TYPE_LABELS[skill.type] || skill.type}
                        </span>
                      </div>
                      <p className="text-gray-500 text-xs leading-relaxed line-clamp-2 pl-8 mb-2">
                        {skill.description}
                      </p>
                      {skill.estimated_time && (
                        <div className="flex items-center gap-1.5 pl-8">
                          <svg className="w-3 h-3 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                          <span className="text-gray-400 text-xs">{skill.estimated_time}</span>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* 技能详情 */}
          <div className="lg:col-span-1">
            {selectedSkill ? (
              <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden sticky top-8">
                <div className="p-6">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xl">{TYPE_ICONS[selectedSkill.type] || "📄"}</span>
                    <h2 className="text-lg font-bold text-gray-900">{selectedSkill.name}</h2>
                  </div>
                  <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-medium ${SKILL_TYPE_BADGES[selectedSkill.type]?.bg || SKILL_TYPE_BADGES.native.bg} ${SKILL_TYPE_BADGES[selectedSkill.type]?.text || SKILL_TYPE_BADGES.native.text}`}>
                    <span className={`w-1.5 h-1.5 rounded-full ${SKILL_TYPE_BADGES[selectedSkill.type]?.dot || SKILL_TYPE_BADGES.native.dot}`} />
                    {SKILL_TYPE_LABELS[selectedSkill.type] || selectedSkill.type}
                  </span>

                  <p className="text-sm text-gray-500 mt-4 leading-relaxed">{selectedSkill.description}</p>

                  {selectedSkill.intent && (
                    <div className="mt-5">
                      <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">意图</h4>
                      <p className="text-sm text-gray-700">{selectedSkill.intent}</p>
                    </div>
                  )}

                  {selectedSkill.best_for.length > 0 && (
                    <div className="mt-5">
                      <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">最佳使用场景</h4>
                      <div className="space-y-1.5">
                        {selectedSkill.best_for.map((item, i) => (
                          <div key={i} className="flex items-start gap-2 text-sm text-gray-600">
                            <span className="w-1.5 h-1.5 rounded-full bg-blue-400 mt-1.5 shrink-0" />
                            {item}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {selectedSkill.scenarios.length > 0 && (
                    <div className="mt-5">
                      <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">使用示例</h4>
                      <div className="space-y-2">
                        {selectedSkill.scenarios.map((item, i) => (
                          <div key={i} className="flex items-start gap-2 text-sm text-gray-600 bg-gray-50 rounded-lg p-2.5">
                            <span className="text-blue-500 font-mono text-xs mt-0.5">{i + 1}.</span>
                            {item}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {selectedSkill.steps.length > 0 && (
                    <div className="mt-5">
                      <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">执行步骤</h4>
                      <div className="space-y-2">
                        {selectedSkill.steps.map((step, i) => (
                          <div key={i} className="flex items-start gap-3 text-sm text-gray-600">
                            <span className="flex items-center justify-center w-5 h-5 rounded-full bg-blue-100 text-blue-700 text-xs font-medium shrink-0 mt-0.5">{i + 1}</span>
                            {step}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  <button
                    onClick={() => router.push(`/requirements?skill=${selectedSkill.name}`)}
                    className="w-full mt-6 px-4 py-2.5 bg-gradient-to-r from-blue-600 to-blue-700 text-white rounded-xl text-sm font-medium hover:from-blue-700 hover:to-blue-800 transition-all shadow-sm shadow-blue-200"
                  >
                    使用此技能
                  </button>
                </div>
              </div>
            ) : (
              <div className="bg-white rounded-2xl border border-gray-200 p-12 text-center shadow-sm">
                <div className="w-16 h-16 bg-gray-50 rounded-2xl flex items-center justify-center mx-auto mb-4">
                  <svg className="w-8 h-8 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" /></svg>
                </div>
                <p className="text-gray-400 text-sm">点击左侧技能卡片查看详情</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 新建技能弹窗 */}
      {showNewModal && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50" onClick={() => { if (!saving) setShowNewModal(false); }}>
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-2xl mx-4 max-h-[85vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <div className="sticky top-0 bg-white border-b border-gray-100 px-6 py-4 flex items-center justify-between rounded-t-2xl z-10">
              <h2 className="text-lg font-semibold text-gray-900">新建技能</h2>
              <button onClick={() => setShowNewModal(false)} className="w-8 h-8 flex items-center justify-center rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
              </button>
            </div>
            <div className="p-6 space-y-5">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">技能名称</label>
                  <input type="text" value={newForm.name} onChange={(e) => setNewForm({ ...newForm, name: e.target.value })}
                    className="w-full px-3.5 py-2.5 border border-gray-300 rounded-xl text-sm focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400 transition-all" placeholder="如：用户画像分析" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">技能类型</label>
                  <select value={newForm.type} onChange={(e) => setNewForm({ ...newForm, type: e.target.value })}
                    className="w-full px-3.5 py-2.5 border border-gray-300 rounded-xl text-sm focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400 transition-all">
                    {NEW_SKILL_TYPE_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>{opt.label}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1.5">描述</label>
                <textarea value={newForm.description} onChange={(e) => setNewForm({ ...newForm, description: e.target.value })}
                  rows={2} className="w-full px-3.5 py-2.5 border border-gray-300 rounded-xl text-sm focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400 transition-all" placeholder="技能描述" />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">最佳使用场景（每行一个）</label>
                  <textarea value={newForm.best_for} onChange={(e) => setNewForm({ ...newForm, best_for: e.target.value })}
                    rows={3} className="w-full px-3.5 py-2.5 border border-gray-300 rounded-xl text-sm focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400 transition-all" placeholder="产品前期调研&#10;用户需求分析" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">使用示例（每行一个）</label>
                  <textarea value={newForm.scenarios} onChange={(e) => setNewForm({ ...newForm, scenarios: e.target.value })}
                    rows={3} className="w-full px-3.5 py-2.5 border border-gray-300 rounded-xl text-sm focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400 transition-all" placeholder="分析电商平台用户行为&#10;优化注册流程" />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">预计时间</label>
                  <input type="text" value={newForm.estimated_time} onChange={(e) => setNewForm({ ...newForm, estimated_time: e.target.value })}
                    className="w-full px-3.5 py-2.5 border border-gray-300 rounded-xl text-sm focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400 transition-all" placeholder="如：30-60 分钟" />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1.5">执行步骤（每行一步）</label>
                <textarea value={newForm.steps} onChange={(e) => setNewForm({ ...newForm, steps: e.target.value })}
                  rows={4} className="w-full px-3.5 py-2.5 border border-gray-300 rounded-xl text-sm font-mono focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400 transition-all" placeholder="收集用户数据&#10;分析用户行为模式&#10;生成用户画像报告" />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1.5">System Prompt</label>
                <textarea value={newForm.system_prompt} onChange={(e) => setNewForm({ ...newForm, system_prompt: e.target.value })}
                  rows={6} className="w-full px-3.5 py-2.5 border border-gray-300 rounded-xl text-sm font-mono focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400 transition-all" placeholder="AI 助手的系统提示词..." />
              </div>
            </div>

            <div className="sticky bottom-0 bg-white border-t border-gray-100 px-6 py-4 flex justify-end gap-3 rounded-b-2xl">
              <button onClick={() => setShowNewModal(false)} className="px-5 py-2.5 text-sm font-medium text-gray-600 bg-gray-100 rounded-xl hover:bg-gray-200 transition-colors">取消</button>
              <button onClick={handleCreateSkill} disabled={saving}
                className="px-5 py-2.5 text-sm font-medium text-white bg-gradient-to-r from-blue-600 to-blue-700 rounded-xl hover:from-blue-700 hover:to-blue-800 disabled:opacity-50 transition-all shadow-sm">
                {saving ? "创建中..." : "创建"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 导入技能弹窗 */}
      {showImportModal && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50" onClick={() => { if (!importing) setShowImportModal(false); }}>
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-2xl mx-4 max-h-[85vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <div className="sticky top-0 bg-white border-b border-gray-100 px-6 py-4 flex items-center justify-between rounded-t-2xl z-10">
              <h2 className="text-lg font-semibold text-gray-900">导入技能</h2>
              <button onClick={() => setShowImportModal(false)} className="w-8 h-8 flex items-center justify-center rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
              </button>
            </div>

            <div className="p-6">
              <div className="flex gap-2 mb-5">
                <button
                  onClick={() => setImportTab("paste")}
                  className={`px-4 py-2 rounded-xl text-sm font-medium transition-all ${importTab === "paste" ? "bg-blue-600 text-white shadow-sm" : "bg-gray-100 text-gray-600 hover:bg-gray-200"}`}
                >粘贴内容</button>
                <button
                  onClick={() => setImportTab("upload")}
                  className={`px-4 py-2 rounded-xl text-sm font-medium transition-all ${importTab === "upload" ? "bg-blue-600 text-white shadow-sm" : "bg-gray-100 text-gray-600 hover:bg-gray-200"}`}
                >上传文件</button>
              </div>

              {importTab === "paste" ? (
                <div>
                  <p className="text-sm text-gray-500 mb-3">粘贴 SKILL.md 格式内容（含 YAML front matter）</p>
                  <textarea
                    value={importContent}
                    onChange={(e) => setImportContent(e.target.value)}
                    rows={15}
                    className="w-full px-3.5 py-3 border border-gray-300 rounded-xl text-sm font-mono focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400 transition-all"
                    placeholder="---&#10;name: 技能名称&#10;description: 技能描述&#10;type: component&#10;---&#10;&#10;技能内容..."
                  />
                </div>
              ) : (
                <div>
                  <p className="text-sm text-gray-500 mb-3">上传 .md 文件（SKILL.md 格式）</p>
                  <div className="border-2 border-dashed border-gray-300 rounded-xl p-10 text-center hover:border-blue-400 transition-colors">
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept=".md"
                      className="hidden"
                      onChange={(e) => setImportFile(e.target.files?.[0] || null)}
                    />
                    {importFile ? (
                      <div>
                        <div className="w-12 h-12 bg-blue-50 rounded-xl flex items-center justify-center mx-auto mb-3">
                          <svg className="w-6 h-6 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
                        </div>
                        <p className="text-sm font-medium text-gray-700 mb-1">{importFile.name}</p>
                        <p className="text-xs text-gray-400 mb-4">{(importFile.size / 1024).toFixed(1)} KB</p>
                        <button onClick={() => { setImportFile(null); if (fileInputRef.current) fileInputRef.current.value = ""; }}
                          className="text-xs text-red-500 hover:text-red-600 font-medium">重新选择</button>
                      </div>
                    ) : (
                      <div>
                        <div className="w-12 h-12 bg-gray-50 rounded-xl flex items-center justify-center mx-auto mb-3">
                          <svg className="w-6 h-6 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" /></svg>
                        </div>
                        <p className="text-gray-400 text-sm mb-3">拖拽文件到此处，或</p>
                        <button onClick={() => fileInputRef.current?.click()}
                          className="px-5 py-2.5 bg-gray-100 text-gray-700 rounded-xl text-sm font-medium hover:bg-gray-200 transition-colors">选择文件</button>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>

            <div className="sticky bottom-0 bg-white border-t border-gray-100 px-6 py-4 flex justify-end gap-3 rounded-b-2xl">
              <button onClick={() => setShowImportModal(false)} className="px-5 py-2.5 text-sm font-medium text-gray-600 bg-gray-100 rounded-xl hover:bg-gray-200 transition-colors">取消</button>
              {importTab === "paste" ? (
                <button onClick={handleImportPaste} disabled={importing}
                  className="px-5 py-2.5 text-sm font-medium text-white bg-gradient-to-r from-blue-600 to-blue-700 rounded-xl hover:from-blue-700 hover:to-blue-800 disabled:opacity-50 transition-all shadow-sm">
                  {importing ? "导入中..." : "导入"}
                </button>
              ) : (
                <button onClick={handleImportFile} disabled={importing || !importFile}
                  className="px-5 py-2.5 text-sm font-medium text-white bg-gradient-to-r from-blue-600 to-blue-700 rounded-xl hover:from-blue-700 hover:to-blue-800 disabled:opacity-50 transition-all shadow-sm">
                  {importing ? "导入中..." : "导入"}
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}