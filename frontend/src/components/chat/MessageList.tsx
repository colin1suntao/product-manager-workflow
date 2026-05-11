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
  thinking_time_ms?: number;
  token_usage?: { prompt_tokens: number; completion_tokens: number; total_tokens: number };
  tool_calls?: Array<{ tool_name: string; tool_type: string; description: string }>;
  context_length?: number;
  context_limit?: number;
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

            {/* Message Metadata: thinking time, tokens, tool calls */}
            {message.role === "assistant" && (message.thinking_time_ms || message.token_usage?.total_tokens || (message.tool_calls && message.tool_calls.length > 0)) && (
              <div className="mt-2 pt-2 border-t border-gray-100">
                <div className="flex flex-wrap items-center gap-3 text-xs text-gray-400">
                  {message.thinking_time_ms ? (
                    <span className="flex items-center gap-1" title="思考时间">
                      <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      {message.thinking_time_ms >= 1000
                        ? `${(message.thinking_time_ms / 1000).toFixed(1)}s`
                        : `${message.thinking_time_ms}ms`}
                    </span>
                  ) : null}
                  {message.token_usage?.total_tokens ? (
                    <span className="flex items-center gap-1" title={`输入 ${message.token_usage.prompt_tokens?.toLocaleString() || 0} / 输出 ${message.token_usage.completion_tokens?.toLocaleString() || 0} tokens`}>
                      <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                      {message.token_usage.total_tokens?.toLocaleString()} tokens
                    </span>
                  ) : null}
                  {message.tool_calls && message.tool_calls.length > 0 && (
                    <span className="flex items-center gap-1" title={message.tool_calls.map(t => t.description).join("\n")}>
                      <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                      </svg>
                      {message.tool_calls.length} 个工具
                    </span>
                  )}
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
