"use client";

import { useState, useRef, useEffect } from "react";

interface ChatInputProps {
  onSendMessage: (content: string) => void;
  loading?: boolean;
  disabled?: boolean;
}

const QUICK_PROMPTS = [
  "帮我分析用户登录功能的需求",
  "生成一个电商首页的原型",
  "撰写用户管理模块的 PRD",
  "分析智能家居市场的竞争格局",
];

export default function ChatInput({
  onSendMessage,
  loading = false,
  disabled = false,
}: ChatInputProps) {
  const [content, setContent] = useState("");
  const [showSuggestions, setShowSuggestions] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 150)}px`;
    }
  }, [content]);

  const handleSubmit = () => {
    const trimmed = content.trim();
    if (!trimmed || loading || disabled) return;

    onSendMessage(trimmed);
    setContent("");
    setShowSuggestions(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleQuickPrompt = (prompt: string) => {
    setContent(prompt);
    setShowSuggestions(false);
    textareaRef.current?.focus();
  };

  return (
    <div className="border-t bg-white p-4">
      {/* Quick Suggestions */}
      {showSuggestions && content === "" && (
        <div className="mb-3 p-3 bg-gray-50 rounded-lg">
          <div className="text-xs font-medium text-gray-500 mb-2">快速开始：</div>
          <div className="flex flex-wrap gap-2">
            {QUICK_PROMPTS.map((prompt, idx) => (
              <button
                key={idx}
                onClick={() => handleQuickPrompt(prompt)}
                className="px-3 py-1.5 bg-white border border-gray-200 rounded-full text-sm text-gray-600 hover:border-blue-300 hover:text-blue-600 transition-colors"
              >
                {prompt}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Input Area */}
      <div className="flex items-end gap-2">
        <div className="flex-1 relative">
          <textarea
            ref={textareaRef}
            value={content}
            onChange={(e) => setContent(e.target.value)}
            onKeyDown={handleKeyDown}
            onFocus={() => setShowSuggestions(true)}
            onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
            placeholder="描述您的需求，或选择一个任务模式..."
            disabled={disabled}
            rows={1}
            className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none disabled:opacity-50 disabled:cursor-not-allowed"
          />
        </div>
        <button
          onClick={handleSubmit}
          disabled={!content.trim() || loading || disabled}
          className="px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {loading ? (
            <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
          ) : (
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
            </svg>
          )}
        </button>
      </div>

      {/* Hint */}
      <div className="mt-2 text-xs text-gray-400">
        按 Enter 发送，Shift + Enter 换行
      </div>
    </div>
  );
}
