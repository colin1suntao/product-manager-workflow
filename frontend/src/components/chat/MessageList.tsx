"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface Message {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  task_mode?: string | null;
  task_status?: string | null;
  artifacts?: Array<{ name: string; url: string; type: string }>;
  created_at: string;
}

interface MessageListProps {
  messages: Message[];
  loading?: boolean;
}

const TASK_MODE_LABELS: Record<string, string> = {
  requirement: "需求分析",
  prototype: "原型设计",
  prd: "文档撰写",
  market_research: "市场调研",
};

const TASK_STATUS_LABELS: Record<string, { label: string; color: string }> = {
  pending: { label: "待处理", color: "bg-gray-100 text-gray-600" },
  running: { label: "执行中", color: "bg-blue-100 text-blue-600" },
  completed: { label: "已完成", color: "bg-green-100 text-green-600" },
  failed: { label: "失败", color: "bg-red-100 text-red-600" },
};

export default function MessageList({ messages, loading = false }: MessageListProps) {
  if (messages.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 mx-auto mb-4 bg-blue-100 rounded-full flex items-center justify-center">
            <svg className="w-8 h-8 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
            </svg>
          </div>
          <h3 className="text-lg font-medium text-gray-900 mb-2">开始对话</h3>
          <p className="text-gray-500 max-w-sm">
            描述您的需求，我将帮助您完成需求分析、原型设计、文档撰写或市场调研。
          </p>
          <div className="mt-4 flex flex-wrap gap-2 justify-center">
            <span className="px-3 py-1 bg-gray-100 text-gray-600 rounded-full text-sm">需求分析</span>
            <span className="px-3 py-1 bg-gray-100 text-gray-600 rounded-full text-sm">原型设计</span>
            <span className="px-3 py-1 bg-gray-100 text-gray-600 rounded-full text-sm">文档撰写</span>
            <span className="px-3 py-1 bg-gray-100 text-gray-600 rounded-full text-sm">市场调研</span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-auto p-4 space-y-4">
      {messages.map((message) => (
        <div
          key={message.id}
          className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
        >
          <div
            className={`max-w-[80%] ${
              message.role === "user"
                ? "bg-blue-600 text-white"
                : "bg-white border"
            } rounded-lg p-4 shadow-sm`}
          >
            {/* Task Mode Badge */}
            {message.task_mode && (
              <div className="mb-2 flex items-center gap-2">
                <span className="px-2 py-0.5 bg-blue-100 text-blue-700 rounded text-xs font-medium">
                  {TASK_MODE_LABELS[message.task_mode] || message.task_mode}
                </span>
                {message.task_status && (
                  <span
                    className={`px-2 py-0.5 rounded text-xs font-medium ${
                      TASK_STATUS_LABELS[message.task_status]?.color || "bg-gray-100 text-gray-600"
                    }`}
                  >
                    {TASK_STATUS_LABELS[message.task_status]?.label || message.task_status}
                  </span>
                )}
              </div>
            )}

            {/* Message Content */}
            {message.role === "user" ? (
              <div className="whitespace-pre-wrap">{message.content}</div>
            ) : (
              <div className="prose prose-sm max-w-none">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {message.content}
                </ReactMarkdown>
              </div>
            )}

            {/* Artifacts */}
            {message.artifacts && message.artifacts.length > 0 && (
              <div className="mt-3 pt-3 border-t">
                <div className="text-xs font-medium text-gray-500 mb-2">附件：</div>
                <div className="flex flex-wrap gap-2">
                  {message.artifacts.map((artifact, idx) => (
                    <a
                      key={idx}
                      href={artifact.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-1 px-2 py-1 bg-gray-100 hover:bg-gray-200 rounded text-xs text-gray-700 transition-colors"
                    >
                      <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                      {artifact.name}
                    </a>
                  ))}
                </div>
              </div>
            )}

            {/* Timestamp */}
            <div
              className={`mt-2 text-xs ${
                message.role === "user" ? "text-blue-200" : "text-gray-400"
              }`}
            >
              {new Date(message.created_at).toLocaleTimeString()}
            </div>
          </div>
        </div>
      ))}

      {/* Loading Indicator */}
      {loading && (
        <div className="flex justify-start">
          <div className="bg-white border rounded-lg p-4 shadow-sm">
            <div className="flex items-center gap-2">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
              <span className="text-gray-500 text-sm">思考中...</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
