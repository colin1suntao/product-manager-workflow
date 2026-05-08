"use client";

import { useState, useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { workflowApi } from "@/lib/api";
import { getAccessToken } from "@/lib/auth";

interface PMSkill {
  name: string;
  description: string;
  type: string;
  best_for: string[];
  estimated_time: string;
}

const SKILL_TYPE_LABELS: Record<string, string> = {
  component: "组件",
  interactive: "交互",
  workflow: "工作流",
  native: "原生",
};

const SKILL_TYPE_COLORS: Record<string, string> = {
  component: "bg-blue-100 text-blue-700 border-blue-300",
  interactive: "bg-green-100 text-green-700 border-green-300",
  workflow: "bg-purple-100 text-purple-700 border-purple-300",
  native: "bg-gray-100 text-gray-700 border-gray-300",
};

export default function RequirementsPage() {
  return (
    <Suspense fallback={<div className="flex items-center justify-center h-screen">加载中...</div>}>
      <RequirementsContent />
    </Suspense>
  );
}

function RequirementsContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [title, setTitle] = useState("");
  const [requirements, setRequirements] = useState("");
  const [targetAudience, setTargetAudience] = useState("");
  const [constraints, setConstraints] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // PM Skills 相关状态
  const [skills, setSkills] = useState<PMSkill[]>([]);
  const [selectedSkills, setSelectedSkills] = useState<string[]>([]);
  const [skillsLoading, setSkillsLoading] = useState(false);
  const [showSkills, setShowSkills] = useState(false);
  const [skillFilter, setSkillFilter] = useState<string>("");
  const [skillSearch, setSkillSearch] = useState("");

  // 加载 PM Skills
  useEffect(() => {
    loadSkills();
    // 检查 URL 参数中是否有预选的技能
    const skillParam = searchParams.get("skill");
    if (skillParam) {
      setSelectedSkills([skillParam]);
      setShowSkills(true);
    }
  }, [searchParams]);

  const loadSkills = async () => {
    setSkillsLoading(true);
    try {
      const token = getAccessToken();
      const response = await fetch("/api/v1/skills/list", {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        const data = await response.json();
        setSkills(data.skills);
      }
    } catch (error) {
      console.error("Failed to load skills:", error);
    } finally {
      setSkillsLoading(false);
    }
  };

  const toggleSkill = (skillName: string) => {
    setSelectedSkills((prev) =>
      prev.includes(skillName)
        ? prev.filter((name) => name !== skillName)
        : [...prev, skillName]
    );
  };

  const filteredSkills = skills.filter((skill) => {
    const matchesType = !skillFilter || skill.type === skillFilter;
    const matchesSearch =
      !skillSearch ||
      skill.name.toLowerCase().includes(skillSearch.toLowerCase()) ||
      skill.description.toLowerCase().includes(skillSearch.toLowerCase());
    return matchesType && matchesSearch;
  });

  // 按类型分组技能
  const groupedSkills = filteredSkills.reduce(
    (acc, skill) => {
      const type = skill.type || "native";
      if (!acc[type]) acc[type] = [];
      acc[type].push(skill);
      return acc;
    },
    {} as Record<string, PMSkill[]>
  );

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
        skills: selectedSkills.length > 0 ? selectedSkills : undefined,
      });
      router.push(`/workflows/detail?id=${run.id}`);
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

          {/* PM Skills 选择区域 */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="block text-sm font-medium text-gray-700">
                PM Skills 技能选择
                <span className="text-gray-400 font-normal ml-1">(可选)</span>
              </label>
              <button
                type="button"
                onClick={() => setShowSkills(!showSkills)}
                className="text-sm text-blue-600 hover:text-blue-700"
              >
                {showSkills ? "收起" : "展开"}技能选择
              </button>
            </div>

            {showSkills && (
              <div className="border border-gray-200 rounded-lg p-4 bg-gray-50">
                {/* 搜索和过滤 */}
                <div className="mb-4 flex flex-wrap gap-3">
                  <div className="flex-1 min-w-[200px]">
                    <input
                      type="text"
                      placeholder="搜索技能..."
                      value={skillSearch}
                      onChange={(e) => setSkillSearch(e.target.value)}
                      className="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-sm"
                    />
                  </div>
                  <div className="flex gap-2">
                    {["", "component", "interactive", "workflow"].map((type) => (
                      <button
                        key={type}
                        type="button"
                        onClick={() => setSkillFilter(type)}
                        className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                          skillFilter === type
                            ? "bg-blue-600 text-white"
                            : "bg-white text-gray-600 border border-gray-300 hover:bg-gray-50"
                        }`}
                      >
                        {type ? SKILL_TYPE_LABELS[type] : "全部"}
                      </button>
                    ))}
                  </div>
                </div>

                {/* 已选技能 */}
                {selectedSkills.length > 0 && (
                  <div className="mb-4 p-3 bg-blue-50 rounded-lg border border-blue-200">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium text-blue-800">
                        已选技能 ({selectedSkills.length})
                      </span>
                      <button
                        type="button"
                        onClick={() => setSelectedSkills([])}
                        className="text-xs text-blue-600 hover:text-blue-700"
                      >
                        清空
                      </button>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {selectedSkills.map((skillName) => {
                        const skill = skills.find((s) => s.name === skillName);
                        return (
                          <span
                            key={skillName}
                            className="inline-flex items-center gap-1 px-2 py-1 bg-blue-100 text-blue-800 rounded-full text-xs"
                          >
                            {skillName}
                            <button
                              type="button"
                              onClick={() => toggleSkill(skillName)}
                              className="hover:text-blue-900"
                            >
                              ×
                            </button>
                          </span>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* 技能列表 */}
                {skillsLoading ? (
                  <div className="text-center py-4">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
                    <p className="mt-2 text-gray-500 text-sm">加载技能中...</p>
                  </div>
                ) : (
                  <div className="max-h-[400px] overflow-y-auto space-y-4">
                    {Object.entries(groupedSkills).map(([type, typeSkills]) => (
                      <div key={type}>
                        <h4 className="text-xs font-semibold text-gray-500 uppercase mb-2">
                          {SKILL_TYPE_LABELS[type] || type} 技能
                        </h4>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                          {typeSkills.map((skill) => (
                            <div
                              key={skill.name}
                              onClick={() => toggleSkill(skill.name)}
                              className={`p-3 rounded-lg border cursor-pointer transition-all ${
                                selectedSkills.includes(skill.name)
                                  ? "border-blue-500 bg-blue-50 ring-1 ring-blue-200"
                                  : "border-gray-200 bg-white hover:border-gray-300"
                              }`}
                            >
                              <div className="flex items-start justify-between">
                                <div className="flex-1">
                                  <div className="flex items-center gap-2">
                                    <input
                                      type="checkbox"
                                      checked={selectedSkills.includes(skill.name)}
                                      onChange={() => {}}
                                      className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                                    />
                                    <span className="font-medium text-sm text-gray-900">
                                      {skill.name}
                                    </span>
                                  </div>
                                  <p className="text-xs text-gray-500 mt-1 line-clamp-2">
                                    {skill.description}
                                  </p>
                                  {skill.best_for.length > 0 && (
                                    <div className="mt-1.5 flex flex-wrap gap-1">
                                      {skill.best_for.slice(0, 2).map((item, i) => (
                                        <span
                                          key={i}
                                          className="px-1.5 py-0.5 bg-gray-100 text-gray-600 rounded text-xs"
                                        >
                                          {item.length > 15 ? item.slice(0, 15) + "..." : item}
                                        </span>
                                      ))}
                                    </div>
                                  )}
                                </div>
                                {skill.estimated_time && (
                                  <span className="text-xs text-gray-400 ml-2 whitespace-nowrap">
                                    {skill.estimated_time}
                                  </span>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {!showSkills && selectedSkills.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-2">
                {selectedSkills.map((skillName) => (
                  <span
                    key={skillName}
                    className="inline-flex items-center gap-1 px-2 py-1 bg-blue-100 text-blue-800 rounded-full text-xs"
                  >
                    {skillName}
                    <button
                      type="button"
                      onClick={() => toggleSkill(skillName)}
                      className="hover:text-blue-900"
                    >
                      ×
                    </button>
                  </span>
                ))}
              </div>
            )}
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
