"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { workflowApi } from "@/lib/api";
import type { WorkflowRun } from "@/types/api";

export default function PrototypesPage() {
  const [runs, setRuns] = useState<WorkflowRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedRun, setSelectedRun] = useState<WorkflowRun | null>(null);

  useEffect(() => {
    async function fetchRuns() {
      try {
        const data = await workflowApi.list();
        const withPrototypes = data.workflows.filter(
          (r) => r.prototype_url && ["completed", "verifying", "fixing"].includes(r.status),
        );
        setRuns(withPrototypes);
        if (withPrototypes.length > 0) {
          setSelectedRun(withPrototypes[0]);
        }
      } catch {
        // ignore
      } finally {
        setLoading(false);
      }
    }
    fetchRuns();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-gray-500">加载中...</p>
      </div>
    );
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">原型预览</h1>

      {runs.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-lg border border-gray-200">
          <p className="text-gray-500">暂无可用的原型</p>
          <Link
            href="/requirements"
            className="mt-2 inline-block text-blue-600 hover:underline text-sm"
          >
            创建新工作流 →
          </Link>
        </div>
      ) : (
        <div className="flex gap-6 h-[calc(100vh-8rem)]">
          {/* 列表 */}
          <div className="w-64 bg-white rounded-lg border border-gray-200 p-3 overflow-auto">
            <h2 className="text-sm font-medium text-gray-700 mb-3">原型列表</h2>
            <ul className="space-y-2">
              {runs.map((run) => (
                <li key={run.id}>
                  <button
                    onClick={() => setSelectedRun(run)}
                    className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors ${
                      selectedRun?.id === run.id
                        ? "bg-blue-50 text-blue-700"
                        : "hover:bg-gray-50"
                    }`}
                  >
                    <div className="font-medium truncate">{run.title}</div>
                    <div className="text-xs text-gray-400 mt-0.5">
                      {new Date(run.updated_at).toLocaleDateString("zh-CN")}
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          </div>

          {/* 预览 */}
          <div className="flex-1 bg-white rounded-lg border border-gray-200 overflow-hidden">
            {selectedRun?.prototype_url ? (
              <iframe
                src={selectedRun.prototype_url}
                className="w-full h-full border-0"
                title={`原型 - ${selectedRun.title}`}
              />
            ) : selectedRun ? (
              <div className="flex items-center justify-center h-full">
                <p className="text-gray-500">原型生成中，请稍候...</p>
              </div>
            ) : (
              <div className="flex items-center justify-center h-full">
                <p className="text-gray-500">请选择一个原型</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
