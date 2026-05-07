"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { workflowApi } from "@/lib/api";

export default function RequirementsPage() {
  const router = useRouter();
  const [title, setTitle] = useState("");
  const [requirements, setRequirements] = useState("");
  const [targetAudience, setTargetAudience] = useState("");
  const [constraints, setConstraints] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");

    if (!title.trim() || !requirements.trim()) {
      setError("标题和需求描述为必填项");
      setLoading(false);
      return;
    }

    try {
      const requirementText = [
        title.trim(),
        requirements.trim(),
        targetAudience.trim() ? `目标用户：${targetAudience.trim()}` : "",
        constraints.trim() ? `约束条件：${constraints.trim()}` : "",
      ]
        .filter(Boolean)
        .join("\n\n");

      const run = await workflowApi.create({
        requirement_text: requirementText,
      });
      router.push(`/workflows/${run.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "创建失败");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">需求输入</h1>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 rounded-lg">
          {error}
        </div>
      )}

      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label
              htmlFor="title"
              className="block text-sm font-medium text-gray-700 mb-1.5"
            >
              标题 <span className="text-red-500">*</span>
            </label>
            <input
              id="title"
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="例如：电商平台用户注册流程"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
            />
          </div>

          <div>
            <label
              htmlFor="requirements"
              className="block text-sm font-medium text-gray-700 mb-1.5"
            >
              需求描述 <span className="text-red-500">*</span>
            </label>
            <textarea
              id="requirements"
              value={requirements}
              onChange={(e) => setRequirements(e.target.value)}
              placeholder="请详细描述您的需求，包括功能、交互、业务规则等..."
              rows={6}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm resize-y"
            />
          </div>

          <div>
            <label
              htmlFor="targetAudience"
              className="block text-sm font-medium text-gray-700 mb-1.5"
            >
              目标用户
            </label>
            <input
              id="targetAudience"
              type="text"
              value={targetAudience}
              onChange={(e) => setTargetAudience(e.target.value)}
              placeholder="例如：25-40岁的电商消费者"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
            />
          </div>

          <div>
            <label
              htmlFor="constraints"
              className="block text-sm font-medium text-gray-700 mb-1.5"
            >
              约束条件
            </label>
            <textarea
              id="constraints"
              value={constraints}
              onChange={(e) => setConstraints(e.target.value)}
              placeholder="例如：必须支持移动端、需要符合 WCAG 2.1 无障碍标准..."
              rows={3}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm resize-y"
            />
          </div>

          <div className="flex gap-3 pt-2">
            <button
              type="submit"
              disabled={loading}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-sm font-medium"
            >
              {loading ? "创建中..." : "启动工作流"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
