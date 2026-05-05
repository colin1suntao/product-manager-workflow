"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { workflowApi } from "@/lib/api";
import type { WorkflowRun } from "@/types/api";

export default function DocumentsPage() {
  const [runs, setRuns] = useState<WorkflowRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedRun, setSelectedRun] = useState<WorkflowRun | null>(null);
  const [docContent, setDocContent] = useState("");

  useEffect(() => {
    async function fetchRuns() {
      try {
        const data = await workflowApi.list();
        const withDocs = data.runs.filter(
          (r) => r.document_url && ["completed", "verifying", "fixing"].includes(r.status),
        );
        setRuns(withDocs);
        if (withDocs.length > 0) {
          setSelectedRun(withDocs[0]);
        }
      } catch {
        // ignore
      } finally {
        setLoading(false);
      }
    }
    fetchRuns();
  }, []);

  useEffect(() => {
    async function fetchDoc() {
      if (!selectedRun?.document_url) {
        setDocContent("");
        return;
      }
      try {
        const response = await fetch(selectedRun.document_url);
        const text = await response.text();
        setDocContent(text);
      } catch {
        setDocContent("文档加载失败");
      }
    }
    fetchDoc();
  }, [selectedRun?.document_url]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-gray-500">加载中...</p>
      </div>
    );
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">文档查看</h1>

      {runs.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-lg border border-gray-200">
          <p className="text-gray-500">暂无可用的文档</p>
          <Link
            href="/requirements"
            className="mt-2 inline-block text-blue-600 hover:underline text-sm"
          >
            创建新工作流 →
          </Link>
        </div>
      ) : (
        <div className="flex gap-6 h-[calc(100vh-8rem)]">
          <div className="w-64 bg-white rounded-lg border border-gray-200 p-3 overflow-auto">
            <h2 className="text-sm font-medium text-gray-700 mb-3">文档列表</h2>
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

          <div className="flex-1 bg-white rounded-lg border border-gray-200 overflow-auto p-6">
            {docContent ? (
              <div className="prose prose-sm max-w-none">
                <pre className="whitespace-pre-wrap font-mono text-sm text-gray-700">
                  {docContent}
                </pre>
              </div>
            ) : selectedRun ? (
              <div className="flex items-center justify-center h-full">
                <p className="text-gray-500">文档生成中，请稍候...</p>
              </div>
            ) : (
              <div className="flex items-center justify-center h-full">
                <p className="text-gray-500">请选择一个文档</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
