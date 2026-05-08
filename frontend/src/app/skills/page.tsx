"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { getAccessToken } from "@/lib/auth";

interface PMSkill {
  name: string;
  description: string;
  type: string;
  best_for: string[];
  scenarios: string[];
  estimated_time: string;
}

interface SkillDetail {
  name: string;
  description: string;
  intent: string;
  type: string;
  best_for: string[];
  scenarios: string[];
  estimated_time: string;
  system_prompt: string;
  steps: string[];
}

const SKILL_TYPE_LABELS: Record<string, string> = {
  component: "组件技能",
  interactive: "交互技能",
  workflow: "工作流技能",
  native: "原生技能",
};

const SKILL_TYPE_COLORS: Record<string, string> = {
  component: "bg-blue-100 text-blue-800",
  interactive: "bg-green-100 text-green-800",
  workflow: "bg-purple-100 text-purple-800",
  native: "bg-gray-100 text-gray-800",
};

export default function SkillsPage() {
  const router = useRouter();
  const [skills, setSkills] = useState<PMSkill[]>([]);
  const [selectedSkill, setSelectedSkill] = useState<SkillDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [filterType, setFilterType] = useState<string>("");
  const [searchQuery, setSearchQuery] = useState("");

  useEffect(() => {
    if (!getAccessToken()) {
      router.push("/auth/login");
      return;
    }
    loadSkills();
  }, [router, filterType]);

  const loadSkills = async () => {
    setLoading(true);
    try {
      const token = getAccessToken();
      const query = filterType ? `?skill_type=${filterType}` : "";
      const response = await fetch(`/api/v1/skills/list${query}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        const data = await response.json();
        setSkills(data.skills);
      }
    } catch (error) {
      console.error("Failed to load skills:", error);
    } finally {
      setLoading(false);
    }
  };

  const loadSkillDetail = async (skillName: string) => {
    try {
      const token = getAccessToken();
      const response = await fetch(`/api/v1/skills/${skillName}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        const data = await response.json();
        setSelectedSkill(data);
      }
    } catch (error) {
      console.error("Failed to load skill detail:", error);
    }
  };

  const filteredSkills = skills.filter(
    (skill) =>
      skill.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      skill.description.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">PM Skills 技能库</h1>
          <p className="mt-2 text-gray-600">
            基于 Product-Manager-Skills 的 47 个专业产品经理技能，帮助你生成更专业、更精细的产品文档
          </p>
        </div>

        {/* 筛选和搜索 */}
        <div className="mb-6 flex flex-wrap gap-4">
          <div className="flex-1 min-w-[200px]">
            <input
              type="text"
              placeholder="搜索技能..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
          <div className="flex gap-2">
            {["", "component", "interactive", "workflow"].map((type) => (
              <button
                key={type}
                onClick={() => setFilterType(type)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  filterType === type
                    ? "bg-blue-600 text-white"
                    : "bg-white text-gray-700 border border-gray-300 hover:bg-gray-50"
                }`}
              >
                {type ? SKILL_TYPE_LABELS[type] : "全部"}
              </button>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* 技能列表 */}
          <div className="lg:col-span-2">
            {loading ? (
              <div className="text-center py-12">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
                <p className="mt-4 text-gray-500">加载中...</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {filteredSkills.map((skill) => (
                  <div
                    key={skill.name}
                    onClick={() => loadSkillDetail(skill.name)}
                    className={`bg-white rounded-lg border p-4 cursor-pointer transition-all hover:shadow-md ${
                      selectedSkill?.name === skill.name
                        ? "border-blue-500 ring-2 ring-blue-200"
                        : "border-gray-200"
                    }`}
                  >
                    <div className="flex items-start justify-between mb-2">
                      <h3 className="font-semibold text-gray-900 text-sm">
                        {skill.name}
                      </h3>
                      <span
                        className={`px-2 py-1 rounded-full text-xs font-medium ${
                          SKILL_TYPE_COLORS[skill.type] || SKILL_TYPE_COLORS.native
                        }`}
                      >
                        {SKILL_TYPE_LABELS[skill.type] || skill.type}
                      </span>
                    </div>
                    <p className="text-gray-600 text-xs line-clamp-2 mb-3">
                      {skill.description}
                    </p>
                    {skill.estimated_time && (
                      <p className="text-gray-400 text-xs">
                        预计时间: {skill.estimated_time}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* 技能详情 */}
          <div className="lg:col-span-1">
            {selectedSkill ? (
              <div className="bg-white rounded-lg border border-gray-200 p-6 sticky top-8">
                <h2 className="text-xl font-bold text-gray-900 mb-2">
                  {selectedSkill.name}
                </h2>
                <span
                  className={`inline-block px-2 py-1 rounded-full text-xs font-medium mb-4 ${
                    SKILL_TYPE_COLORS[selectedSkill.type] || SKILL_TYPE_COLORS.native
                  }`}
                >
                  {SKILL_TYPE_LABELS[selectedSkill.type] || selectedSkill.type}
                </span>

                {selectedSkill.intent && (
                  <div className="mb-4">
                    <h3 className="text-sm font-semibold text-gray-700 mb-1">意图</h3>
                    <p className="text-gray-600 text-sm">{selectedSkill.intent}</p>
                  </div>
                )}

                {selectedSkill.best_for.length > 0 && (
                  <div className="mb-4">
                    <h3 className="text-sm font-semibold text-gray-700 mb-1">
                      最佳使用场景
                    </h3>
                    <ul className="list-disc list-inside text-gray-600 text-sm">
                      {selectedSkill.best_for.map((item, i) => (
                        <li key={i}>{item}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {selectedSkill.scenarios.length > 0 && (
                  <div className="mb-4">
                    <h3 className="text-sm font-semibold text-gray-700 mb-1">
                      使用示例
                    </h3>
                    <ul className="list-disc list-inside text-gray-600 text-sm">
                      {selectedSkill.scenarios.map((item, i) => (
                        <li key={i}>{item}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {selectedSkill.steps.length > 0 && (
                  <div className="mb-4">
                    <h3 className="text-sm font-semibold text-gray-700 mb-1">
                      执行步骤
                    </h3>
                    <ol className="list-decimal list-inside text-gray-600 text-sm">
                      {selectedSkill.steps.map((step, i) => (
                        <li key={i}>{step}</li>
                      ))}
                    </ol>
                  </div>
                )}

                <button
                  onClick={() => {
                    router.push(`/requirements?skill=${selectedSkill.name}`);
                  }}
                  className="w-full mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                >
                  使用此技能
                </button>
              </div>
            ) : (
              <div className="bg-white rounded-lg border border-gray-200 p-6 text-center text-gray-500">
                <p>点击左侧技能查看详情</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
