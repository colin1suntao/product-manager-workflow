"use client";

import { useState, useEffect, useRef } from "react";
import { chatApi } from "@/lib/api";
import { getAccessToken } from "@/lib/auth";
import ChatSidebar from "@/components/chat/ChatSidebar";
import ChatInput from "@/components/chat/ChatInput";
import MessageList from "@/components/chat/MessageList";
import TaskModeSelector from "@/components/chat/TaskModeSelector";
import ModelSelector from "@/components/chat/ModelSelector";

interface ChatSession {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

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

export default function ChatPage() {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [sessionsLoading, setSessionsLoading] = useState(true);
  const [selectedMode, setSelectedMode] = useState<string | null>(null);
  const [selectedProvider, setSelectedProvider] = useState<string | null>(null);
  const [selectedModel, setSelectedModel] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [contextLength, setContextLength] = useState(0);
  const [contextLimit, setContextLimit] = useState(128000);
  const [compressing, setCompressing] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Load sessions on mount
  useEffect(() => {
    loadSessions();
  }, []);

  // Load messages when session changes
  useEffect(() => {
    if (activeSessionId) {
      loadMessages(activeSessionId);
    } else {
      setMessages([]);
    }
  }, [activeSessionId]);

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const loadSessions = async () => {
    try {
      setSessionsLoading(true);
      const data = await chatApi.listSessions();
      setSessions(data.sessions);
    } catch (error) {
      console.error("Failed to load sessions:", error);
      setError("加载会话列表失败");
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
      setError("加载消息失败");
    }
  };

  const handleCreateSession = async () => {
    try {
      setLoading(true);
      const session = await chatApi.createSession();
      setSessions((prev) => [session, ...prev]);
      setActiveSessionId(session.id);
    } catch (error) {
      console.error("Failed to create session:", error);
      setError("创建会话失败");
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteSession = async (sessionId: string) => {
    try {
      await chatApi.deleteSession(sessionId);
      setSessions((prev) => prev.filter((s) => s.id !== sessionId));
      if (activeSessionId === sessionId) {
        setActiveSessionId(null);
      }
    } catch (error) {
      console.error("Failed to delete session:", error);
      setError("删除会话失败");
    }
  };

  const handleCompressContext = async () => {
    if (!activeSessionId) return;
    try {
      setCompressing(true);
      const result = await chatApi.compressContext(activeSessionId);
      setContextLength(0);
      await loadMessages(activeSessionId);
      setError(`上下文已压缩，移除了 ${result.removed_count} 条旧消息`);
      setTimeout(() => setError(null), 3000);
    } catch (error) {
      console.error("Failed to compress context:", error);
      setError("压缩上下文失败");
    } finally {
      setCompressing(false);
    }
  };

  const handleSendMessage = async (content: string) => {
    if (!activeSessionId) {
      // Auto-create session if none exists
      await handleCreateSession();
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
        provider_id: selectedProvider || undefined,
        model_name: selectedModel || undefined,
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
      setError("发送消息失败，请重试");
      // Remove temp message on error
      setMessages((prev) => prev.filter((m) => !m.id.startsWith("temp-")));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex h-[calc(100vh-4rem)] bg-gray-100">
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
              {activeSessionId
                ? sessions.find((s) => s.id === activeSessionId)?.title || "会话"
                : "新建会话"}
            </h1>
            {activeSessionId && (
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
          <div className="mt-3 flex items-center gap-3">
            <div className="flex-1">
              <TaskModeSelector
                selectedMode={selectedMode}
                onSelectMode={setSelectedMode}
              />
            </div>
            <ModelSelector
              selectedModel={selectedModel}
              selectedProvider={selectedProvider}
              onSelect={(providerId, model) => {
                setSelectedProvider(providerId);
                setSelectedModel(model);
              }}
            />
          </div>
        </div>

        {/* Error Banner */}
        {error && (
          <div className="mx-4 mt-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
            {error}
            <button
              onClick={() => setError(null)}
              className="ml-2 text-red-500 hover:text-red-700"
            >
              关闭
            </button>
          </div>
        )}

        {/* Messages */}
        <MessageList messages={messages} loading={loading} />
        <div ref={messagesEndRef} />

        {/* Input */}
        <ChatInput
          onSendMessage={handleSendMessage}
          loading={loading}
        />
      </div>
    </div>
  );
}
