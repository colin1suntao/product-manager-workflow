"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { workflowApi, reportApi } from "@/lib/api";
import type { WorkflowRun, VerificationReport, Issue } from "@/types/api";

const SEVERITY_COLORS: Record<string, string> = {
  critical: "bg-red-100 text-red-700",
  major: "bg-orange-100 text-orange-700",
  minor: "bg-yellow-100 text-yellow-700",
  info: "bg-blue-100 text-blue-700",
};

const SEVERITY_LABELS: Record<string, string> = {
  critical: "严重",
  major: "重要",
  minor: "次要",
  info: "提示",
};

function IssueCard({ issue }: { issue: Issue }) {
  return (
    <div className="p-4 bg-white rounded-lg border border-gray-200">
      <div className="flex items-center gap-2 mb-2">
        <span
          className={`px-2 py-0.5 rounded-full text-xs font-medium ${SEVERITY_COLORS[issue.severity]}`}
        >
          {SEVERITY_LABELS[issue.severity] || issue.severity}
        </span>
        <span className="text-sm text-gray-500">{issue.type}</span>
      </div>
      <p className="text-sm text-gray-700 mb-2">{issue.message}</p>
      {issue.suggestion && (
        <p className="text-xs text-gray-500">建议: {issue.suggestion}</p>
      )}
      {issue.location && (
        <p className="text-xs text-gray-400 mt-1">位置: {issue.location}</p>
      )}
    </div>
  );
}

export default function ReportsPage() {
  const [runs, setRuns] = useState<WorkflowRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedRun, setSelectedRun] = useState<WorkflowRun | null>(null);
  const [report, setReport] = useState<VerificationReport | null>(null);
  const [reportLoading, setReportLoading] = useState(false);

  useEffect(() => {
    async function fetchRuns() {
      try {
        const data = await workflowApi.list();
        const withReport = data.workflows.filter((r) =>
          ["completed", "verifying", "fixing"].includes(r.status),
        );
        setRuns(withReport);
      } catch {
        // ignore
      } finally {
        setLoading(false);
      }
    }
    fetchRuns();
  }, []);

  async function handleSelectRun(run: WorkflowRun) {
    setSelectedRun(run);
    setReportLoading(true);
    try {
      const r = await reportApi.get(run.id);
      setReport(r);
    } catch {
      setReport(null);
    } finally {
      setReportLoading(false);
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
      <h1 className="text-2xl font-bold mb-6">校验报告</h1>

      {runs.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-lg border border-gray-200">
          <p className="text-gray-500">暂无可用的报告</p>
          <Link
            href="/requirements"
            className="mt-2 inline-block text-blue-600 hover:underline text-sm"
          >
            创建新工作流 →
          </Link>
        </div>
      ) : (
        <div className="flex gap-6">
          <div className="w-64 bg-white rounded-lg border border-gray-200 p-3 h-[calc(100vh-8rem)] overflow-auto">
            <h2 className="text-sm font-medium text-gray-700 mb-3">工作流列表</h2>
            <ul className="space-y-2">
              {runs.map((run) => (
                <li key={run.id}>
                  <button
                    onClick={() => handleSelectRun(run)}
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

          <div className="flex-1 overflow-auto h-[calc(100vh-8rem)]">
            {reportLoading ? (
              <div className="flex items-center justify-center h-64">
                <p className="text-gray-500">加载报告中...</p>
              </div>
            ) : report ? (
              <div className="space-y-6">
                {/* 概览 */}
                <div className="bg-white rounded-lg border border-gray-200 p-6">
                  <h2 className="text-lg font-semibold mb-4">校验概览</h2>
                  <div className="grid grid-cols-3 gap-4">
                    <div className="text-center">
                      <div
                        className={`text-3xl font-bold ${
                          report.status === "pass"
                            ? "text-green-600"
                            : report.status === "fail"
                              ? "text-red-600"
                              : "text-yellow-600"
                        }`}
                      >
                        {report.overall_score}
                      </div>
                      <div className="text-sm text-gray-500 mt-1">综合评分</div>
                    </div>
                    <div className="text-center">
                      <div className="text-3xl font-bold text-gray-700">
                        {report.prototype_issues.length +
                          report.document_issues.length +
                          report.consistency_issues.length}
                      </div>
                      <div className="text-sm text-gray-500 mt-1">问题总数</div>
                    </div>
                    <div className="text-center">
                      <div
                        className={`px-3 py-1 rounded-full text-sm font-medium ${
                          report.status === "pass"
                            ? "bg-green-100 text-green-700"
                            : report.status === "fail"
                              ? "bg-red-100 text-red-700"
                              : "bg-yellow-100 text-yellow-700"
                        }`}
                      >
                        {report.status === "pass"
                          ? "通过"
                          : report.status === "fail"
                            ? "不通过"
                            : "警告"}
                      </div>
                      <div className="text-sm text-gray-500 mt-1">校验结果</div>
                    </div>
                  </div>
                </div>

                {/* 原型问题 */}
                {report.prototype_issues.length > 0 && (
                  <div>
                    <h3 className="text-md font-semibold mb-3">
                      原型问题 ({report.prototype_issues.length})
                    </h3>
                    <div className="space-y-3">
                      {report.prototype_issues.map((issue) => (
                        <IssueCard key={issue.id} issue={issue} />
                      ))}
                    </div>
                  </div>
                )}

                {/* 文档问题 */}
                {report.document_issues.length > 0 && (
                  <div>
                    <h3 className="text-md font-semibold mb-3">
                      文档问题 ({report.document_issues.length})
                    </h3>
                    <div className="space-y-3">
                      {report.document_issues.map((issue) => (
                        <IssueCard key={issue.id} issue={issue} />
                      ))}
                    </div>
                  </div>
                )}

                {/* 一致性问题 */}
                {report.consistency_issues.length > 0 && (
                  <div>
                    <h3 className="text-md font-semibold mb-3">
                      一致性问题 ({report.consistency_issues.length})
                    </h3>
                    <div className="space-y-3">
                      {report.consistency_issues.map((issue) => (
                        <IssueCard key={issue.id} issue={issue} />
                      ))}
                    </div>
                  </div>
                )}

                {report.prototype_issues.length === 0 &&
                  report.document_issues.length === 0 &&
                  report.consistency_issues.length === 0 && (
                    <div className="text-center py-8 bg-green-50 rounded-lg">
                      <p className="text-green-700 font-medium">
                        所有校验通过，未发现问题
                      </p>
                    </div>
                  )}
              </div>
            ) : selectedRun ? (
              <div className="flex items-center justify-center h-64">
                <p className="text-gray-500">该工作流暂无校验报告</p>
              </div>
            ) : (
              <div className="flex items-center justify-center h-64">
                <p className="text-gray-500">请选择一个工作流</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
