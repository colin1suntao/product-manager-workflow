"use client";

import { useEffect, useState, useCallback } from "react";
import { componentApi } from "@/lib/api";
import type { Component } from "@/types/api";

const CATEGORY_OPTIONS = [
  "按钮",
  "表单",
  "导航",
  "布局",
  "数据展示",
  "反馈",
  "弹窗",
  "其他",
];

export default function ComponentsLibPage() {
  const [components, setComponents] = useState<Component[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [filterCategory, setFilterCategory] = useState("");

  // Form state
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState("");
  const [tags, setTags] = useState("");
  const [htmlPreview, setHtmlPreview] = useState("");
  const [usageExample, setUsageExample] = useState("");

  const fetchComponents = useCallback(async () => {
    try {
      const params = filterCategory ? { category: filterCategory } : undefined;
      const data = await componentApi.list(params);
      setComponents(data.components);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, [filterCategory]);

  useEffect(() => {
    fetchComponents();
  }, [fetchComponents]);

  function resetForm() {
    setName("");
    setDescription("");
    setCategory("");
    setTags("");
    setHtmlPreview("");
    setUsageExample("");
    setShowForm(false);
    setEditingId(null);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name || !category || !htmlPreview) return;

    try {
      if (editingId) {
        await componentApi.update(editingId, {
          name,
          description,
          category,
          tags: tags
            .split(",")
            .map((t) => t.trim())
            .filter(Boolean),
          html_preview: htmlPreview,
          usage_example: usageExample || undefined,
        });
      } else {
        await componentApi.create({
          name,
          description,
          category,
          tags: tags
            .split(",")
            .map((t) => t.trim())
            .filter(Boolean),
          html_preview: htmlPreview,
          usage_example: usageExample || undefined,
        });
      }
      resetForm();
      fetchComponents();
    } catch {
      // ignore
    }
  }

  function handleEdit(comp: Component) {
    setName(comp.name);
    setDescription(comp.description);
    setCategory(comp.category);
    setTags(comp.tags.join(", "));
    setHtmlPreview(comp.html_preview);
    setUsageExample(comp.usage_example || "");
    setEditingId(comp.id);
    setShowForm(true);
  }

  async function handleDelete(id: string) {
    if (!confirm("确定要删除这个组件吗？")) return;
    try {
      await componentApi.delete(id);
      fetchComponents();
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
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">组件库管理</h1>
        <div className="flex items-center gap-3">
          <select
            value={filterCategory}
            onChange={(e) => setFilterCategory(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-lg text-sm"
          >
            <option value="">全部分类</option>
            {CATEGORY_OPTIONS.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
          <button
            onClick={() => {
              resetForm();
              setShowForm(true);
            }}
            className="px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm"
          >
            新增组件
          </button>
        </div>
      </div>

      {/* 表单 */}
      {showForm && (
        <div className="mb-6 p-4 bg-white rounded-lg border border-gray-200">
          <h2 className="text-lg font-semibold mb-4">
            {editingId ? "编辑组件" : "新增组件"}
          </h2>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  名称 <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  分类 <span className="text-red-500">*</span>
                </label>
                <select
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                  required
                >
                  <option value="">请选择</option>
                  {CATEGORY_OPTIONS.map((c) => (
                    <option key={c} value={c}>
                      {c}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                描述
              </label>
              <input
                type="text"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                标签（逗号分隔）
              </label>
              <input
                type="text"
                value={tags}
                onChange={(e) => setTags(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                HTML 预览 <span className="text-red-500">*</span>
              </label>
              <textarea
                value={htmlPreview}
                onChange={(e) => setHtmlPreview(e.target.value)}
                rows={4}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm font-mono resize-y"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                使用示例
              </label>
              <textarea
                value={usageExample}
                onChange={(e) => setUsageExample(e.target.value)}
                rows={3}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm font-mono resize-y"
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
                onClick={resetForm}
                className="px-4 py-2 bg-gray-100 rounded-lg hover:bg-gray-200 text-sm"
              >
                取消
              </button>
            </div>
          </form>
        </div>
      )}

      {/* 列表 */}
      {components.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-lg border border-gray-200">
          <p className="text-gray-500">暂无组件</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {components.map((comp) => (
            <div
              key={comp.id}
              className="bg-white rounded-lg border border-gray-200 p-4"
            >
              <div className="flex items-start justify-between mb-2">
                <div>
                  <h3 className="font-medium">{comp.name}</h3>
                  <span className="inline-block mt-1 px-2 py-0.5 bg-gray-100 text-gray-600 rounded text-xs">
                    {comp.category}
                  </span>
                </div>
                <span
                  className={`px-2 py-0.5 rounded-full text-xs ${
                    comp.status === "active"
                      ? "bg-green-100 text-green-700"
                      : comp.status === "draft"
                        ? "bg-yellow-100 text-yellow-700"
                        : "bg-gray-100 text-gray-600"
                  }`}
                >
                  {comp.status === "active" ? "已启用" : comp.status === "draft" ? "草稿" : "已归档"}
                </span>
              </div>
              {comp.description && (
                <p className="text-sm text-gray-500 mb-3">{comp.description}</p>
              )}
              {comp.tags.length > 0 && (
                <div className="flex flex-wrap gap-1 mb-3">
                  {comp.tags.map((tag) => (
                    <span
                      key={tag}
                      className="px-1.5 py-0.5 bg-blue-50 text-blue-600 rounded text-xs"
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              )}
              <div className="flex gap-2">
                <button
                  onClick={() => handleEdit(comp)}
                  className="px-2 py-1 bg-gray-50 rounded text-xs hover:bg-gray-100"
                >
                  编辑
                </button>
                <button
                  onClick={() => handleDelete(comp.id)}
                  className="px-2 py-1 bg-red-50 text-red-600 rounded text-xs hover:bg-red-100"
                >
                  删除
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
