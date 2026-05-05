"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { workflowApi } from "@/lib/api";
import type { WorkflowRun } from "@/types/api";

const STATUS_LABELS: Record<string, string> = {
  pending: "等待中",
  analyzing: "分析中",
  decomposing: "规则拆解中",
  generating_prototype: "生成原型中",
  generating_docs: "生成文档中",
  verifying: "校验中",
  fixing: "修复中",
  completed: "已完成",
  paused: "已暂停",
  error: "错误",
};

const STATUS_COLORS: Record<string, string> = {
  pending: "bg-gray-100 text-gray-700",
  analyzing: "bg-blue-100 text-blue-700",
  decomposing: "bg-blue-100 text-blue-700",
  generating_prototype: "bg-purple-100 text-purple-700",
  generating_docs: "bg-yellow-100 text-yellow-700",
  verifying: "bg-orange-100 text-orange-700",
  fixing: "bg-orange-100 text-orange-700",
  completed: "bg-green-100 text-green-700",
  paused: "bg-gray-200 text-gray-700",
  error: "bg-red-100 text-red-700",
};

const STEPS = [
  { key: "analyzing", label: "需求分析" },
  { key: "decomposing", label: "规则拆解" },
  { key: "generating_prototype", label: "生成原型" },
  { key: "generating_docs", label: "生成文档" },
  { key: "verifying", label: "校验" },
  { key: "fixing", label: "修复" },
  { key: "completed", label: "完成" },
];

export default function WorkflowDetailPage() {
  const params = useParams();
  const router = useRouter();
  const runId = params.id as string;
  const [run, setRun] = useState<WorkflowRun | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const fetchRun = useCallback(async () => {
    try {
      const data = await workflowApi.get(runId);
      setRun(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "加载失败");
    } finally {
      setLoading(false);
    }
  }, [runId]);

  useEffect(() => {
    fetchRun();
    const timer = setInterval(fetchRun, 3000);
    return () => clearInterval(timer);
  }, [fetchRun]);

  async function handlePause() {
    try {
      await workflowApi.pause(runId);
      fetchRun();
    } catch (err) {
      setError(err instanceof Error ? err.message : "操作失败");
    }
  }

  async function handleResume() {
    try {
      await workflowApi.resume(runId);
      fetchRun();
    } catch (err) {
      setError(err instanceof Error ? err.message : "操作失败");
    }
  }

  async function handleCancel() {
    try {
      await workflowApi.cancel(runId);
      fetchRun();
    } catch (err) {
      setError(err instanceof Error ? err.message : "操作失败");
    }
  }

  if (loading && !run) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-gray-500">加载中...</p>
      </div>
    );
  }

  if (!run) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500 mb-4">工作流不存在</p>
        <Link href="/workflows" className="text-blue-600 hover:underline">
          返回列表
        </Link>
      </div>
    );
  }

  const stepIndex = STEPS.findIndex((s) => s.key === run.status);

  return (
    <div className="max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <Link
            href="/workflows"
            className="text-sm text-gray-500 hover:text-gray-700 mb-1 inline-block"
          >
            ← 返回流程列表
          </Link>
          <h1 className="text-2xl font-bold">{run.title}</h1>
        </div>
        <div className="flex gap-2">
          {run.status === "paused" && (
            <button
              onClick={handleResume}
              className="px-3 py-2 bg-green-50 text-green-700 rounded-lg hover:bg-green-100 text-sm font-medium"
            >
              恢复
            </button>
          )}
          {(run.status === "pending" || run.status === "paused") && (
            <button
              onClick={handlePause}
              className="px-3 py-2 bg-gray-100 rounded-lg hover:bg-gray-200 text-sm font-medium"
            >
              暂停
            </button>
          )}
          {(run.status === "pending" || run.status === "paused") && (
            <button
              onClick={handleCancel}
              className="px-3 py-2 bg-red-50 text-red-700 rounded-lg hover:bg-red-100 text-sm font-medium"
            >
              取消
            </button>
          )}
        </div>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 rounded-lg">
          {error}
        </div>
      )}

      {/* 状态 */}
      <div className="bg-white rounded-lg border border-gray-200 p-6 mb-6">
        <div className="flex items-center gap-3 mb-4">
          <span
            className={`px-3 py-1 rounded-full text-sm font-medium ${STATUS_COLORS[run.status]}`}
          >
            {STATUS_LABELS[run.status]}
          </span>
          <span className="text-sm text-gray-500">ID: {run.id}</span>
        </div>

        {/* 进度条 */}
        <div className="flex items-center gap-2 mb-2">
          {STEPS.map((step, i) => (
            <div key={step.key} className="flex-1">
              <div className="flex items-center gap-2">
                <div
                  className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium ${
                    i < stepIndex
                      ? "bg-green-500 text-white"
                      : i === stepIndex
                        ? "bg-blue-500 text-white"
                        : "bg-gray-200 text-gray-500"
                  }`}
                >
                  {i < stepIndex ? "✓" : i + 1}
                </div>
                <span
                  className={`text-xs ${
                    i <= stepIndex ? "text-gray-700 font-medium" : "text-gray-400"
                  }`}
                >
                  {step.label}
                </span>
              </div>
              {i < STEPS.length - 1 && (
                <div
                  className={`h-0.5 w-full mt-2 ${
                    i < stepIndex ? "bg-green-500" : "bg-gray-200"
                  }`}
                />
              )}
            </div>
          ))}
        </div>

        <div className="text-sm text-gray-500 mt-4">
          进度: {run.completed_steps}/{run.total_steps}
        </div>
      </div>

      {/* 错误信息 */}
      {run.error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <h3 className="font-medium text-red-700 mb-1">错误信息</h3>
          <p className="text-sm text-red-600">{run.error}</p>
        </div>
      )}

      {/* 输出链接 */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h2 className="text-lg font-semibold mb-4">输出</h2>
        <div className="space-y-3">
          {run.prototype_url ? (
            <Link
              href={`/prototypes`}
              className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg hover:bg-gray-100"
            >
              <span className="text-2xl">🎨</span>
              <div>
                <div className="font-medium">原型预览</div>
                <div className="text-sm text-gray-500">查看生成的 HTML 原型</div>
              </div>
            </Link>
          ) : (
            <div className="p-3 bg-gray-50 rounded-lg text-gray-400">
              原型尚未生成
            </div>
          )}

          {run.document_url ? (
            <Link
              href={`/documents`}
              className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg hover:bg-gray-100"
            >
              <span className="text-2xl">📄</span>
              <div>
                <div className="font-medium">文档查看</div>
                <div className="text-sm text-gray-500">查看生成的 PRD 文档</div>
              </div>
            </Link>
          ) : (
            <div className="p-3 bg-gray-50 rounded-lg text-gray-400">
              文档尚未生成
            </div>
          )}

          {run.report_url ? (
            <Link
              href={`/reports`}
              className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg hover:bg-gray-100"
            >
              <span className="text-2xl">✅</span>
              <div>
                <div className="font-medium">校验报告</div>
                <div className="text-sm text-gray-500">查看验证报告</div>
              </div>
            </Link>
          ) : run.status === "completed" ? (
            <Link
              href={`/reports`}
              className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg hover:bg-gray-100"
            >
              <span className="text-2xl">✅</span>
              <div>
                <div className="font-medium">校验报告</div>
                <div className="text-sm text-gray-500">查看验证报告</div>
              </div>
            </Link>
          ) : (
            <div className="p-3 bg-gray-50 rounded-lg text-gray-400">
              校验尚未完成
            </div>
          )}
        </div>
      </div>

      {/* 时间信息 */}
      <div className="mt-6 text-sm text-gray-400">
        创建于: {new Date(run.created_at).toLocaleString("zh-CN")}
        <br />
        更新于: {new Date(run.updated_at).toLocaleString("zh-CN")}
      </div>
    </div>
  );
}
