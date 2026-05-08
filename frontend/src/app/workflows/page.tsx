"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { workflowApi } from "@/lib/api";
import type { WorkflowRun } from "@/types/api";

const STATUS_LABELS: Record<string, string> = {
  init: "等待中",
  parsing: "需求分析中",
  parsed: "需求已分析",
  generating: "生成中",
  generated: "已生成",
  verifying: "校验中",
  verified: "已校验",
  completed: "已完成",
  failed: "失败",
  waiting_user_input: "等待输入",
  cancelled: "已停止",
};

const STATUS_COLORS: Record<string, string> = {
  init: "bg-gray-100 text-gray-700",
  parsing: "bg-blue-100 text-blue-700",
  parsed: "bg-blue-100 text-blue-700",
  generating: "bg-purple-100 text-purple-700",
  generated: "bg-yellow-100 text-yellow-700",
  verifying: "bg-orange-100 text-orange-700",
  verified: "bg-green-100 text-green-700",
  completed: "bg-green-100 text-green-700",
  failed: "bg-red-100 text-red-700",
  waiting_user_input: "bg-gray-200 text-gray-700",
  cancelled: "bg-red-100 text-red-700",
};

export default function WorkflowsPage() {
  const router = useRouter();
  const [runs, setRuns] = useState<WorkflowRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [filterStatus, setFilterStatus] = useState("");

  function getRunTitle(run: WorkflowRun): string {
    if (run.title) return run.title;
    if (run.requirement_text) {
      return run.requirement_text.split("\n\n")[0].trim();
    }
    return "init";
  }

  useEffect(() => {
    const load = async () => {
      try {
        const data = await workflowApi.list(filterStatus ? { status: filterStatus } : undefined);
        setRuns(data.workflows);
      } catch (err) {
        const msg = err instanceof Error ? err.message : "";
        if (msg.includes("401") || msg.includes("认证") || msg.includes("未提供")) {
          router.push("/auth/login");
          return;
        }
        setError(msg || "加载失败");
      } finally {
        setLoading(false);
      }
    };
    load();
    const timer = setInterval(load, 5000);
    return () => clearInterval(timer);
  }, [filterStatus, router]);

  const refetch = async () => {
    try {
      const data = await workflowApi.list(filterStatus ? { status: filterStatus } : undefined);
      setRuns(data.workflows);
    } catch (err) {
      setError(err instanceof Error ? err.message : "操作失败");
    }
  };

  async function handlePause(runId: string) {
    try {
      await workflowApi.pause(runId);
      refetch();
    } catch (err) {
      setError(err instanceof Error ? err.message : "操作失败");
    }
  }

  async function handleResume(runId: string) {
    try {
      await workflowApi.resume(runId);
      refetch();
    } catch (err) {
      setError(err instanceof Error ? err.message : "操作失败");
    }
  }

  async function handleCancel(runId: string) {
    try {
      await workflowApi.cancel(runId);
      refetch();
    } catch (err) {
      setError(err instanceof Error ? err.message : "操作失败");
    }
  }

  async function handleDelete(runId: string) {
    if (!confirm("确定要删除此工作流吗？此操作不可恢复。")) return;
    try {
      await workflowApi.delete(runId);
      refetch();
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
        <h1 className="text-2xl font-bold">工作流管理</h1>
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
            onClick={refetch}
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
                  <h3 className="font-medium">{getRunTitle(run)}</h3>
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

              {run.error_message && (
                <p className="text-sm text-red-600 mb-3">{run.error_message}</p>
              )}

              <div className="flex gap-2">
                <Link
                  href={`/workflows/detail/?id=${run.id}`}
                  className="px-3 py-1.5 bg-blue-50 text-blue-700 rounded-lg hover:bg-blue-100 text-xs font-medium"
                >
                  详情
                </Link>
                {run.status === "waiting_user_input" && (
                  <button
                    onClick={() => handleResume(run.id)}
                    className="px-3 py-1.5 bg-green-50 text-green-700 rounded-lg hover:bg-green-100 text-xs font-medium"
                  >
                    恢复
                  </button>
                )}
                {(run.status === "init" ||
                  run.status === "waiting_user_input" ||
                  run.status === "parsing" ||
                  run.status === "parsed" ||
                  run.status === "generating" ||
                  run.status === "generated" ||
                  run.status === "verifying") && (
                  <button
                    onClick={() => handlePause(run.id)}
                    className="px-3 py-1.5 bg-gray-50 text-gray-700 rounded-lg hover:bg-gray-100 text-xs font-medium"
                  >
                    暂停
                  </button>
                )}
                {(run.status === "init" ||
                  run.status === "waiting_user_input") && (
                  <button
                    onClick={() => handleCancel(run.id)}
                    className="px-3 py-1.5 bg-red-50 text-red-700 rounded-lg hover:bg-red-100 text-xs font-medium"
                  >
                    停止
                  </button>
                )}
                {(run.status === "completed" ||
                  run.status === "failed" ||
                  run.status === "cancelled") && (
                  <button
                    onClick={() => handleDelete(run.id)}
                    className="px-3 py-1.5 bg-red-50 text-red-700 rounded-lg hover:bg-red-100 text-xs font-medium"
                  >
                    删除
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
