"use client";

import { useState, useEffect } from "react";
import { channelsApi } from "@/lib/api";

interface Channel {
  id: string;
  name: string;
  channel_type: string;
  status: string;
  config: Record<string, string>;
  webhook_url: string;
  message_count: number;
  last_error: string | null;
  created_at: string;
  updated_at: string;
}

const TYPE_LABELS: Record<string, { label: string; color: string; icon: string }> = {
  feishu: { label: "飞书", color: "bg-blue-100 text-blue-700", icon: "M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z" },
  wechat: { label: "微信", color: "bg-green-100 text-green-700", icon: "M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z" },
};

const STATUS_LABELS: Record<string, { label: string; color: string }> = {
  active: { label: "已激活", color: "bg-green-100 text-green-700" },
  inactive: { label: "未激活", color: "bg-gray-100 text-gray-600" },
  error: { label: "异常", color: "bg-red-100 text-red-700" },
};

const FEISHU_FIELDS = [
  { key: "app_id", label: "App ID", placeholder: "cli_xxxxxxxxxxxx", required: true },
  { key: "app_secret", label: "App Secret", placeholder: "应用密钥", required: true, secret: true },
  { key: "verification_token", label: "Verification Token", placeholder: "事件订阅验证令牌", required: true },
  { key: "encrypt_key", label: "Encrypt Key", placeholder: "加密密钥（可选）" },
];

const WECHAT_FIELDS = [
  { key: "corp_id", label: "企业 ID", placeholder: "wwxxxxxxxxxxxxxx", required: true },
  { key: "agent_id", label: "应用 AgentId", placeholder: "1000002", required: true },
  { key: "secret", label: "应用 Secret", placeholder: "应用密钥", required: true, secret: true },
  { key: "token", label: "回调 Token", placeholder: "回调配置 Token", required: true },
  { key: "encoding_aes_key", label: "EncodingAESKey", placeholder: "消息加密密钥（可选）" },
];

function ConfigForm({ channelType, config, onChange }: {
  channelType: string;
  config: Record<string, string>;
  onChange: (key: string, value: string) => void;
}) {
  const fields = channelType === "feishu" ? FEISHU_FIELDS : WECHAT_FIELDS;
  return (
    <div className="space-y-3">
      {fields.map((f) => (
        <div key={f.key}>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            {f.label} {f.required && <span className="text-red-500">*</span>}
          </label>
          <input
            type={f.secret ? "password" : "text"}
            value={config[f.key] || ""}
            onChange={(e) => onChange(f.key, e.target.value)}
            placeholder={f.placeholder}
            className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
        </div>
      ))}
    </div>
  );
}

export default function ChannelsPage() {
  const [channels, setChannels] = useState<Channel[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [editId, setEditId] = useState<string | null>(null);
  const [testing, setTesting] = useState<string | null>(null);
  const [testResults, setTestResults] = useState<Record<string, { valid: boolean; message: string }>>({});

  // Form state
  const [formName, setFormName] = useState("");
  const [formType, setFormType] = useState("feishu");
  const [formConfig, setFormConfig] = useState<Record<string, string>>({});

  useEffect(() => {
    loadChannels();
  }, []);

  const loadChannels = async () => {
    try {
      setLoading(true);
      const data = await channelsApi.list();
      setChannels(data.channels);
    } catch {
      setError("加载渠道列表失败");
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setFormName("");
    setFormType("feishu");
    setFormConfig({});
    setShowCreate(false);
    setEditId(null);
  };

  const handleCreate = async () => {
    if (!formName.trim()) {
      setError("请输入渠道名称");
      return;
    }
    try {
      setError(null);
      await channelsApi.create({
        name: formName.trim(),
        channel_type: formType,
        config: formConfig,
      });
      resetForm();
      loadChannels();
    } catch (e) {
      setError("创建渠道失败");
    }
  };

  const handleUpdate = async () => {
    if (!editId) return;
    try {
      setError(null);
      await channelsApi.update(editId, {
        name: formName.trim(),
        config: formConfig,
      });
      resetForm();
      loadChannels();
    } catch {
      setError("更新渠道失败");
    }
  };

  const handleTest = async (id: string) => {
    setTesting(id);
    try {
      const result = await channelsApi.test(id);
      setTestResults((prev) => ({ ...prev, [id]: { valid: result.valid, message: result.message } }));
    } catch {
      setTestResults((prev) => ({ ...prev, [id]: { valid: false, message: "测试请求失败" } }));
    } finally {
      setTesting(null);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("确定要删除此渠道吗？")) return;
    try {
      await channelsApi.delete(id);
      loadChannels();
    } catch {}
  };

  const startEdit = (ch: Channel) => {
    setEditId(ch.id);
    setFormName(ch.name);
    setFormType(ch.channel_type);
    setFormConfig(ch.config || {});
    setShowCreate(true);
  };

  const copyWebhook = (url: string) => {
    const full = `${window.location.origin}${url}`;
    navigator.clipboard.writeText(full).then(() => {
      alert("Webhook URL 已复制到剪贴板");
    });
  };

  return (
    <div className="max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">渠道接入</h1>
          <p className="text-sm text-gray-500 mt-1">配置飞书、微信等渠道，对接 AI 会话功能</p>
        </div>
        <button
          onClick={() => { resetForm(); setShowCreate(true); }}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-medium"
        >
          + 添加渠道
        </button>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="text-red-500 hover:text-red-700 font-medium">关闭</button>
        </div>
      )}

      {/* Create / Edit modal */}
      {showCreate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
          <div className="bg-white rounded-lg shadow-xl p-6 max-w-lg w-full mx-4 max-h-[90vh] overflow-y-auto">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              {editId ? "编辑渠道" : "添加渠道"}
            </h3>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  渠道名称 <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={formName}
                  onChange={(e) => setFormName(e.target.value)}
                  placeholder="如：产品团队飞书群"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              {!editId && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    渠道类型 <span className="text-red-500">*</span>
                  </label>
                  <div className="flex gap-3">
                    {Object.entries(TYPE_LABELS).map(([key, { label }]) => (
                      <button
                        key={key}
                        onClick={() => { setFormType(key); setFormConfig({}); }}
                        className={`flex-1 px-4 py-3 rounded-lg border-2 text-sm font-medium transition-colors ${
                          formType === key
                            ? "border-blue-500 bg-blue-50 text-blue-700"
                            : "border-gray-200 text-gray-600 hover:border-gray-300"
                        }`}
                      >
                        {label}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  {TYPE_LABELS[formType]?.label || formType} 配置
                </label>
                <ConfigForm
                  channelType={formType}
                  config={formConfig}
                  onChange={(k, v) => setFormConfig((prev) => ({ ...prev, [k]: v }))}
                />
              </div>
            </div>

            <div className="flex justify-end gap-2 mt-6">
              <button
                onClick={resetForm}
                className="px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-100 text-sm"
              >
                取消
              </button>
              <button
                onClick={editId ? handleUpdate : handleCreate}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm font-medium"
              >
                {editId ? "保存" : "创建"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Channel list */}
      {loading ? (
        <div className="flex items-center justify-center py-20">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
        </div>
      ) : channels.length === 0 ? (
        <div className="text-center py-16">
          <div className="w-16 h-16 mx-auto mb-4 bg-gray-100 rounded-full flex items-center justify-center">
            <svg className="w-8 h-8 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.288 15.038a5.25 5.25 0 017.424 0M5.106 11.856c3.807-3.808 9.98-3.808 13.788 0M1.924 8.674c5.565-5.565 14.587-5.565 20.152 0M12.53 18.22l-.53.53-.53-.53a.75.75 0 011.06 0z" />
            </svg>
          </div>
          <h3 className="text-lg font-medium text-gray-900 mb-2">暂无渠道</h3>
          <p className="text-gray-500 text-sm mb-4">添加飞书或微信渠道，让外部用户通过机器人与 AI 会话</p>
          <button
            onClick={() => { resetForm(); setShowCreate(true); }}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-medium"
          >
            添加渠道
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          {channels.map((ch) => {
            const typeInfo = TYPE_LABELS[ch.channel_type] || { label: ch.channel_type, color: "bg-gray-100 text-gray-600" };
            const statusInfo = STATUS_LABELS[ch.status] || STATUS_LABELS.inactive;
            const testResult = testResults[ch.id];

            return (
              <div key={ch.id} className="bg-white rounded-lg border p-5">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${typeInfo.color}`}>
                      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.288 15.038a5.25 5.25 0 017.424 0M5.106 11.856c3.807-3.808 9.98-3.808 13.788 0M1.924 8.674c5.565-5.565 14.587-5.565 20.152 0M12.53 18.22l-.53.53-.53-.53a.75.75 0 011.06 0z" />
                      </svg>
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <h3 className="text-base font-semibold text-gray-900">{ch.name}</h3>
                        <span className={`px-2 py-0.5 rounded text-xs font-medium ${typeInfo.color}`}>
                          {typeInfo.label}
                        </span>
                        <span className={`px-2 py-0.5 rounded text-xs font-medium ${statusInfo.color}`}>
                          {statusInfo.label}
                        </span>
                      </div>
                      <div className="flex items-center gap-4 mt-1 text-xs text-gray-500">
                        <span>{ch.message_count} 条消息</span>
                        <span>创建于 {new Date(ch.created_at).toLocaleDateString("zh-CN")}</span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleTest(ch.id)}
                      disabled={testing === ch.id}
                      className="px-3 py-1.5 border border-gray-300 rounded-md hover:bg-gray-50 text-xs font-medium disabled:opacity-50"
                    >
                      {testing === ch.id ? "测试中..." : "测试连接"}
                    </button>
                    <button
                      onClick={() => startEdit(ch)}
                      className="px-3 py-1.5 border border-gray-300 rounded-md hover:bg-gray-50 text-xs font-medium"
                    >
                      编辑
                    </button>
                    <button
                      onClick={() => handleDelete(ch.id)}
                      className="px-3 py-1.5 border border-red-300 rounded-md hover:bg-red-50 text-xs font-medium text-red-600"
                    >
                      删除
                    </button>
                  </div>
                </div>

                {/* Test result */}
                {testResult && (
                  <div className={`mt-3 p-2 rounded text-xs ${
                    testResult.valid ? "bg-green-50 text-green-700 border border-green-200" : "bg-red-50 text-red-700 border border-red-200"
                  }`}>
                    {testResult.message}
                  </div>
                )}

                {/* Error */}
                {ch.last_error && (
                  <div className="mt-2 p-2 bg-red-50 border border-red-200 rounded text-xs text-red-600">
                    错误: {ch.last_error}
                  </div>
                )}

                {/* Webhook URL */}
                <div className="mt-3 pt-3 border-t border-gray-100">
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-gray-500 font-medium">Webhook URL:</span>
                    <code className="flex-1 px-2 py-1 bg-gray-50 rounded text-xs text-gray-700 font-mono truncate">
                      {ch.webhook_url}
                    </code>
                    <button
                      onClick={() => copyWebhook(ch.webhook_url)}
                      className="px-2 py-1 border border-gray-300 rounded text-xs hover:bg-gray-50"
                      title="复制完整 URL"
                    >
                      复制
                    </button>
                  </div>
                  <p className="mt-1 text-[11px] text-gray-400">
                    将此 URL 配置到 {typeInfo.label} 机器人的事件回调地址中
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Help section */}
      <div className="mt-8 bg-blue-50 border border-blue-200 rounded-lg p-5">
        <h3 className="text-sm font-semibold text-blue-900 mb-3">接入指南</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <h4 className="text-xs font-semibold text-blue-800 mb-2">飞书接入步骤</h4>
            <ol className="text-xs text-blue-700 space-y-1 list-decimal list-inside">
              <li>在飞书开放平台创建自建应用</li>
              <li>获取 App ID、App Secret、Verification Token</li>
              <li>配置事件回调地址（Webhook URL）</li>
              <li>订阅 im.message.receive_v1 事件</li>
              <li>发布应用并审批通过</li>
            </ol>
            <div className="mt-2 p-2 bg-white rounded text-xs text-blue-600">
              注意：应用需发布后且用户已添加机器人到群聊才能接收消息
            </div>
          </div>
          <div>
            <h4 className="text-xs font-semibold text-blue-800 mb-2">企业微信接入步骤</h4>
            <ol className="text-xs text-blue-700 space-y-1 list-decimal list-inside">
              <li>在企业微信管理后台创建自建应用</li>
              <li>获取企业 ID、AgentId 和 Secret</li>
              <li>配置接收消息服务器，填写上方 Webhook URL</li>
              <li>设置 Token 和 EncodingAESKey</li>
              <li>确保应用可见范围包含目标用户</li>
            </ol>
          </div>
        </div>
      </div>
    </div>
  );
}
