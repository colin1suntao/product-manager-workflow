"use client";

import { useState, useEffect, FormEvent } from "react";
import { useRouter } from "next/navigation";
import { llmApi, LLMProvider, LLMProviderCreate, LLMTestResult } from "@/lib/llm";
import { isAuthenticated } from "@/lib/auth";

const PROVIDER_PRESETS: { type: "openai" | "anthropic" | "custom"; name: string; model: string; url?: string }[] = [
  { type: "custom", name: "", model: "", url: "" },
  { type: "openai", name: "OpenAI", model: "gpt-4o" },
  { type: "anthropic", name: "Anthropic Claude", model: "claude-3-5-sonnet-20241022" },
  { type: "custom", name: "DeepSeek", model: "deepseek-chat", url: "https://api.deepseek.com/v1" },
  { type: "custom", name: "通义千问", model: "qwen-turbo", url: "https://dashscope.aliyuncs.com/compatible-mode/v1" },
  { type: "custom", name: "Kimi", model: "moonshot-v1-8k", url: "https://api.moonshot.cn/v1" },
  { type: "custom", name: "GLM 智谱", model: "glm-4", url: "https://open.bigmodel.cn/api/paas/v4" },
  { type: "custom", name: "MiniMax", model: "abab6.5-chat", url: "https://api.minimax.chat/v1" },
];

export default function LLMSettingsPage() {
  const router = useRouter();
  const [providers, setProviders] = useState<LLMProvider[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<LLMTestResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [testingConn, setTestingConn] = useState(false);
  const [fetchingModels, setFetchingModels] = useState(false);
  const [availableModels, setAvailableModels] = useState<{ id: string }[]>([]);
  const [authError, setAuthError] = useState<string | null>(null);
  const [form, setForm] = useState<LLMProviderCreate>({
    name: "",
    provider_type: "openai",
    api_key: "",
    base_url: "",
    default_model: "",
  });

  useEffect(() => {
    if (!isAuthenticated()) {
      router.push("/auth/login");
      return;
    }
    let ignore = false;
    const load = async () => {
      try {
        const data = await llmApi.list();
        if (!ignore) setProviders(data.providers);
      } catch (e) {
        const msg = e instanceof Error ? e.message : "";
        if (msg.includes("401") || msg.includes("认证")) {
          router.push("/auth/login");
        } else {
          console.error("Failed to load providers", e);
        }
      }
    };
    load();
    return () => { ignore = true; };
  }, [router]);

  const loadProviders = async () => {
    try {
      const data = await llmApi.list();
      setProviders(data.providers);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "";
      if (msg.includes("401") || msg.includes("认证")) {
        router.push("/auth/login");
      } else {
        console.error("Failed to load providers", e);
      }
    }
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      if (editingId) {
        await llmApi.update(editingId, form);
      } else {
        await llmApi.create(form);
      }
      setShowForm(false);
      setEditingId(null);
      setForm({ name: "", provider_type: "openai", api_key: "", base_url: "", default_model: "" });
      await loadProviders();
    } catch (e) {
      const msg = e instanceof Error ? e.message : "";
      if (msg.includes("401") || msg.includes("认证")) {
        router.push("/auth/login");
      } else {
        console.error("Failed to save provider", e);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("确定删除此 LLM Provider？")) return;
    try {
      await llmApi.delete(id);
      await loadProviders();
    } catch (e) {
      const msg = e instanceof Error ? e.message : "";
      if (msg.includes("401") || msg.includes("认证")) {
        router.push("/auth/login");
      } else {
        console.error("Failed to delete provider", e);
      }
    }
  };

  const handleTest = async (id: string) => {
    setTestResult(null);
    try {
      const result = await llmApi.test(id);
      setTestResult(result);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "测试失败";
      if (msg.includes("401") || msg.includes("认证")) {
        router.push("/auth/login");
      } else {
        setTestResult({ success: false, response_time_ms: 0, model: "", message: msg });
      }
    }
  };

  const handleSetDefault = async (id: string) => {
    try {
      await llmApi.setDefault(id);
      await loadProviders();
    } catch (e) {
      const msg = e instanceof Error ? e.message : "";
      if (msg.includes("401") || msg.includes("认证")) {
        router.push("/auth/login");
      } else {
        console.error("Failed to set default", e);
      }
    }
  };

  const applyPreset = (preset: typeof PROVIDER_PRESETS[0]) => {
    setForm({
      name: preset.name || "",
      provider_type: preset.type,
      api_key: "",
      base_url: preset.url || "",
      default_model: preset.model || "",
    });
    setAvailableModels([]);
  };

  const handleQuickTest = async () => {
    if (!form.api_key) {
      alert("请先填写 API Key");
      return;
    }
    setTestingConn(true);
    setTestResult(null);
    try {
      const result = await llmApi.quickTest({
        provider_type: form.provider_type,
        api_key: form.api_key,
        base_url: form.base_url || undefined,
        default_model: form.default_model || undefined,
      });
      setTestResult(result);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "测试失败";
      if (msg.includes("401") || msg.includes("认证")) {
        setAuthError("登录已过期，请重新登录");
        router.push("/auth/login");
      } else {
        setTestResult({ success: false, response_time_ms: 0, model: "", message: msg });
      }
    } finally {
      setTestingConn(false);
    }
  };

  const handleFetchModels = async () => {
    if (!form.api_key) {
      alert("请先填写 API Key");
      return;
    }
    setFetchingModels(true);
    try {
      const data = await llmApi.listModels({
        provider_type: form.provider_type,
        api_key: form.api_key,
        base_url: form.base_url || undefined,
      });
      setAvailableModels(data.models);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "获取模型列表失败";
      if (msg.includes("401") || msg.includes("认证")) {
        setAuthError("登录已过期，请重新登录");
        router.push("/auth/login");
      } else {
        alert(msg);
      }
    } finally {
      setFetchingModels(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-4xl mx-auto">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-2xl font-bold text-gray-900">LLM Provider 配置</h1>
          <button
            onClick={() => { setShowForm(true); setEditingId(null); setForm({ name: "", provider_type: "openai", api_key: "", base_url: "", default_model: "" }); }}
            className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700"
          >
            添加 Provider
          </button>
        </div>

        {authError && (
          <div className="mb-6 p-4 rounded-lg bg-yellow-50 border border-yellow-200">
            <p className="text-yellow-800 font-medium">{authError}</p>
            <button
              onClick={() => router.push("/auth/login")}
              className="mt-2 text-sm text-yellow-700 underline hover:text-yellow-900"
            >
              前往登录
            </button>
          </div>
        )}

        {showForm && (
          <div className="bg-white rounded-lg shadow p-6 mb-6">
            <h2 className="text-lg font-semibold mb-4">{editingId ? "编辑 Provider" : "添加 Provider"}</h2>

            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">快速选择预设配置</label>
              <div className="flex flex-wrap gap-2">
                {PROVIDER_PRESETS.map((preset, idx) => {
                  const label = idx === 0 ? "第三方自定义" : preset.name;
                  return (
                    <button
                      key={idx}
                      type="button"
                      onClick={() => applyPreset(preset)}
                      className={`px-3 py-1 text-sm border rounded-full hover:bg-gray-100 ${
                        idx === 0
                          ? "border-blue-300 bg-blue-50 text-blue-700 font-medium"
                          : "border-gray-300"
                      }`}
                    >
                      {idx === 0 && "+ "}
                      {label}
                    </button>
                  );
                })}
              </div>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">名称</label>
                <input
                  type="text"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  required
                  className="w-full px-4 py-2 border border-gray-300 rounded-md"
                  placeholder="例如：OpenAI"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">类型</label>
                <select
                  value={form.provider_type}
                  onChange={(e) => setForm({ ...form, provider_type: e.target.value as "openai" | "anthropic" | "custom" })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-md"
                >
                  <option value="openai">OpenAI</option>
                  <option value="anthropic">Anthropic Claude</option>
                  <option value="custom">自定义 (OpenAI 兼容)</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">API Key</label>
                <input
                  type="password"
                  value={form.api_key}
                  onChange={(e) => setForm({ ...form, api_key: e.target.value })}
                  required
                  className="w-full px-4 py-2 border border-gray-300 rounded-md"
                  placeholder="sk-..."
                />
              </div>

              {(form.provider_type === "custom" || form.base_url) && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Base URL</label>
                  <input
                    type="text"
                    value={form.base_url || ""}
                    onChange={(e) => setForm({ ...form, base_url: e.target.value })}
                    className="w-full px-4 py-2 border border-gray-300 rounded-md"
                    placeholder="https://api.example.com/v1"
                  />
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">默认模型</label>
                <div className="flex gap-2">
                  <select
                    value={form.default_model}
                    onChange={(e) => setForm({ ...form, default_model: e.target.value })}
                    className="flex-1 px-4 py-2 border border-gray-300 rounded-md"
                  >
                    <option value="">选择模型...</option>
                    {availableModels.map((m) => (
                      <option key={m.id} value={m.id}>{m.id}</option>
                    ))}
                  </select>
                  <button
                    type="button"
                    onClick={handleFetchModels}
                    disabled={fetchingModels || !form.api_key}
                    className="px-4 py-2 text-sm border border-gray-300 rounded-md hover:bg-gray-100 disabled:opacity-50 whitespace-nowrap"
                  >
                    {fetchingModels ? "获取中..." : "获取模型列表"}
                  </button>
                </div>
                <input
                  type="text"
                  value={form.default_model}
                  onChange={(e) => setForm({ ...form, default_model: e.target.value })}
                  className="w-full mt-2 px-4 py-2 border border-gray-300 rounded-md"
                  placeholder="或手动输入模型名称，如 gpt-4o"
                />
              </div>

              <div className="flex gap-2 pt-2">
                <button
                  type="button"
                  onClick={handleQuickTest}
                  disabled={testingConn || !form.api_key}
                  className="px-4 py-2 text-sm border border-green-300 text-green-700 rounded-md hover:bg-green-50 disabled:opacity-50"
                >
                  {testingConn ? "测试中..." : "测试连接"}
                </button>
              </div>

              <div className="flex gap-2">
                <button type="submit" disabled={loading} className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 disabled:opacity-50">
                  {loading ? "保存中..." : "保存"}
                </button>
                <button type="button" onClick={() => setShowForm(false)} className="px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-100">
                  取消
                </button>
              </div>
            </form>
          </div>
        )}

        {testResult && (
          <div className={`mb-6 p-4 rounded-lg ${testResult.success ? "bg-green-50 border border-green-200" : "bg-red-50 border border-red-200"}`}>
            <p className={`font-medium ${testResult.success ? "text-green-800" : "text-red-800"}`}>
              {testResult.message}
            </p>
            {testResult.success && (
              <p className="text-sm text-green-600 mt-1">模型: {testResult.model} | 响应时间: {testResult.response_time_ms}ms</p>
            )}
          </div>
        )}

        <div className="space-y-4">
          {providers.map((p) => (
            <div key={p.id} className="bg-white rounded-lg shadow p-4">
              <div className="flex justify-between items-start">
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-lg font-semibold">{p.name}</h3>
                    {p.is_default && <span className="bg-blue-100 text-blue-800 text-xs px-2 py-1 rounded-full">默认</span>}
                    {!p.is_active && <span className="bg-gray-100 text-gray-800 text-xs px-2 py-1 rounded-full">已禁用</span>}
                  </div>
                  <p className="text-sm text-gray-500 mt-1">
                    {p.provider_type} · {p.default_model} · {p.api_key}
                  </p>
                  {p.base_url && <p className="text-xs text-gray-400">{p.base_url}</p>}
                </div>
                <div className="flex gap-2">
                  <button onClick={() => handleTest(p.id)} className="px-3 py-1 text-sm border border-gray-300 rounded-md hover:bg-gray-100">
                    测试
                  </button>
                  {!p.is_default && (
                    <button onClick={() => handleSetDefault(p.id)} className="px-3 py-1 text-sm border border-gray-300 rounded-md hover:bg-gray-100">
                      设为默认
                    </button>
                  )}
                  <button onClick={() => handleDelete(p.id)} className="px-3 py-1 text-sm text-red-600 border border-red-300 rounded-md hover:bg-red-50">
                    删除
                  </button>
                </div>
              </div>
            </div>
          ))}

          {providers.length === 0 && (
            <div className="text-center py-12 text-gray-500">
              暂无 LLM Provider 配置，点击「添加 Provider」开始配置
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
