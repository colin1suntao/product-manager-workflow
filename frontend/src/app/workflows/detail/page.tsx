"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
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

const STEPS = [
  { key: "parsing", label: "需求分析" },
  { key: "parsed", label: "需求已分析" },
  { key: "generating", label: "生成" },
  { key: "generated", label: "已生成" },
  { key: "verifying", label: "校验" },
  { key: "verified", label: "已校验" },
  { key: "completed", label: "完成" },
];

export default function WorkflowDetailPage() {
  return (
    <Suspense fallback={<div className="flex items-center justify-center h-64"><p className="text-gray-500">加载中...</p></div>}>
      <WorkflowDetailContent />
    </Suspense>
  );
}

function WorkflowDetailContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const runId = searchParams.get("id") || "";
  const [run, setRun] = useState<WorkflowRun | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const load = async () => {
      try {
        const data = await workflowApi.get(runId);
        setRun(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "加载失败");
      } finally {
        setLoading(false);
      }
    };
    load();
    const timer = setInterval(load, 3000);
    return () => clearInterval(timer);
  }, [runId]);

  const refetch = async () => {
    try {
      const data = await workflowApi.get(runId);
      setRun(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "操作失败");
    }
  };

  async function handlePause() {
    try {
      await workflowApi.pause(runId);
      refetch();
    } catch (err) {
      setError(err instanceof Error ? err.message : "操作失败");
    }
  }

  async function handleResume() {
    try {
      await workflowApi.resume(runId);
      refetch();
    } catch (err) {
      setError(err instanceof Error ? err.message : "操作失败");
    }
  }

  async function handleCancel() {
    try {
      await workflowApi.cancel(runId);
      refetch();
    } catch (err) {
      setError(err instanceof Error ? err.message : "操作失败");
    }
  }

  async function handleDelete() {
    if (!confirm("确定要删除此工作流吗？此操作不可恢复。")) return;
    try {
      await workflowApi.delete(runId);
      router.push("/workflows");
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

  const stepIndex = (() => {
    const idx = STEPS.findIndex((s) => s.key === run.status);
    return run.status === "init" ? 0 : idx;
  })();

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
          <h1 className="text-2xl font-bold">{run.title || run.requirement_text?.split("\n\n")[0]?.trim() || "init"}</h1>
        </div>
        <div className="flex gap-2">
          {run.status === "waiting_user_input" && (
            <button
              onClick={handleResume}
              className="px-3 py-2 bg-green-50 text-green-700 rounded-lg hover:bg-green-100 text-sm font-medium"
            >
              恢复
            </button>
          )}
          {(run.status === "init" || run.status === "waiting_user_input") && (
            <button
              onClick={handlePause}
              className="px-3 py-2 bg-gray-100 rounded-lg hover:bg-gray-200 text-sm font-medium"
            >
              暂停
            </button>
          )}
          {(run.status === "init" || run.status === "waiting_user_input") && (
            <button
              onClick={handleCancel}
              className="px-3 py-2 bg-red-50 text-red-700 rounded-lg hover:bg-red-100 text-sm font-medium"
            >
              停止
            </button>
          )}
          {(run.status === "completed" || run.status === "failed" || run.status === "cancelled") && (
            <button
              onClick={handleDelete}
              className="px-3 py-2 bg-red-50 text-red-700 rounded-lg hover:bg-red-100 text-sm font-medium"
            >
              删除
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

        {/* 已选技能 */}
        {run.selected_skills && run.selected_skills.length > 0 && (
          <div className="mt-4 pt-4 border-t border-gray-100">
            <h3 className="text-sm font-medium text-gray-600 mb-2">已选技能</h3>
            <div className="flex flex-wrap gap-1.5">
              {run.selected_skills.map((skill) => (
                <span
                  key={skill}
                  className="px-2 py-0.5 bg-blue-50 text-blue-700 rounded text-xs border border-blue-200"
                >
                  {skill}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* 错误信息 */}
      {run.error_message && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <h3 className="font-medium text-red-700 mb-1">错误信息</h3>
          <p className="text-sm text-red-600">{run.error_message}</p>
        </div>
      )}

      {/* 输出链接 */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h2 className="text-lg font-semibold mb-4">输出</h2>
        <div className="space-y-3">
          {run.prototype_url ? (
            <a
              href={run.prototype_url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg hover:bg-gray-100"
            >
              <span className="text-2xl">&#127912;</span>
              <div>
                <div className="font-medium">原型预览</div>
                <div className="text-sm text-gray-500">查看生成的 HTML 原型</div>
              </div>
            </a>
          ) : (
            <div className="p-3 bg-gray-50 rounded-lg text-gray-400">
              原型尚未生成
            </div>
          )}

          {run.prd_document_url ? (
            <Link
              href="/documents"
              className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg hover:bg-gray-100"
            >
              <span className="text-2xl">&#128196;</span>
              <div>
                <div className="font-medium">产品文档</div>
                <div className="text-sm text-gray-500">查看生成的 PRD 文档</div>
              </div>
            </Link>
          ) : (
            <div className="p-3 bg-gray-50 rounded-lg text-gray-400">
              文档尚未生成
            </div>
          )}

          {run.verification_report_url ? (
            <Link
              href="/reports"
              className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg hover:bg-gray-100"
            >
              <span className="text-2xl">&#9989;</span>
              <div>
                <div className="font-medium">校验报告</div>
                <div className="text-sm text-gray-500">查看校验报告详情</div>
              </div>
            </Link>
          ) : run.status === "completed" ? (
            <Link
              href="/reports"
              className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg hover:bg-gray-100"
            >
              <span className="text-2xl">&#9989;</span>
              <div>
                <div className="font-medium">校验报告</div>
                <div className="text-sm text-gray-500">查看校验报告详情</div>
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
