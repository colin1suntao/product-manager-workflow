"use client";

import { useState, useEffect } from "react";
import { knowledgeBaseApi } from "@/lib/api";

interface Template {
  id: string;
  name: string;
  description: string;
  type: string;
  type_label: string;
  tags: string[];
  content_preview: string;
  created_at: string;
  updated_at: string;
}

export default function KnowledgeBasePage() {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [formData, setFormData] = useState({ name: "", description: "", content: "", tags: "" });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [detailId, setDetailId] = useState<string | null>(null);
  const [detailData, setDetailData] = useState<any>(null);

  useEffect(() => {
    loadTemplates();
  }, []);

  const loadTemplates = async () => {
    setLoading(true);
    try {
      const data = await knowledgeBaseApi.listTemplates("document");
      setTemplates(data.templates);
    } catch (err) {
      console.error("Failed to load templates:", err);
    } finally {
      setLoading(false);
    }
  };

  const openCreate = () => {
    setEditingId(null);
    setFormData({ name: "", description: "", content: "", tags: "" });
    setError("");
    setShowForm(true);
  };

  const openEdit = async (id: string) => {
    setError("");
    try {
      const data = await knowledgeBaseApi.getTemplate(id);
      setEditingId(id);
      setFormData({
        name: data.name,
        description: data.description,
        content: data.content,
        tags: data.tags.join(", "),
      });
      setShowForm(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "加载失败");
    }
  };

  const handleSave = async () => {
    if (!formData.name.trim()) {
      setError("模板名称不能为空");
      return;
    }
    setSaving(true);
    setError("");
    try {
      const tags = formData.tags.split(",").map((t) => t.trim()).filter(Boolean);
      if (editingId) {
        await knowledgeBaseApi.updateTemplate(editingId, {
          name: formData.name,
          description: formData.description,
          content: formData.content,
          tags,
        });
      } else {
        await knowledgeBaseApi.createTemplate({
          name: formData.name,
          description: formData.description,
          type: "document",
          content: formData.content,
          tags,
        });
      }
      setShowForm(false);
      loadTemplates();
    } catch (err) {
      setError(err instanceof Error ? err.message : "保存失败");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: string, name: string) => {
    if (!confirm(`确定删除文档模板「${name}」吗？`)) return;
    try {
      await knowledgeBaseApi.deleteTemplate(id);
      loadTemplates();
    } catch (err) {
      setError(err instanceof Error ? err.message : "删除失败");
    }
  };

  const viewDetail = async (id: string) => {
    try {
      const data = await knowledgeBaseApi.getTemplate(id);
      setDetailData(data);
      setDetailId(id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "加载失败");
    }
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">知识库</h1>
        <button
          onClick={openCreate}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-medium"
        >
          + 新建文档模板
        </button>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 rounded-lg text-sm">{error}</div>
      )}

      {loading ? (
        <div className="text-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-2 text-gray-500 text-sm">加载中...</p>
        </div>
      ) : templates.length === 0 ? (
        <div className="text-center py-12 bg-gray-50 rounded-lg border border-gray-200">
          <p className="text-gray-500">暂无文档模板，点击上方按钮新建</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {templates.map((t) => (
            <div key={t.id} className="bg-white rounded-lg border border-gray-200 p-4 hover:shadow-sm transition-shadow">
              <div className="flex items-start justify-between mb-2">
                <div>
                  <h3 className="font-medium text-gray-900">{t.name}</h3>
                  <span className="inline-block mt-1 text-xs px-2 py-0.5 rounded-full bg-green-100 text-green-700">
                    {t.type_label}
                  </span>
                </div>
              </div>
              <p className="text-sm text-gray-500 mt-2 line-clamp-2">{t.description}</p>
              {t.tags.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1">
                  {t.tags.map((tag, i) => (
                    <span key={i} className="px-1.5 py-0.5 bg-gray-100 text-gray-600 rounded text-xs">{tag}</span>
                  ))}
                </div>
              )}
              <p className="text-xs text-gray-400 mt-2 line-clamp-2 font-mono">{t.content_preview}</p>
              <div className="mt-3 flex gap-2">
                <button onClick={() => viewDetail(t.id)} className="text-xs text-blue-600 hover:text-blue-700">查看</button>
                <button onClick={() => openEdit(t.id)} className="text-xs text-gray-600 hover:text-gray-700">编辑</button>
                <button onClick={() => handleDelete(t.id, t.name)} className="text-xs text-red-600 hover:text-red-700">删除</button>
              </div>
            </div>
          ))}
        </div>
      )}

      {showForm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => { if (!saving) setShowForm(false); }}>
          <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl mx-4 max-h-[85vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <div className="p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold">{editingId ? "编辑文档模板" : "新建文档模板"}</h2>
                <button onClick={() => setShowForm(false)} className="text-gray-400 hover:text-gray-600 text-xl leading-none">x</button>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">模板名称</label>
                  <input type="text" value={formData.name} onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" placeholder="模板名称" />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">描述</label>
                  <textarea value={formData.description} onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                    rows={2} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" placeholder="模板描述" />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">标签（逗号分隔）</label>
                  <input type="text" value={formData.tags} onChange={(e) => setFormData({ ...formData, tags: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" placeholder="标签1, 标签2" />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">模板内容</label>
                  <textarea value={formData.content} onChange={(e) => setFormData({ ...formData, content: e.target.value })}
                    rows={10} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm font-mono" placeholder="模板内容（Markdown 格式）" />
                </div>
              </div>

              <div className="mt-6 flex justify-end gap-3">
                <button onClick={() => setShowForm(false)} className="px-4 py-2 text-sm text-gray-600 bg-gray-100 rounded-lg hover:bg-gray-200">取消</button>
                <button onClick={handleSave} disabled={saving}
                  className="px-4 py-2 text-sm text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50">
                  {saving ? "保存中..." : "保存"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {detailId && detailData && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setDetailId(null)}>
          <div className="bg-white rounded-xl shadow-xl w-full max-w-3xl mx-4 max-h-[80vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <div className="p-6">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h2 className="text-lg font-semibold">{detailData.name}</h2>
                  <span className="inline-block mt-1 text-xs px-2 py-0.5 rounded-full bg-green-100 text-green-700">{detailData.type_label}</span>
                </div>
                <button onClick={() => setDetailId(null)} className="text-gray-400 hover:text-gray-600 text-xl leading-none">x</button>
              </div>
              <p className="text-sm text-gray-600 mb-4">{detailData.description}</p>
              {detailData.tags?.length > 0 && (
                <div className="mb-4 flex flex-wrap gap-1">
                  {detailData.tags.map((tag: string, i: number) => (
                    <span key={i} className="px-2 py-0.5 bg-gray-100 text-gray-600 rounded text-xs">{tag}</span>
                  ))}
                </div>
              )}
              <div className="border-t border-gray-200 pt-4">
                <h3 className="text-sm font-medium text-gray-700 mb-2">模板内容</h3>
                <pre className="text-sm text-gray-600 whitespace-pre-wrap font-mono bg-gray-50 p-4 rounded-lg max-h-96 overflow-y-auto">{detailData.content}</pre>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}