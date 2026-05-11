"use client";

import { useState, useEffect, useRef } from "react";

interface ProviderModel {
  provider_id: string;
  provider_name: string;
  provider_type: string;
  model: string;
  is_default: boolean;
}

interface ModelSelectorProps {
  selectedModel: string | null;
  selectedProvider: string | null;
  onSelect: (providerId: string, model: string) => void;
}

export default function ModelSelector({
  selectedModel,
  selectedProvider,
  onSelect,
}: ModelSelectorProps) {
  const [providers, setProviders] = useState<ProviderModel[]>([]);
  const [open, setOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchProviders();
  }, []);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const fetchProviders = async () => {
    try {
      const token = document.cookie
        .split("; ")
        .find((row) => row.startsWith("access_token="))
        ?.split("=")[1];
      if (!token) return;

      const res = await fetch("/api/v1/llm/providers", {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      if (data.providers) {
        const models: ProviderModel[] = [];
        for (const p of data.providers) {
          models.push({
            provider_id: p.id,
            provider_name: p.name,
            provider_type: p.provider_type,
            model: p.default_model,
            is_default: p.is_default,
          });
        }
        setProviders(models);

        // Auto-select default if nothing selected
        if (!selectedModel && models.length > 0) {
          const defaultModel = models.find((m) => m.is_default) || models[0];
          onSelect(defaultModel.provider_id, defaultModel.model);
        }
      }
    } catch (err) {
      console.error("Failed to fetch providers:", err);
    }
  };

  const currentLabel = selectedModel
    ? `${providers.find((p) => p.provider_id === selectedProvider)?.provider_name || "未知"} / ${selectedModel}`
    : "选择模型";

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 px-3 py-2 rounded-lg border border-gray-200 bg-white text-sm text-gray-700 hover:border-gray-300 hover:bg-gray-50 transition-colors"
      >
        <svg className="w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
        </svg>
        <span className="max-w-[160px] truncate">{currentLabel}</span>
        <svg className={`w-4 h-4 text-gray-400 transition-transform ${open ? "rotate-180" : ""}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {open && (
        <div className="absolute top-full left-0 mt-1 w-72 bg-white border border-gray-200 rounded-lg shadow-lg z-50 max-h-72 overflow-y-auto">
          {providers.length === 0 ? (
            <div className="p-4 text-sm text-gray-500 text-center">
              暂无可用模型，请先在供应商配置中添加
            </div>
          ) : (
            providers.map((p) => (
              <button
                key={`${p.provider_id}-${p.model}`}
                onClick={() => {
                  onSelect(p.provider_id, p.model);
                  setOpen(false);
                }}
                className={`w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-gray-50 transition-colors border-b border-gray-100 last:border-0 ${
                  selectedProvider === p.provider_id && selectedModel === p.model
                    ? "bg-blue-50"
                    : ""
                }`}
              >
                <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center flex-shrink-0">
                  <span className="text-sm font-medium text-blue-600">
                    {p.provider_name.charAt(0)}
                  </span>
                </div>
                <div className="min-w-0 flex-1">
                  <div className="text-sm font-medium text-gray-900 truncate">
                    {p.provider_name}
                  </div>
                  <div className="text-xs text-gray-500 truncate">{p.model}</div>
                </div>
                {p.is_default && (
                  <span className="text-xs text-blue-600 bg-blue-50 px-2 py-0.5 rounded-full">
                    默认
                  </span>
                )}
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
}