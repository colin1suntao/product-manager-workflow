"""Token 用量追踪模型与存储"""

import threading
from datetime import datetime

from pydantic import BaseModel, Field


class TokenUsageRecord(BaseModel):
    id: str = Field(default_factory=lambda: __import__("uuid").uuid4().hex)
    model_id: str
    provider_id: str = ""
    source: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    created_at: datetime = Field(default_factory=datetime.now)


class DailyUsage(BaseModel):
    date: str
    total_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    call_count: int = 0


class ModelUsage(BaseModel):
    model_id: str
    total_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    call_count: int = 0
    last_used_at: str | None = None


class UsageOverview(BaseModel):
    total_tokens: int = 0
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_calls: int = 0
    model_count: int = 0
    daily_usage: list[DailyUsage] = []
    model_usage: list[ModelUsage] = []


class TokenUsageStore:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._records: list[TokenUsageRecord] = []
            return cls._instance

    def record(
        self,
        model_id: str,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        total_tokens: int = 0,
        provider_id: str = "",
        source: str = "",
    ) -> TokenUsageRecord:
        r = TokenUsageRecord(
            model_id=model_id,
            provider_id=provider_id,
            source=source,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens or (prompt_tokens + completion_tokens),
        )
        self._records.append(r)
        return r

    def get_overview(self, days: int = 30) -> UsageOverview:
        now = datetime.now()
        cutoff = now.replace(hour=0, minute=0, second=0, microsecond=0)
        from datetime import timedelta
        cutoff = cutoff - timedelta(days=days - 1)

        filtered = [r for r in self._records if r.created_at >= cutoff]

        total_tokens = sum(r.total_tokens for r in filtered)
        total_prompt = sum(r.prompt_tokens for r in filtered)
        total_completion = sum(r.completion_tokens for r in filtered)

        # Daily aggregation
        daily_map: dict[str, DailyUsage] = {}
        for r in filtered:
            d = r.created_at.strftime("%Y-%m-%d")
            if d not in daily_map:
                daily_map[d] = DailyUsage(date=d)
            daily_map[d].total_tokens += r.total_tokens
            daily_map[d].prompt_tokens += r.prompt_tokens
            daily_map[d].completion_tokens += r.completion_tokens
            daily_map[d].call_count += 1

        daily_list = sorted(daily_map.values(), key=lambda x: x.date)

        # Model aggregation
        model_map: dict[str, ModelUsage] = {}
        for r in filtered:
            mid = r.model_id
            if mid not in model_map:
                model_map[mid] = ModelUsage(model_id=mid)
            model_map[mid].total_tokens += r.total_tokens
            model_map[mid].prompt_tokens += r.prompt_tokens
            model_map[mid].completion_tokens += r.completion_tokens
            model_map[mid].call_count += 1
            model_map[mid].last_used_at = r.created_at.isoformat()

        model_list = sorted(model_map.values(), key=lambda x: x.total_tokens, reverse=True)

        return UsageOverview(
            total_tokens=total_tokens,
            total_prompt_tokens=total_prompt,
            total_completion_tokens=total_completion,
            total_calls=len(filtered),
            model_count=len(model_map),
            daily_usage=daily_list,
            model_usage=model_list,
        )

    def get_records(self, limit: int = 100, offset: int = 0) -> list[TokenUsageRecord]:
        return list(reversed(self._records))[offset : offset + limit]
