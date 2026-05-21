"use client";

import { useState, useEffect } from "react";
import { tokenUsageApi } from "@/lib/api";

interface DailyUsage {
  date: string;
  total_tokens: number;
  prompt_tokens: number;
  completion_tokens: number;
  call_count: number;
}

interface ModelUsage {
  model_id: string;
  total_tokens: number;
  prompt_tokens: number;
  completion_tokens: number;
  call_count: number;
  last_used_at: string | null;
}

interface UsageRecord {
  id: string;
  model_id: string;
  provider_id: string;
  source: string;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  created_at: string;
}

function formatTokens(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toString();
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function BarChart({ data, maxVal }: { data: number[]; maxVal: number }) {
  const height = 120;
  const barWidth = data.length > 0 ? Math.min(24, 280 / data.length) : 24;
  return (
    <div className="flex items-end gap-[2px]" style={{ height }}>
      {data.map((v, i) => {
        const pct = maxVal > 0 ? (v / maxVal) * 100 : 0;
        return (
          <div
            key={i}
            className="bg-blue-500 rounded-t hover:bg-blue-600 transition-colors relative group"
            style={{
              width: barWidth,
              height: `${Math.max(2, pct)}%`,
              minWidth: 4,
            }}
          >
            <div className="absolute -top-6 left-1/2 -translate-x-1/2 bg-gray-800 text-white text-[10px] px-1.5 py-0.5 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none z-10">
              {formatTokens(v)}
            </div>
          </div>
        );
      })}
    </div>
  );
}

const MODEL_COLORS = [
  "bg-blue-500",
  "bg-emerald-500",
  "bg-violet-500",
  "bg-amber-500",
  "bg-rose-500",
  "bg-cyan-500",
  "bg-orange-500",
  "bg-teal-500",
];

export default function UsagePage() {
  const [days, setDays] = useState(30);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [totalTokens, setTotalTokens] = useState(0);
  const [totalPrompt, setTotalPrompt] = useState(0);
  const [totalCompletion, setTotalCompletion] = useState(0);
  const [totalCalls, setTotalCalls] = useState(0);
  const [modelCount, setModelCount] = useState(0);
  const [dailyUsage, setDailyUsage] = useState<DailyUsage[]>([]);
  const [modelUsage, setModelUsage] = useState<ModelUsage[]>([]);
  const [records, setRecords] = useState<UsageRecord[]>([]);

  useEffect(() => {
    loadData();
  }, [days]);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await tokenUsageApi.getOverview(days);
      setTotalTokens(data.total_tokens);
      setTotalPrompt(data.total_prompt_tokens);
      setTotalCompletion(data.total_completion_tokens);
      setTotalCalls(data.total_calls);
      setModelCount(data.model_count);
      setDailyUsage(data.daily_usage);
      setModelUsage(data.model_usage);
    } catch (e) {
      setError("加载用量数据失败");
    } finally {
      setLoading(false);
    }
  };

  const loadRecords = async () => {
    try {
      const data = await tokenUsageApi.getRecords(50, 0);
      setRecords(data.records);
    } catch {}
  };

  useEffect(() => {
    loadRecords();
  }, []);

  const dailyMax = Math.max(...dailyUsage.map((d) => d.total_tokens), 1);
  const modelMax = Math.max(...modelUsage.map((m) => m.total_tokens), 1);

  return (
    <div className="max-w-6xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">模型用量</h1>
          <p className="text-sm text-gray-500 mt-1">查看系统各模型的 Token 消耗情况</p>
        </div>
        <div className="flex items-center gap-2">
          {[7, 14, 30, 90].map((d) => (
            <button
              key={d}
              onClick={() => setDays(d)}
              className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                days === d
                  ? "bg-blue-600 text-white"
                  : "bg-white border border-gray-300 text-gray-600 hover:bg-gray-50"
              }`}
            >
              {d} 天
            </button>
          ))}
        </div>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
          {error}
        </div>
      )}

      {/* Overview cards */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4 mb-6">
        <div className="bg-white rounded-lg border p-4">
          <div className="text-xs text-gray-500 mb-1">总 Token 消耗</div>
          <div className="text-2xl font-bold text-gray-900">{formatTokens(totalTokens)}</div>
        </div>
        <div className="bg-white rounded-lg border p-4">
          <div className="text-xs text-gray-500 mb-1">输入 Token</div>
          <div className="text-2xl font-bold text-blue-600">{formatTokens(totalPrompt)}</div>
        </div>
        <div className="bg-white rounded-lg border p-4">
          <div className="text-xs text-gray-500 mb-1">输出 Token</div>
          <div className="text-2xl font-bold text-emerald-600">{formatTokens(totalCompletion)}</div>
        </div>
        <div className="bg-white rounded-lg border p-4">
          <div className="text-xs text-gray-500 mb-1">总调用次数</div>
          <div className="text-2xl font-bold text-violet-600">{totalCalls.toLocaleString()}</div>
        </div>
        <div className="bg-white rounded-lg border p-4">
          <div className="text-xs text-gray-500 mb-1">使用模型数</div>
          <div className="text-2xl font-bold text-amber-600">{modelCount}</div>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          {/* Daily usage chart */}
          <div className="bg-white rounded-lg border p-5">
            <h2 className="text-sm font-semibold text-gray-900 mb-4">每日 Token 用量</h2>
            {dailyUsage.length > 0 ? (
              <>
                <BarChart
                  data={dailyUsage.map((d) => d.total_tokens)}
                  maxVal={dailyMax}
                />
                <div className="flex justify-between mt-2">
                  <span className="text-[10px] text-gray-400">
                    {dailyUsage[0]?.date?.slice(5)}
                  </span>
                  <span className="text-[10px] text-gray-400">
                    {dailyUsage[dailyUsage.length - 1]?.date?.slice(5)}
                  </span>
                </div>
                {/* Daily table */}
                <div className="mt-4 max-h-48 overflow-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="text-gray-500 border-b">
                        <th className="text-left py-1.5 font-medium">日期</th>
                        <th className="text-right py-1.5 font-medium">总 Token</th>
                        <th className="text-right py-1.5 font-medium">输入</th>
                        <th className="text-right py-1.5 font-medium">输出</th>
                        <th className="text-right py-1.5 font-medium">调用次数</th>
                      </tr>
                    </thead>
                    <tbody>
                      {[...dailyUsage].reverse().map((d) => (
                        <tr key={d.date} className="border-b border-gray-50 hover:bg-gray-50">
                          <td className="py-1.5 text-gray-700">{d.date}</td>
                          <td className="py-1.5 text-right font-medium text-gray-900">{formatTokens(d.total_tokens)}</td>
                          <td className="py-1.5 text-right text-blue-600">{formatTokens(d.prompt_tokens)}</td>
                          <td className="py-1.5 text-right text-emerald-600">{formatTokens(d.completion_tokens)}</td>
                          <td className="py-1.5 text-right text-gray-500">{d.call_count}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            ) : (
              <div className="text-center py-10 text-gray-400 text-sm">暂无数据</div>
            )}
          </div>

          {/* Model usage */}
          <div className="bg-white rounded-lg border p-5">
            <h2 className="text-sm font-semibold text-gray-900 mb-4">模型用量分布</h2>
            {modelUsage.length > 0 ? (
              <div className="space-y-4">
                {modelUsage.map((m, idx) => {
                  const pct = modelMax > 0 ? (m.total_tokens / modelMax) * 100 : 0;
                  const color = MODEL_COLORS[idx % MODEL_COLORS.length];
                  return (
                    <div key={m.model_id}>
                      <div className="flex items-center justify-between mb-1">
                        <div className="flex items-center gap-2">
                          <span className={`w-2.5 h-2.5 rounded-full ${color}`} />
                          <span className="text-sm font-medium text-gray-700 font-mono">{m.model_id}</span>
                        </div>
                        <div className="flex items-center gap-3 text-xs text-gray-500">
                          <span>{m.call_count} 次调用</span>
                          <span className="font-medium text-gray-900">{formatTokens(m.total_tokens)} tokens</span>
                        </div>
                      </div>
                      <div className="w-full h-2 bg-gray-100 rounded-full overflow-hidden">
                        <div
                          className={`h-full ${color} rounded-full transition-all`}
                          style={{ width: `${Math.max(2, pct)}%` }}
                        />
                      </div>
                      <div className="flex items-center gap-4 mt-1 text-[11px] text-gray-400">
                        <span>输入: {formatTokens(m.prompt_tokens)}</span>
                        <span>输出: {formatTokens(m.completion_tokens)}</span>
                        {m.last_used_at && (
                          <span>最近: {formatDate(m.last_used_at)}</span>
                        )}
                      </div>
                    </div>
                  );
                })}

                {/* Token composition pie-like visualization */}
                <div className="mt-4 pt-4 border-t">
                  <div className="text-xs font-medium text-gray-500 mb-2">Token 构成</div>
                  <div className="flex items-center gap-4">
                    <div className="flex-1">
                      <div className="h-4 bg-gray-100 rounded-full overflow-hidden flex">
                        {totalTokens > 0 && modelUsage.map((m, idx) => {
                          const widthPct = (m.total_tokens / totalTokens) * 100;
                          if (widthPct < 1) return null;
                          return (
                            <div
                              key={m.model_id}
                              className={`h-full ${MODEL_COLORS[idx % MODEL_COLORS.length]}`}
                              style={{ width: `${widthPct}%` }}
                              title={`${m.model_id}: ${formatTokens(m.total_tokens)}`}
                            />
                          );
                        })}
                      </div>
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-3 mt-2">
                    {modelUsage.map((m, idx) => (
                      <div key={m.model_id} className="flex items-center gap-1.5">
                        <span className={`w-2 h-2 rounded-full ${MODEL_COLORS[idx % MODEL_COLORS.length]}`} />
                        <span className="text-[11px] text-gray-500 truncate max-w-[120px]">{m.model_id}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-center py-10 text-gray-400 text-sm">暂无数据</div>
            )}
          </div>
        </div>
      )}

      {/* Recent records */}
      <div className="bg-white rounded-lg border p-5">
        <h2 className="text-sm font-semibold text-gray-900 mb-4">最近调用记录</h2>
        {records.length > 0 ? (
          <div className="overflow-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-gray-500 border-b">
                  <th className="text-left py-2 font-medium">时间</th>
                  <th className="text-left py-2 font-medium">模型</th>
                  <th className="text-left py-2 font-medium">来源</th>
                  <th className="text-right py-2 font-medium">输入</th>
                  <th className="text-right py-2 font-medium">输出</th>
                  <th className="text-right py-2 font-medium">总计</th>
                </tr>
              </thead>
              <tbody>
                {records.map((r) => (
                  <tr key={r.id} className="border-b border-gray-50 hover:bg-gray-50">
                    <td className="py-2 text-gray-600 whitespace-nowrap">{formatDate(r.created_at)}</td>
                    <td className="py-2">
                      <span className="px-1.5 py-0.5 bg-blue-50 text-blue-700 rounded font-mono text-[11px]">
                        {r.model_id}
                      </span>
                    </td>
                    <td className="py-2 text-gray-500">{r.source || "-"}</td>
                    <td className="py-2 text-right text-blue-600">{r.prompt_tokens.toLocaleString()}</td>
                    <td className="py-2 text-right text-emerald-600">{r.completion_tokens.toLocaleString()}</td>
                    <td className="py-2 text-right font-medium text-gray-900">{r.total_tokens.toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-10 text-gray-400 text-sm">暂无调用记录</div>
        )}
      </div>
    </div>
  );
}
