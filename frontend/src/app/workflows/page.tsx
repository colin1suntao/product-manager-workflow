"use client";

import { useEffect, useState, useCallback } from "react";
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

export default function WorkflowsPage() {
  const [runs, setRuns] = useState<WorkflowRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [filterStatus, setFilterStatus] = useState("");

  const fetchRuns = useCallback(async () => {
    try {
      const params = filterStatus ? { status: filterStatus } : undefined;
      const data = await workflowApi.list(params);
      setRuns(data.runs);
    } catch (err) {
      setError(err instanceof Error ? err.message : "加载失败");
    } finally {
      setLoading(false);
    }
  }, [filterStatus]);

  useEffect(() => {
    fetchRuns();
    const timer = setInterval(fetchRuns, 5000);
    return () => clearInterval(timer);
  }, [fetchRuns]);

  async function handlePause(runId: string) {
    try {
      await workflowApi.pause(runId);
      fetchRuns();
    } catch (err) {
      setError(err instanceof Error ? err.message : "操作失败");
    }
  }

  async function handleResume(runId: string) {
    try {
      await workflowApi.resume(runId);
      fetchRuns();
    } catch (err) {
      setError(err instanceof Error ? err.message : "操作失败");
    }
  }

  async function handleCancel(runId: string) {
    try {
      await workflowApi.cancel(runId);
      fetchRuns();
    } catch (err) {
      setError(err instanceof Error ? err.message : "操作失败");
    }
  }

  if (loading && runs.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-gray-500">加载中...</p>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">流程监控</h1>
        <div className="flex items-center gap-3">
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-lg text-sm"
          >
            <option value="">全部状态</option>
            {Object.entries(STATUS_LABELS).map(([key, label]) => (
              <option key={key} value={key}>
                {label}
              </option>
            ))}
          </select>
          <button
            onClick={fetchRuns}
            className="px-3 py-2 bg-gray-100 rounded-lg hover:bg-gray-200 text-sm"
          >
            刷新
          </button>
        </div>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 rounded-lg">
          {error}
        </div>
      )}

      {runs.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-lg border border-gray-200">
          <p className="text-gray-500">暂无工作流</p>
          <Link
            href="/requirements"
            className="mt-2 inline-block text-blue-600 hover:underline text-sm"
          >
            创建新工作流 →
          </Link>
        </div>
      ) : (
        <div className="space-y-3">
          {runs.map((run) => (
            <div
              key={run.id}
              className="p-4 bg-white rounded-lg border border-gray-200 hover:border-gray-300 transition-colors"
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-3">
                  <h3 className="font-medium">{run.title}</h3>
                  <span
                    className={`px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLORS[run.status]}`}
                  >
                    {STATUS_LABELS[run.status] || run.status}
                  </span>
                </div>
                <span className="text-xs text-gray-400">
                  {new Date(run.created_at).toLocaleString("zh-CN")}
                </span>
              </div>

              <div className="flex items-center gap-4 text-sm text-gray-500 mb-3">
                <span>
                  进度: {run.completed_steps}/{run.total_steps}
                </span>
                <span>ID: {run.id}</span>
              </div>

              {run.error && (
                <p className="text-sm text-red-600 mb-3">{run.error}</p>
              )}

              <div className="flex gap-2">
                <Link
                  href={`/workflows/${run.id}`}
                  className="px-3 py-1.5 bg-blue-50 text-blue-700 rounded-lg hover:bg-blue-100 text-xs font-medium"
                >
                  详情
                </Link>
                {run.status === "paused" && (
                  <button
                    onClick={() => handleResume(run.id)}
                    className="px-3 py-1.5 bg-green-50 text-green-700 rounded-lg hover:bg-green-100 text-xs font-medium"
                  >
                    恢复
                  </button>
                )}
                {(run.status === "pending" ||
                  run.status === "paused" ||
                  run.status === "analyzing" ||
                  run.status === "decomposing" ||
                  run.status === "generating_prototype" ||
                  run.status === "generating_docs" ||
                  run.status === "verifying" ||
                  run.status === "fixing") && (
                  <button
                    onClick={() => handlePause(run.id)}
                    className="px-3 py-1.5 bg-gray-50 text-gray-700 rounded-lg hover:bg-gray-100 text-xs font-medium"
                  >
                    暂停
                  </button>
                )}
                {(run.status === "pending" ||
                  run.status === "paused") && (
                  <button
                    onClick={() => handleCancel(run.id)}
                    className="px-3 py-1.5 bg-red-50 text-red-700 rounded-lg hover:bg-red-100 text-xs font-medium"
                  >
                    取消
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
