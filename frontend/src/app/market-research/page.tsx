"use client";

import { useState, useEffect } from "react";
import { marketResearchApi } from "@/lib/api";
import { getAccessToken } from "@/lib/auth";

interface SkillRecommendation {
  name: string;
  description: string;
  relevance_score: number;
  category: string;
}

interface ResearchReport {
  id: string;
  title: string;
  status: string;
  selected_skills: string[];
  created_at: string;
  completed_at: string | null;
}

interface ResearchTemplate {
  id: string;
  name: string;
  description: string;
  skill_names: string[];
  created_at: string;
}

const CATEGORY_LABELS: Record<string, string> = {
  macro: "宏观环境",
  market: "市场规模",
  customer: "用户研究",
  competitor: "竞争分析",
  strategy: "产品策略",
  other: "其他",
};

const CATEGORY_COLORS: Record<string, string> = {
  macro: "bg-blue-100 text-blue-700 border-blue-300",
  market: "bg-green-100 text-green-700 border-green-300",
  customer: "bg-purple-100 text-purple-700 border-purple-300",
  competitor: "bg-orange-100 text-orange-700 border-orange-300",
  strategy: "bg-pink-100 text-pink-700 border-pink-300",
  other: "bg-gray-100 text-gray-700 border-gray-300",
};

export default function MarketResearchPage() {
  const [activeTab, setActiveTab] = useState<"create" | "history" | "templates">("create");
  const [title, setTitle] = useState("");
  const [requirementText, setRequirementText] = useState("");
  const [selectedSkills, setSelectedSkills] = useState<string[]>([]);
  const [recommendations, setRecommendations] = useState<SkillRecommendation[]>([]);
  const [reports, setReports] = useState<ResearchReport[]>([]);
  const [templates, setTemplates] = useState<ResearchTemplate[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [selectedReport, setSelectedReport] = useState<string | null>(null);
  const [reportContent, setReportContent] = useState("");
  const [reportStatus, setReportStatus] = useState<string | null>(null);

  // 模板保存相关
  const [showSaveTemplate, setShowSaveTemplate] = useState(false);
  const [templateName, setTemplateName] = useState("");
  const [templateDesc, setTemplateDesc] = useState("");

  useEffect(() => {
    loadReports();
    loadTemplates();
  }, []);

  const loadReports = async () => {
    try {
      const data = await marketResearchApi.list();
      setReports(data.reports);
    } catch (error) {
      console.error("Failed to load reports:", error);
    }
  };

  const loadTemplates = async () => {
    try {
      const data = await marketResearchApi.listTemplates();
      setTemplates(data.templates);
    } catch (error) {
      console.error("Failed to load templates:", error);
    }
  };

  const handleRecommendSkills = async () => {
    if (!requirementText.trim()) {
      setError("请输入调研需求描述");
      return;
    }

    setLoading(true);
    setError("");

    try {
      const data = await marketResearchApi.recommendSkills(requirementText);
      setRecommendations(data.recommendations);
      // 自动选中推荐的技能
      setSelectedSkills(data.recommendations.map((r) => r.name));
    } catch (error) {
      setError("获取技能推荐失败");
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateResearch = async () => {
    if (!requirementText.trim()) {
      setError("请输入调研需求描述");
      return;
    }

    if (selectedSkills.length === 0) {
      setError("请选择至少一个 PM Skills");
      return;
    }

    setLoading(true);
    setError("");
    setSuccess("");

    try {
      const data = await marketResearchApi.create({
        title: title || undefined,
        requirement_text: requirementText,
        selected_skills: selectedSkills,
      });

      setSuccess(`调研任务已创建，报告 ID: ${data.report_id}`);
      setSelectedReport(data.report_id);
      setReportStatus("pending");

      // 开始轮询状态
      pollReportStatus(data.report_id);

      // 刷新报告列表
      loadReports();
    } catch (error) {
      setError("创建调研任务失败");
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const pollReportStatus = async (reportId: string) => {
    const maxAttempts = 60; // 最多轮询 60 次（约 2 分钟）
    let attempts = 0;

    const poll = async () => {
      if (attempts >= maxAttempts) {
        setReportStatus("timeout");
        return;
      }

      try {
        const status = await marketResearchApi.getStatus(reportId);
        setReportStatus(status.status);

        if (status.status === "completed") {
          // 加载报告内容
          const report = await marketResearchApi.get(reportId);
          setReportContent(report.report_content);
          loadReports();
          return;
        }

        if (status.status === "failed") {
          setError(`报告生成失败: ${status.error_message}`);
          return;
        }

        // 继续轮询
        attempts++;
        setTimeout(poll, 2000);
      } catch (error) {
        console.error("Failed to poll status:", error);
        attempts++;
        setTimeout(poll, 2000);
      }
    };

    poll();
  };

  const handleViewReport = async (reportId: string) => {
    setSelectedReport(reportId);
    setLoading(true);

    try {
      const report = await marketResearchApi.get(reportId);
      setReportContent(report.report_content);
      setReportStatus(report.status);
    } catch (error) {
      setError("加载报告失败");
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const handleSaveTemplate = async () => {
    if (!templateName.trim()) {
      setError("请输入模板名称");
      return;
    }

    if (selectedSkills.length === 0) {
      setError("请选择至少一个技能");
      return;
    }

    try {
      await marketResearchApi.saveTemplate({
        name: templateName,
        description: templateDesc,
        skill_names: selectedSkills,
      });

      setSuccess("模板保存成功");
      setShowSaveTemplate(false);
      setTemplateName("");
      setTemplateDesc("");
      loadTemplates();
    } catch (error) {
      setError("保存模板失败");
      console.error(error);
    }
  };

  const handleUseTemplate = (template: ResearchTemplate) => {
    setSelectedSkills(template.skill_names);
    setActiveTab("create");
    setSuccess(`已加载模板: ${template.name}`);
  };

  const handleDeleteTemplate = async (templateId: string) => {
    try {
      await marketResearchApi.deleteTemplate(templateId);
      loadTemplates();
    } catch (error) {
      setError("删除模板失败");
      console.error(error);
    }
  };

  const toggleSkill = (skillName: string) => {
    setSelectedSkills((prev) =>
      prev.includes(skillName)
        ? prev.filter((name) => name !== skillName)
        : [...prev, skillName]
    );
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 py-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-8">市场调研</h1>

        {/* 选项卡 */}
        <div className="flex space-x-4 mb-6">
          <button
            onClick={() => setActiveTab("create")}
            className={`px-4 py-2 rounded-lg ${
              activeTab === "create"
                ? "bg-blue-600 text-white"
                : "bg-white text-gray-700 hover:bg-gray-100"
            }`}
          >
            创建调研
          </button>
          <button
            onClick={() => setActiveTab("history")}
            className={`px-4 py-2 rounded-lg ${
              activeTab === "history"
                ? "bg-blue-600 text-white"
                : "bg-white text-gray-700 hover:bg-gray-100"
            }`}
          >
            历史报告 ({reports.length})
          </button>
          <button
            onClick={() => setActiveTab("templates")}
            className={`px-4 py-2 rounded-lg ${
              activeTab === "templates"
                ? "bg-blue-600 text-white"
                : "bg-white text-gray-700 hover:bg-gray-100"
            }`}
          >
            调研模板 ({templates.length})
          </button>
        </div>

        {/* 错误/成功提示 */}
        {error && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
            {error}
          </div>
        )}
        {success && (
          <div className="mb-4 p-4 bg-green-50 border border-green-200 rounded-lg text-green-700">
            {success}
          </div>
        )}

        {/* 创建调研页面 */}
        {activeTab === "create" && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* 左侧：输入表单 */}
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-xl font-semibold mb-4">调研需求</h2>

              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  调研标题（可选）
                </label>
                <input
                  type="text"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="例如：智能家居市场调研"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>

              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  调研需求描述 *
                </label>
                <textarea
                  value={requirementText}
                  onChange={(e) => setRequirementText(e.target.value)}
                  placeholder="请描述您的调研需求，例如：&#10;- 分析中国智能家居市场的规模和增长趋势&#10;- 研究目标用户群体的特征和需求&#10;- 评估主要竞争对手的市场策略"
                  rows={6}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>

              <button
                onClick={handleRecommendSkills}
                disabled={loading || !requirementText.trim()}
                className="w-full px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? "分析中..." : "智能推荐技能"}
              </button>
            </div>

            {/* 右侧：技能选择 */}
            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-xl font-semibold">选择 PM Skills</h2>
                {selectedSkills.length > 0 && (
                  <button
                    onClick={() => setShowSaveTemplate(true)}
                    className="px-3 py-1 text-sm bg-purple-600 text-white rounded hover:bg-purple-700"
                  >
                    保存为模板
                  </button>
                )}
              </div>

              {recommendations.length > 0 ? (
                <div className="space-y-3">
                  {recommendations.map((rec) => (
                    <div
                      key={rec.name}
                      onClick={() => toggleSkill(rec.name)}
                      className={`p-3 border rounded-lg cursor-pointer transition-all ${
                        selectedSkills.includes(rec.name)
                          ? "border-blue-500 bg-blue-50"
                          : "border-gray-200 hover:border-gray-300"
                      }`}
                    >
                      <div className="flex justify-between items-start">
                        <div>
                          <div className="font-medium text-gray-900">{rec.name}</div>
                          <div className="text-sm text-gray-600 mt-1">{rec.description}</div>
                        </div>
                        <div className="flex items-center space-x-2">
                          <span
                            className={`px-2 py-1 text-xs rounded ${
                              CATEGORY_COLORS[rec.category] || CATEGORY_COLORS.other
                            }`}
                          >
                            {CATEGORY_LABELS[rec.category] || rec.category}
                          </span>
                          <div
                            className={`w-5 h-5 rounded border-2 flex items-center justify-center ${
                              selectedSkills.includes(rec.name)
                                ? "bg-blue-600 border-blue-600"
                                : "border-gray-300"
                            }`}
                          >
                            {selectedSkills.includes(rec.name) && (
                              <svg
                                className="w-3 h-3 text-white"
                                fill="none"
                                viewBox="0 0 24 24"
                                stroke="currentColor"
                              >
                                <path
                                  strokeLinecap="round"
                                  strokeLinejoin="round"
                                  strokeWidth={2}
                                  d="M5 13l4 4L19 7"
                                />
                              </svg>
                            )}
                          </div>
                        </div>
                      </div>
                      <div className="text-xs text-gray-400 mt-2">
                        相关度: {Math.round(rec.relevance_score * 100)}%
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center text-gray-500 py-8">
                  请输入调研需求并点击「智能推荐技能」
                </div>
              )}

              {selectedSkills.length > 0 && (
                <div className="mt-4 pt-4 border-t">
                  <div className="text-sm text-gray-600 mb-2">
                    已选择 {selectedSkills.length} 个技能
                  </div>
                  <button
                    onClick={handleCreateResearch}
                    disabled={loading}
                    className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
                  >
                    {loading ? "创建中..." : "开始生成调研报告"}
                  </button>
                </div>
              )}
            </div>

            {/* 报告预览 */}
            {selectedReport && (
              <div className="lg:col-span-2 bg-white rounded-lg shadow p-6">
                <h2 className="text-xl font-semibold mb-4">调研报告</h2>

                {reportStatus === "pending" || reportStatus === "running" ? (
                  <div className="text-center py-8">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
                    <p className="text-gray-600">报告生成中，请稍候...</p>
                  </div>
                ) : reportStatus === "completed" && reportContent ? (
                  <div className="prose max-w-none">
                    <pre className="whitespace-pre-wrap bg-gray-50 p-4 rounded-lg">
                      {reportContent}
                    </pre>
                  </div>
                ) : reportStatus === "failed" ? (
                  <div className="text-center py-8 text-red-600">报告生成失败</div>
                ) : null}
              </div>
            )}
          </div>
        )}

        {/* 历史报告页面 */}
        {activeTab === "history" && (
          <div className="bg-white rounded-lg shadow">
            {reports.length === 0 ? (
              <div className="text-center py-12 text-gray-500">暂无调研报告</div>
            ) : (
              <div className="divide-y">
                {reports.map((report) => (
                  <div
                    key={report.id}
                    onClick={() => handleViewReport(report.id)}
                    className="p-4 hover:bg-gray-50 cursor-pointer"
                  >
                    <div className="flex justify-between items-start">
                      <div>
                        <h3 className="font-medium text-gray-900">{report.title}</h3>
                        <div className="text-sm text-gray-600 mt-1">
                          使用技能: {report.selected_skills.join(", ")}
                        </div>
                        <div className="text-xs text-gray-400 mt-1">
                          创建时间: {new Date(report.created_at).toLocaleString()}
                        </div>
                      </div>
                      <span
                        className={`px-2 py-1 text-xs rounded ${
                          report.status === "completed"
                            ? "bg-green-100 text-green-700"
                            : report.status === "failed"
                              ? "bg-red-100 text-red-700"
                              : "bg-yellow-100 text-yellow-700"
                        }`}
                      >
                        {report.status === "completed"
                          ? "已完成"
                          : report.status === "failed"
                            ? "失败"
                            : "进行中"}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* 报告详情 */}
            {selectedReport && reportContent && (
              <div className="border-t p-6">
                <h3 className="text-lg font-semibold mb-4">报告内容</h3>
                <pre className="whitespace-pre-wrap bg-gray-50 p-4 rounded-lg max-h-96 overflow-auto">
                  {reportContent}
                </pre>
              </div>
            )}
          </div>
        )}

        {/* 模板管理页面 */}
        {activeTab === "templates" && (
          <div className="bg-white rounded-lg shadow">
            {templates.length === 0 ? (
              <div className="text-center py-12 text-gray-500">
                暂无调研模板，请先创建调研并保存为模板
              </div>
            ) : (
              <div className="divide-y">
                {templates.map((template) => (
                  <div key={template.id} className="p-4">
                    <div className="flex justify-between items-start">
                      <div>
                        <h3 className="font-medium text-gray-900">{template.name}</h3>
                        {template.description && (
                          <div className="text-sm text-gray-600 mt-1">{template.description}</div>
                        )}
                        <div className="text-sm text-gray-500 mt-2">
                          包含技能: {template.skill_names.join(", ")}
                        </div>
                      </div>
                      <div className="flex space-x-2">
                        <button
                          onClick={() => handleUseTemplate(template)}
                          className="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700"
                        >
                          使用
                        </button>
                        <button
                          onClick={() => handleDeleteTemplate(template.id)}
                          className="px-3 py-1 text-sm bg-red-600 text-white rounded hover:bg-red-700"
                        >
                          删除
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* 保存模板弹窗 */}
        {showSaveTemplate && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg p-6 w-full max-w-md">
              <h3 className="text-lg font-semibold mb-4">保存调研模板</h3>

              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  模板名称 *
                </label>
                <input
                  type="text"
                  value={templateName}
                  onChange={(e) => setTemplateName(e.target.value)}
                  placeholder="例如：市场进入分析模板"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>

              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  模板描述（可选）
                </label>
                <textarea
                  value={templateDesc}
                  onChange={(e) => setTemplateDesc(e.target.value)}
                  placeholder="描述此模板的适用场景"
                  rows={3}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>

              <div className="mb-4">
                <div className="text-sm text-gray-600">
                  已选择技能: {selectedSkills.join(", ")}
                </div>
              </div>

              <div className="flex justify-end space-x-3">
                <button
                  onClick={() => setShowSaveTemplate(false)}
                  className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200"
                >
                  取消
                </button>
                <button
                  onClick={handleSaveTemplate}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                >
                  保存
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
