"use client";

import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface ThinkingStep {
  step_name: string;
  description: string;
  duration_ms?: number;
  status?: string;
  detail?: string;
}

interface Message {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  task_mode?: string | null;
  task_status?: string | null;
  artifacts?: Array<{ name: string; url: string; type: string }>;
  thinking_time_ms?: number;
  thinking_process?: ThinkingStep[];
  model_id?: string;
  intent_summary?: string;
  token_usage?: { prompt_tokens: number; completion_tokens: number; total_tokens: number };
  tool_calls?: Array<{ tool_name: string; tool_type: string; description: string; duration_ms?: number; status?: string }>;
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

const STEP_ICONS: Record<string, string> = {
  context_building: "M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z",
  intent_analysis: "M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456zM16.894 20.567L16.5 21.75l-.394-1.183a2.25 2.25 0 00-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 001.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 001.423 1.423l1.183.394-1.183.394a2.25 2.25 0 00-1.423 1.423z",
  task_routing: "M7.5 21L3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5",
  task_execution: "M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.348a1.125 1.125 0 010 1.971l-11.54 6.347a1.125 1.125 0 01-1.667-.985V5.653z",
  mode_selection: "M3.75 6A2.25 2.25 0 016 3.75h2.25A2.25 2.25 0 0110.5 6v2.25a2.25 2.25 0 01-2.25 2.25H6a2.25 2.25 0 01-2.25-2.25V6zM3.75 15.75A2.25 2.25 0 016 13.5h2.25a2.25 2.25 0 012.25 2.25V18a2.25 2.25 0 01-2.25 2.25H6A2.25 2.25 0 013.75 18v-2.25zM13.5 6a2.25 2.25 0 012.25-2.25H18A2.25 2.25 0 0120.25 6v2.25A2.25 2.25 0 0118 10.5h-2.25a2.25 2.25 0 01-2.25-2.25V6zM13.5 15.75a2.25 2.25 0 012.25-2.25H18a2.25 2.25 0 012.25 2.25V18A2.25 2.25 0 0118 20.25h-2.25A2.25 2.25 0 0113.5 18v-2.25z",
  clarification: "M9.879 7.519c1.171-1.025 3.071-1.025 4.242 0 1.172 1.025 1.172 2.687 0 3.712-.203.179-.43.326-.67.442-.745.361-1.45.999-1.45 1.827v.75M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9 5.25h.008v.008H12v-.008z",
};

function ThinkingProcessPanel({ steps, modelId, intentSummary, thinkingTimeMs, toolCalls }: {
  steps: ThinkingStep[];
  modelId?: string;
  intentSummary?: string;
  thinkingTimeMs?: number;
  toolCalls?: Array<{ tool_name: string; tool_type: string; description: string; duration_ms?: number; status?: string }>;
}) {
  const [expanded, setExpanded] = useState(false);

  if (!steps || steps.length === 0) return null;

  return (
    <div className="mt-2 pt-2 border-t border-gray-100">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-2 text-xs text-blue-500 hover:text-blue-700 transition-colors w-full text-left"
      >
        <svg
          className={`w-3.5 h-3.5 transition-transform ${expanded ? "rotate-90" : ""}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
        <span className="font-medium">思考过程</span>
        {thinkingTimeMs ? (
          <span className="text-gray-400 ml-1">
            {thinkingTimeMs >= 1000 ? `${(thinkingTimeMs / 1000).toFixed(1)}s` : `${thinkingTimeMs}ms`}
          </span>
        ) : null}
        {modelId ? (
          <span className="ml-auto px-1.5 py-0.5 bg-purple-50 text-purple-600 rounded text-[10px] font-mono">
            {modelId}
          </span>
        ) : null}
      </button>

      {expanded && (
        <div className="mt-2 space-y-1.5">
          {/* Intent summary */}
          {intentSummary && (
            <div className="flex items-start gap-2 px-2 py-1.5 bg-amber-50 rounded text-xs">
              <svg className="w-3.5 h-3.5 text-amber-500 mt-0.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
              </svg>
              <div>
                <span className="font-medium text-amber-700">意图识别: </span>
                <span className="text-amber-600">{intentSummary}</span>
              </div>
            </div>
          )}

          {/* Steps timeline */}
          <div className="relative pl-4">
            {steps.map((step, idx) => {
              const isLast = idx === steps.length - 1;
              const iconPath = STEP_ICONS[step.step_name] || STEP_ICONS.task_execution;
              const statusColor = step.status === "pending" ? "text-yellow-500" : step.status === "failed" ? "text-red-500" : "text-green-500";

              return (
                <div key={idx} className="relative pb-3">
                  {!isLast && (
                    <div className="absolute left-[7px] top-5 bottom-0 w-px bg-gray-200" />
                  )}
                  <div className="flex items-start gap-2.5">
                    <div className="relative z-10 mt-0.5">
                      <div className={`w-[15px] h-[15px] rounded-full border-2 flex items-center justify-center ${step.status === "pending" ? "border-yellow-400 bg-yellow-50" : step.status === "failed" ? "border-red-400 bg-red-50" : "border-green-400 bg-green-50"}`}>
                        <svg className={`w-2 h-2 ${statusColor}`} fill="currentColor" viewBox="0 0 8 8">
                          <circle cx="4" cy="4" r="3" />
                        </svg>
                      </div>
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <svg className="w-3 h-3 text-gray-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={iconPath} />
                        </svg>
                        <span className="text-xs font-medium text-gray-700">{step.description}</span>
                        {step.duration_ms ? (
                          <span className="text-[10px] text-gray-400">
                            {step.duration_ms >= 1000 ? `${(step.duration_ms / 1000).toFixed(1)}s` : `${step.duration_ms}ms`}
                          </span>
                        ) : null}
                      </div>
                      {step.detail && (
                        <p className="text-[11px] text-gray-500 mt-0.5 ml-5">{step.detail}</p>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Skill/Tool calls */}
          {toolCalls && toolCalls.length > 0 && (
            <div className="mt-1 px-2 py-1.5 bg-blue-50 rounded">
              <div className="text-[11px] font-medium text-blue-700 mb-1">技能调用</div>
              <div className="space-y-1">
                {toolCalls.map((tc, idx) => (
                  <div key={idx} className="flex items-center gap-2 text-[11px]">
                    <span className={`px-1 py-0.5 rounded text-[10px] font-medium ${tc.tool_type === "skill" ? "bg-violet-100 text-violet-700" : "bg-sky-100 text-sky-700"}`}>
                      {tc.tool_type === "skill" ? "Skill" : "Func"}
                    </span>
                    <span className="text-gray-700 font-medium">{tc.tool_name}</span>
                    {tc.duration_ms ? (
                      <span className="text-gray-400">{tc.duration_ms >= 1000 ? `${(tc.duration_ms / 1000).toFixed(1)}s` : `${tc.duration_ms}ms`}</span>
                    ) : null}
                    {tc.status && tc.status !== "success" && tc.status !== "used" && (
                      <span className="text-yellow-500">{tc.status}</span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

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

            {/* Thinking Process Panel (assistant only) */}
            {message.role === "assistant" && message.thinking_process && message.thinking_process.length > 0 && (
              <ThinkingProcessPanel
                steps={message.thinking_process}
                modelId={message.model_id}
                intentSummary={message.intent_summary}
                thinkingTimeMs={message.thinking_time_ms}
                toolCalls={message.tool_calls}
              />
            )}

            {/* Compact metadata bar (for messages without thinking_process) */}
            {message.role === "assistant" && (!message.thinking_process || message.thinking_process.length === 0) && (message.thinking_time_ms || message.token_usage?.total_tokens || (message.tool_calls && message.tool_calls.length > 0)) && (
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
