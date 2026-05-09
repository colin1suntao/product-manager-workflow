"use client";

import { useState, useEffect } from "react";

interface ChatSession {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

interface ChatSidebarProps {
  sessions: ChatSession[];
  activeSessionId: string | null;
  onSelectSession: (sessionId: string) => void;
  onCreateSession: () => void;
  onDeleteSession: (sessionId: string) => void;
  loading?: boolean;
}

export default function ChatSidebar({
  sessions,
  activeSessionId,
  onSelectSession,
  onCreateSession,
  onDeleteSession,
  loading = false,
}: ChatSidebarProps) {
  return (
    <div className="w-64 bg-gray-50 border-r flex flex-col h-full">
      {/* Header */}
      <div className="p-3 border-b">
        <button
          onClick={onCreateSession}
          disabled={loading}
          className="w-full px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center justify-center gap-2"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          新建会话
        </button>
      </div>

      {/* Session List */}
      <div className="flex-1 overflow-auto">
        {sessions.length === 0 ? (
          <div className="p-4 text-center text-gray-500 text-sm">
            暂无会话，点击上方按钮创建
          </div>
        ) : (
          <ul className="p-2 space-y-1">
            {sessions.map((session) => (
              <li key={session.id}>
                <div
                  className={`group flex items-center gap-2 px-3 py-2 rounded-lg cursor-pointer transition-colors ${
                    activeSessionId === session.id
                      ? "bg-blue-100 text-blue-700"
                      : "hover:bg-gray-100 text-gray-700"
                  }`}
                  onClick={() => onSelectSession(session.id)}
                >
                  <svg className="w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                  </svg>
                  <span className="flex-1 truncate text-sm">{session.title}</span>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onDeleteSession(session.id);
                    }}
                    className="opacity-0 group-hover:opacity-100 p-1 hover:bg-red-100 hover:text-red-600 rounded transition-opacity"
                    title="删除会话"
                  >
                    <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
