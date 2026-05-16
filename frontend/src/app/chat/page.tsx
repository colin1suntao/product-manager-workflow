"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { chatApi, knowledgeBaseApi, componentLibraryApi } from "@/lib/api";
import { getAccessToken } from "@/lib/auth";
import ChatSidebar from "@/components/chat/ChatSidebar";
import ChatInput from "@/components/chat/ChatInput";
import MessageList from "@/components/chat/MessageList";
import TaskModeSelector from "@/components/chat/TaskModeSelector";

interface ChatSession {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

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

function ConfirmDialog({ open, title, message, onConfirm, onCancel }: {
  open: boolean;
  title: string;
  message: string;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
      <div className="bg-white rounded-lg shadow-xl p-6 max-w-sm w-full mx-4">
        <h3 className="text-lg font-semibold text-gray-900 mb-2">{title}</h3>
        <p className="text-sm text-gray-600 mb-6">{message}</p>
        <div className="flex justify-end gap-2">
          <button onClick={onCancel} className="px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-100 text-sm">取消</button>
          <button onClick={onConfirm} className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 text-sm">确认删除</button>
        </div>
      </div>
    </div>
  );
}

export default function ChatPage() {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [sessionsLoading, setSessionsLoading] = useState(true);
  const [selectedMode, setSelectedMode] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [contextLength, setContextLength] = useState(0);
  const [contextLimit, setContextLimit] = useState(128000);
  const [compressing, setCompressing] = useState(false);
  const [creatingSession, setCreatingSession] = useState(false);
  const [pendingMessage, setPendingMessage] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);
  const [selectedTemplateId, setSelectedTemplateId] = useState<string | null>(null);
  const [templates, setTemplates] = useState<Array<{ id: string; name: string; type: string; type_label: string }>>([]);
  const [showTemplateSelector, setShowTemplateSelector] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const errorTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Load sessions on mount
  useEffect(() => {
    loadSessions();
    loadTemplates();
  }, []);

  const loadTemplates = async () => {
    try {
      const [kbData, compData] = await Promise.all([
        knowledgeBaseApi.listTemplates("document"),
        componentLibraryApi.listTemplates(),
      ]);
      const kbItems = (kbData.templates || []).map((t) => ({
        id: t.id,
        name: t.name,
        type: "document" as const,
        type_label: "产品文档模板" as const,
      }));
      const compItems = (compData.templates || []).map((t) => ({
        id: t.id,
        name: t.name,
        type: "prototype" as const,
        type_label: "原型组件模板" as const,
      }));
      setTemplates([...compItems, ...kbItems]);
    } catch (err) {
      console.error("Failed to load templates:", err);
    }
  };

  // Load messages when session changes
  useEffect(() => {
    if (activeSessionId) {
      loadMessages(activeSessionId);
      setPendingMessage(null);
    } else {
      setMessages([]);
    }
  }, [activeSessionId]);

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const showError = useCallback((msg: string) => {
    setError(msg);
    if (errorTimer.current) clearTimeout(errorTimer.current);
    errorTimer.current = setTimeout(() => setError(null), 5000);
  }, []);

  const loadSessions = async () => {
    try {
      setSessionsLoading(true);
      const data = await chatApi.listSessions();
      setSessions(data.sessions);
    } catch (error) {
      console.error("Failed to load sessions:", error);
    } finally {
      setSessionsLoading(false);
    }
  };

  const loadMessages = async (sessionId: string) => {
    try {
      const data = await chatApi.getMessages(sessionId);
      setMessages(data.messages);
    } catch (error) {
      console.error("Failed to load messages:", error);
      showError("加载消息失败");
    }
  };

  const handleCreateSession = async () => {
    try {
      setCreatingSession(true);
      const session = await chatApi.createSession();
      setSessions((prev) => [session, ...prev]);
      setActiveSessionId(session.id);
      return session.id;
    } catch (error) {
      console.error("Failed to create session:", error);
      showError("创建会话失败");
      return null;
    } finally {
      setCreatingSession(false);
    }
  };

  const handleDeleteSession = async (sessionId: string) => {
    setDeleteTarget(sessionId);
  };

  const confirmDeleteSession = async () => {
    if (!deleteTarget) return;
    try {
      await chatApi.deleteSession(deleteTarget);
      setSessions((prev) => prev.filter((s) => s.id !== deleteTarget));
      if (activeSessionId === deleteTarget) {
        setActiveSessionId(null);
      }
    } catch (error) {
      console.error("Failed to delete session:", error);
      showError("删除会话失败");
    } finally {
      setDeleteTarget(null);
    }
  };

  const handleCompressContext = async () => {
    if (!activeSessionId) return;
    try {
      setCompressing(true);
      const result = await chatApi.compressContext(activeSessionId);
      setContextLength(0);
      await loadMessages(activeSessionId);
      showError(`上下文已压缩，移除了 ${result.removed_count} 条旧消息`);
    } catch (error) {
      console.error("Failed to compress context:", error);
      showError("压缩上下文失败");
    } finally {
      setCompressing(false);
    }
  };

  const handleSendMessage = async (content: string) => {
    // 如果正在创建会话，暂存消息
    if (creatingSession || !activeSessionId) {
      if (!activeSessionId && !creatingSession) {
        const sid = await handleCreateSession();
        if (sid) {
          // 等待会话创建完成后发送
          setTimeout(() => handleSendMessage(content), 100);
        }
        return;
      }
      setPendingMessage(content);
      return;
    }

    try {
      setLoading(true);
      setError(null);

      // Add user message immediately
      const userMessage: Message = {
        id: `temp-${Date.now()}`,
        role: "user",
        content,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMessage]);

      // Send to API
      const response = await chatApi.sendMessage(activeSessionId, {
        content,
        task_mode: selectedMode || undefined,
        template_id: selectedTemplateId || undefined,
      });

      // Update messages with actual response
      setMessages((prev) => {
        const withoutTemp = prev.filter((m) => m.id !== userMessage.id);
        return [
          ...withoutTemp,
          {
            ...response.user_message,
            role: "user" as const,
          },
          {
            ...response.assistant_message,
            role: "assistant" as const,
          },
        ];
      });

      // Update context length from response
      if (response.assistant_message.context_length) {
        setContextLength(response.assistant_message.context_length);
      }
      if (response.assistant_message.context_limit) {
        setContextLimit(response.assistant_message.context_limit);
      }

      // Refresh sessions to update title
      loadSessions();
    } catch (error) {
      console.error("Failed to send message:", error);
      showError("发送消息失败，请重试");
      // Remove temp message on error
      setMessages((prev) => prev.filter((m) => !m.id.startsWith("temp-")));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex h-[calc(100vh-4rem)] bg-gray-100">
      <ConfirmDialog
        open={deleteTarget !== null}
        title="删除会话"
        message="删除后无法恢复，确定要删除此会话吗？"
        onConfirm={confirmDeleteSession}
        onCancel={() => setDeleteTarget(null)}
      />

      {/* Sidebar */}
      <ChatSidebar
        sessions={sessions}
        activeSessionId={activeSessionId}
        onSelectSession={setActiveSessionId}
        onCreateSession={handleCreateSession}
        onDeleteSession={handleDeleteSession}
        loading={sessionsLoading}
      />

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="bg-white border-b px-6 py-3">
          <div className="flex items-center justify-between">
            <h1 className="text-lg font-semibold text-gray-900">
              {creatingSession
                ? "正在创建会话..."
                : activeSessionId
                ? sessions.find((s) => s.id === activeSessionId)?.title || "会话"
                : "新建会话"}
            </h1>
            {activeSessionId && !creatingSession && (
              <div className="flex items-center gap-2">
                <span className="text-sm text-gray-500">
                  {messages.length} 条消息
                </span>
                {/* Context Length Indicator */}
                {contextLength > 0 && (
                  <div className="flex items-center gap-2">
                    <div className="w-24 h-2 bg-gray-200 rounded-full overflow-hidden" title={`上下文: ${(contextLength / 1024).toFixed(0)}KB / ${(contextLimit / 1024).toFixed(0)}KB`}>
                      <div
                        className={`h-full rounded-full transition-all ${
                          contextLength / contextLimit > 0.8
                            ? "bg-red-500"
                            : contextLength / contextLimit > 0.5
                            ? "bg-yellow-500"
                            : "bg-green-500"
                        }`}
                        style={{ width: `${Math.min(100, (contextLength / contextLimit) * 100)}%` }}
                      />
                    </div>
                    <span className="text-xs text-gray-400">
                      {Math.round((contextLength / contextLimit) * 100)}%
                    </span>
                    <button
                      onClick={handleCompressContext}
                      disabled={compressing}
                      className="text-xs px-2 py-1 border border-gray-300 rounded hover:bg-gray-100 disabled:opacity-50"
                      title="压缩上下文以释放空间"
                    >
                      {compressing ? "压缩中..." : "压缩"}
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Task Mode Selector */}
          <div className="mt-3">
            <TaskModeSelector
              selectedMode={selectedMode}
              onSelectMode={setSelectedMode}
            />
          </div>

          {/* Template Selector */}
          <div className="mt-2 flex items-center gap-2">
            <div className="relative">
              <button
                onClick={() => setShowTemplateSelector(!showTemplateSelector)}
                className={`text-xs px-3 py-1.5 rounded-lg border transition-colors flex items-center gap-1 ${
                  selectedTemplateId
                    ? "bg-purple-50 border-purple-300 text-purple-700"
                    : "bg-white border-gray-300 text-gray-500 hover:border-gray-400"
                }`}
              >
                <span>{selectedTemplateId ? templates.find((t) => t.id === selectedTemplateId)?.name || "已选模板" : "选择模板"}</span>
                <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </button>

              {showTemplateSelector && (
                <div className="absolute top-full left-0 mt-1 w-72 bg-white border border-gray-200 rounded-lg shadow-lg z-10 max-h-60 overflow-y-auto">
                  <div className="p-2">
                    {selectedTemplateId && (
                      <button
                        onClick={() => { setSelectedTemplateId(null); setShowTemplateSelector(false); }}
                        className="w-full text-left px-3 py-2 text-sm text-gray-500 hover:bg-gray-50 rounded"
                      >
                        清除选择
                      </button>
                    )}
                    {templates.length === 0 ? (
                      <p className="px-3 py-2 text-sm text-gray-400">暂无模板</p>
                    ) : (
                      <>
                        <p className="px-3 py-1 text-xs font-medium text-gray-400 uppercase">原型组件模板</p>
                        {templates.filter((t) => t.type === "prototype").map((t) => (
                          <button
                            key={t.id}
                            onClick={() => { setSelectedTemplateId(t.id); setShowTemplateSelector(false); }}
                            className={`w-full text-left px-3 py-2 text-sm rounded hover:bg-gray-50 ${
                              selectedTemplateId === t.id ? "bg-purple-50 text-purple-700" : "text-gray-700"
                            }`}
                          >
                            {t.name}
                          </button>
                        ))}
                        <p className="px-3 py-1 mt-1 text-xs font-medium text-gray-400 uppercase">产品文档模板</p>
                        {templates.filter((t) => t.type === "document").map((t) => (
                          <button
                            key={t.id}
                            onClick={() => { setSelectedTemplateId(t.id); setShowTemplateSelector(false); }}
                            className={`w-full text-left px-3 py-2 text-sm rounded hover:bg-gray-50 ${
                              selectedTemplateId === t.id ? "bg-purple-50 text-purple-700" : "text-gray-700"
                            }`}
                          >
                            {t.name}
                          </button>
                        ))}
                      </>
                    )}
                  </div>
                </div>
              )}
            </div>

            {selectedTemplateId && (
              <span className="text-xs text-purple-600">
                已应用模板
              </span>
            )}
          </div>
        </div>

        {/* Error Banner */}
        {error && (
          <div className="mx-4 mt-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm flex items-center justify-between">
            <span>{error}</span>
            <button onClick={() => setError(null)} className="ml-2 text-red-500 hover:text-red-700 font-medium">关闭</button>
          </div>
        )}

        {/* Messages */}
        <MessageList messages={messages} loading={loading || creatingSession} />
        <div ref={messagesEndRef} />

        {/* Input */}
        <ChatInput
          onSendMessage={handleSendMessage}
          loading={loading || creatingSession}
        />
      </div>
    </div>
  );
}
