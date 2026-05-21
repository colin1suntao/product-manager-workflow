"use client";

interface TaskMode {
  id: string;
  label: string;
  description: string;
  icon: React.ReactNode;
}

const TASK_MODES: TaskMode[] = [
  {
    id: "requirement",
    label: "需求分析",
    description: "梳理和结构化产品需求",
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
      </svg>
    ),
  },
  {
    id: "prototype",
    label: "原型设计",
    description: "生成高保真界面原型",
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z" />
      </svg>
    ),
  },
  {
    id: "prd",
    label: "文档撰写",
    description: "生成 PRD 产品需求文档",
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
      </svg>
    ),
  },
  {
    id: "market_research",
    label: "市场调研",
    description: "进行市场分析和竞品研究",
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
      </svg>
    ),
  },
];

interface TaskModeSelectorProps {
  selectedMode: string | null;
  onSelectMode: (modeId: string | null) => void;
}

export default function TaskModeSelector({
  selectedMode,
  onSelectMode,
}: TaskModeSelectorProps) {
  return (
    <div className="flex gap-2 flex-wrap">
      {TASK_MODES.map((mode) => (
        <button
          key={mode.id}
          onClick={() => onSelectMode(selectedMode === mode.id ? null : mode.id)}
          className={`flex items-center gap-2 px-3 py-2 rounded-lg border transition-colors ${
            selectedMode === mode.id
              ? "bg-blue-50 border-blue-300 text-blue-700"
              : "bg-white border-gray-200 text-gray-600 hover:border-gray-300 hover:bg-gray-50"
          }`}
        >
          {mode.icon}
          <div className="text-left">
            <div className="text-sm font-medium">{mode.label}</div>
            <div className="text-xs text-gray-500">{mode.description}</div>
          </div>
        </button>
      ))}
    </div>
  );
}
