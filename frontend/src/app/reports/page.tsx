"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { workflowApi } from "@/lib/api";
import type { WorkflowRun } from "@/types/api";

interface ReportIssue {
  id: string;
  type: string;
  severity: "critical" | "major" | "minor" | "info";
  message: string;
  suggestion: string;
  location?: string;
}

interface VerificationReportData {
  report_id: string;
  created_at: string;
  prototype_issues: ReportIssue[];
  document_issues: ReportIssue[];
  consistency_issues: ReportIssue[];
  auto_fixed_issues: ReportIssue[];
  manual_review_required: ReportIssue[];
}

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

function IssueCard({ issue }: { issue: ReportIssue }) {
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
  const [report, setReport] = useState<VerificationReportData | null>(null);
  const [reportLoading, setReportLoading] = useState(false);

  useEffect(() => {
    async function fetchRuns() {
      try {
        const data = await workflowApi.list();
        // 筛选有校验报告的工作流
        const withReport = data.workflows.filter(
          (r) => r.verification_report_url && ["completed", "verified", "verifying"].includes(r.status),
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
    if (!run.verification_report_url) {
      setReport(null);
      return;
    }
    setReportLoading(true);
    try {
      // 直接通过 URL 获取报告
      const response = await fetch(run.verification_report_url);
      const text = await response.text();
      
      // 尝试解析 JSON，如果失败则创建一个默认报告
      try {
        const data = JSON.parse(text);
        // 确保数据包含必要的字段
        setReport({
          report_id: data.report_id || `report-${run.id}`,
          created_at: data.created_at || new Date().toISOString(),
          prototype_issues: Array.isArray(data.prototype_issues) ? data.prototype_issues : [],
          document_issues: Array.isArray(data.document_issues) ? data.document_issues : [],
          consistency_issues: Array.isArray(data.consistency_issues) ? data.consistency_issues : [],
          auto_fixed_issues: Array.isArray(data.auto_fixed_issues) ? data.auto_fixed_issues : [],
          manual_review_required: Array.isArray(data.manual_review_required) ? data.manual_review_required : [],
        });
      } catch {
        // JSON 解析失败，显示默认报告
        setReport({
          report_id: `report-${run.id}`,
          created_at: new Date().toISOString(),
          prototype_issues: [],
          document_issues: [],
          consistency_issues: [],
          auto_fixed_issues: [],
          manual_review_required: [{
            id: "MR001",
            type: "error",
            severity: "info",
            message: "报告格式异常，无法解析详细内容",
            suggestion: "请联系管理员或重新生成报告",
            location: "报告文件",
          }],
        });
      }
    } catch {
      setReport(null);
    } finally {
      setReportLoading(false);
    }
  }

  // 计算问题统计
  const getIssueStats = (report: VerificationReportData) => {
    const prototypeIssues = Array.isArray(report.prototype_issues) ? report.prototype_issues : [];
    const documentIssues = Array.isArray(report.document_issues) ? report.document_issues : [];
    const consistencyIssues = Array.isArray(report.consistency_issues) ? report.consistency_issues : [];
    
    const allIssues = [
      ...prototypeIssues,
      ...documentIssues,
      ...consistencyIssues,
    ];
    return {
      total: allIssues.length,
      critical: allIssues.filter((i) => i.severity === "critical").length,
      major: allIssues.filter((i) => i.severity === "major").length,
      minor: allIssues.filter((i) => i.severity === "minor").length,
      info: allIssues.filter((i) => i.severity === "info").length,
    };
  };

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
          <p className="text-gray-500">暂无可用的校验报告</p>
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
                    <div className="font-medium truncate">
                      {run.requirement_text?.slice(0, 30) || run.title || "未命名需求"}
                    </div>
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
                  <div className="grid grid-cols-5 gap-4">
                    <div className="text-center">
                      <div className="text-3xl font-bold text-gray-700">
                        {getIssueStats(report).total}
                      </div>
                      <div className="text-sm text-gray-500 mt-1">问题总数</div>
                    </div>
                    <div className="text-center">
                      <div className="text-3xl font-bold text-red-600">
                        {getIssueStats(report).critical}
                      </div>
                      <div className="text-sm text-gray-500 mt-1">严重问题</div>
                    </div>
                    <div className="text-center">
                      <div className="text-3xl font-bold text-orange-600">
                        {getIssueStats(report).major}
                      </div>
                      <div className="text-sm text-gray-500 mt-1">重要问题</div>
                    </div>
                    <div className="text-center">
                      <div className="text-3xl font-bold text-yellow-600">
                        {getIssueStats(report).minor}
                      </div>
                      <div className="text-sm text-gray-500 mt-1">次要问题</div>
                    </div>
                    <div className="text-center">
                      <div className="text-3xl font-bold text-blue-600">
                        {getIssueStats(report).info}
                      </div>
                      <div className="text-sm text-gray-500 mt-1">提示建议</div>
                    </div>
                  </div>
                  <div className="mt-4 pt-4 border-t border-gray-200">
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-500">报告ID: {report.report_id}</span>
                      <span className="text-sm text-gray-500">
                        生成时间: {new Date(report.created_at).toLocaleString("zh-CN")}
                      </span>
                    </div>
                  </div>
                </div>

                {/* 原型问题 */}
                {Array.isArray(report.prototype_issues) && report.prototype_issues.length > 0 && (
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
                {Array.isArray(report.document_issues) && report.document_issues.length > 0 && (
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
                {Array.isArray(report.consistency_issues) && report.consistency_issues.length > 0 && (
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

                {/* 人工审核建议 */}
                {Array.isArray(report.manual_review_required) && report.manual_review_required.length > 0 && (
                  <div>
                    <h3 className="text-md font-semibold mb-3">
                      审核建议 ({report.manual_review_required.length})
                    </h3>
                    <div className="space-y-3">
                      {report.manual_review_required.map((issue) => (
                        <IssueCard key={issue.id} issue={issue} />
                      ))}
                    </div>
                  </div>
                )}

                {getIssueStats(report).total === 0 && (
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
