"""三层记忆管理器

实现:
1. Short-term Memory (STM)  - Token 预算感知的会话窗口
2. Working Memory (WM)     - 任务驱动，支持用户手动添加
3. Long-term Memory (LTM)  - 持久化 CRUD + 自动提取
"""

import asyncio
import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .layered_models import (
    LongTermCategory,
    LongTermMemoryEntry,
    MemoryLayer,
    MemoryPriority,
    MemoryRetrievalQuery,
    MemorySystemStats,
    ShortTermMemory,
    WorkingMemory,
)

logger = logging.getLogger(__name__)


class LayeredMemoryManager:
    """三层记忆管理器

    使用方式:
        manager = LayeredMemoryManager(storage_dir="./data/memory")
        manager.init_session(session_id, user_id)
        stm = manager.stm  # 短期记忆
        wm = manager.wm    # 工作记忆
        manager.store_long_term(entry)  # 持久化长期记忆
    """

    def __init__(self, storage_dir: str = "./data/memory"):
        self._storage_dir = Path(storage_dir)
        self._storage_dir.mkdir(parents=True, exist_ok=True)

        self._stm: dict[str, ShortTermMemory] = {}
        self._wm: dict[str, WorkingMemory] = {}

        self._current_session_id: str | None = None
        self._current_user_id: str | None = None

    @property
    def stm(self) -> ShortTermMemory | None:
        if self._current_session_id:
            return self._stm.get(self._current_session_id)
        return None

    @property
    def wm(self) -> WorkingMemory | None:
        if self._current_session_id:
            return self._wm.get(self._current_session_id)
        return None

    # ==================== Session 管理 ====================

    def init_session(self, session_id: str, user_id: str) -> None:
        """初始化会话的三层记忆，切换会话时自动清理旧会话"""
        # 清理旧会话防止内存泄漏
        if self._current_session_id and self._current_session_id != session_id:
            self._cleanup_session(self._current_session_id)

        self._current_session_id = session_id
        self._current_user_id = user_id

        if session_id not in self._stm:
            self._stm[session_id] = ShortTermMemory(
                session_id=session_id,
                user_id=user_id,
            )
        if session_id not in self._wm:
            self._wm[session_id] = WorkingMemory(
                session_id=session_id,
                user_id=user_id,
            )

    def _cleanup_session(self, session_id: str) -> None:
        """内部清理指定会话的 STM/WM"""
        self._stm.pop(session_id, None)
        self._wm.pop(session_id, None)

    def end_session(self, session_id: str | None = None) -> bool:
        """结束会话，清理短期和工作记忆

        Args:
            session_id: 要结束的会话 ID，None 则使用当前会话

        Returns:
            True 表示成功清理，False 表示会话不存在
        """
        sid = session_id or self._current_session_id
        if not sid:
            return False

        cleaned = False
        if sid in self._stm:
            del self._stm[sid]
            cleaned = True
        if sid in self._wm:
            del self._wm[sid]
            cleaned = True

        if sid == self._current_session_id:
            self._current_session_id = None
            self._current_user_id = None

        return cleaned

    # ==================== Short-term Memory ====================

    def add_stm_message(self, role: str, content: str) -> bool:
        """向短期记忆添加消息"""
        if not self.stm:
            raise RuntimeError("Session not initialized")
        return self.stm.add_message(role, content)

    def get_stm_context(self) -> str:
        """获取短期记忆上下文"""
        if not self.stm:
            return ""
        return self.stm.get_context_for_injection()

    # ==================== Working Memory ====================

    def load_wm_from_ltm(
        self,
        task_description: str,
        task_type: str = "",
        task_id: str | None = None,
        max_items: int = 10,
    ) -> list[LongTermMemoryEntry]:
        """从长期记忆中加载关联条目到工作记忆"""
        if not self.wm:
            raise RuntimeError("Session not initialized")

        self.wm.task_description = task_description
        self.wm.task_type = task_type
        self.wm.task_id = task_id

        # 关键词检索
        keywords = self._extract_keywords(task_description)
        results = self.search_long_term(
            MemoryRetrievalQuery(
                user_id=self._current_user_id,
                keyword=" ".join(keywords),
                max_results=max_items,
                sort_by="relevance",
            )
        )

        self.wm.loaded_from_ltm = results
        self.wm.updated_at = datetime.now(timezone.utc)
        return results

    def add_wm_entry(
        self,
        title: str,
        content: str,
        category: LongTermCategory = LongTermCategory.CUSTOM,
        tags: list[str] | None = None,
        priority: MemoryPriority = MemoryPriority.MEDIUM,
        importance: float = 0.7,
    ) -> LongTermMemoryEntry:
        """用户手动添加工作记忆条目"""
        if not self.wm:
            raise RuntimeError("Session not initialized")

        entry = LongTermMemoryEntry(
            user_id=self._current_user_id or "anonymous",
            layer=MemoryLayer.WORKING,
            category=category,
            title=title,
            content=content,
            summary=content[:200],
            tags=tags or [],
            priority=priority,
            importance=importance,
            source="user_manual",
        )
        self.wm.add_manual_entry(entry)
        return entry

    def get_wm_context(self, max_tokens: int = 2000) -> str:
        """获取工作记忆上下文"""
        if not self.wm:
            return ""
        return self.wm.get_context_for_injection(max_tokens)

    def clear_wm_task(self):
        """清除当前任务的工作记忆"""
        if self.wm:
            self.wm.clear_task()

    # ==================== Long-term Memory CRUD ====================

    def _get_ltm_file(self, user_id: str) -> Path:
        """获取长期记忆存储文件（使用哈希防路径遍历）"""
        safe_hash = hashlib.sha256(user_id.encode()).hexdigest()[:16]
        return self._storage_dir / f"ltm_{safe_hash}.json"

    def _load_ltm(self, user_id: str) -> list[dict[str, Any]]:
        """加载长期记忆"""
        filepath = self._get_ltm_file(user_id)
        if not filepath.exists():
            return []
        try:
            return json.loads(filepath.read_text())
        except json.JSONDecodeError:
            logger.error("LTM file corrupted for user %s: %s", user_id[:8], filepath)
            return []
        except IOError as e:
            logger.error("LTM file read error for user %s: %s", user_id[:8], e)
            return []

    def _save_ltm(self, user_id: str, data: list[dict[str, Any]]):
        """保存长期记忆（原子写入：先写临时文件再 rename）"""
        filepath = self._get_ltm_file(user_id)
        tmp_path = filepath.with_suffix(filepath.suffix + ".tmp")
        try:
            tmp_path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2, default=str)
            )
            os.replace(tmp_path, filepath)
        except IOError as e:
            logger.error("LTM file write error for user %s: %s", user_id[:8], e)
            raise

    def store_long_term(self, entry: LongTermMemoryEntry) -> LongTermMemoryEntry:
        """存储长期记忆条目（创建或更新）"""
        data = self._load_ltm(entry.user_id)

        # 查找已有条目
        existing_idx = None
        for i, item in enumerate(data):
            if item.get("id") == entry.id:
                existing_idx = i
                break

        entry.layer = MemoryLayer.LONG_TERM
        entry.updated_at = datetime.now(timezone.utc)
        entry_dict = entry.model_dump(mode="json")

        if existing_idx is not None:
            data[existing_idx] = entry_dict
        else:
            data.append(entry_dict)

        self._save_ltm(entry.user_id, data)
        return entry

    def get_long_term(self, user_id: str, memory_id: str) -> LongTermMemoryEntry | None:
        """获取单个长期记忆条目"""
        data = self._load_ltm(user_id)
        for i, item in enumerate(data):
            if item.get("id") == memory_id:
                entry = LongTermMemoryEntry(**item)
                entry.update_access()
                data[i] = entry.model_dump(mode="json")
                self._save_ltm(user_id, data)
                return entry
        return None

    def update_long_term(
        self,
        memory_id: str,
        user_id: str | None = None,
        **updates,
    ) -> LongTermMemoryEntry | None:
        """更新长期记忆条目（用户自定义）"""
        uid = user_id or self._current_user_id
        if not uid:
            raise RuntimeError("No user_id available")

        entry = self.get_long_term(uid, memory_id)
        if not entry:
            return None

        # 允许更新的字段
        allowed_fields = {
            "title",
            "content",
            "summary",
            "tags",
            "category",
            "priority",
            "importance",
            "confidence",
            "context",
            "related_files",
        }
        for key, value in updates.items():
            if key in allowed_fields and value is not None:
                setattr(entry, key, value)

        entry.updated_at = datetime.now(timezone.utc)
        entry.layer = MemoryLayer.LONG_TERM
        return self.store_long_term(entry)

    def delete_long_term(self, user_id: str, memory_id: str) -> bool:
        """删除长期记忆条目（用户可操作）"""
        data = self._load_ltm(user_id)
        original_len = len(data)
        data = [item for item in data if item.get("id") != memory_id]
        if len(data) < original_len:
            self._save_ltm(user_id, data)
            return True
        return False

    def list_long_term(
        self,
        user_id: str,
        category: LongTermCategory | None = None,
        tags: list[str] | None = None,
        priority: MemoryPriority | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[LongTermMemoryEntry], int]:
        """列出长期记忆条目（分页）"""
        data = self._load_ltm(user_id)
        entries: list[LongTermMemoryEntry] = []

        for item in data:
            entry = LongTermMemoryEntry(**item)

            if category and entry.category != category:
                continue
            if priority and entry.priority != priority:
                continue
            if tags:
                if not any(t in entry.tags for t in tags):
                    continue

            entries.append(entry)

        total = len(entries)
        start = (page - 1) * page_size
        end = start + page_size
        return entries[start:end], total

    def search_long_term(
        self, query: MemoryRetrievalQuery, track_access: bool = True
    ) -> list[LongTermMemoryEntry]:
        """搜索长期记忆

        Args:
            query: 检索查询参数
            track_access: 是否更新访问计数（纯读场景设为 False）
        """
        uid = query.user_id or self._current_user_id
        if not uid:
            return []

        data = self._load_ltm(uid)
        scored_entries: list[tuple[float, LongTermMemoryEntry]] = []

        keywords = query.keyword.lower().split() if query.keyword else []

        for item in data:
            entry = LongTermMemoryEntry(**item)

            # 过滤条件
            if query.categories and entry.category not in query.categories:
                continue
            if query.tags:
                if not any(t in entry.tags for t in query.tags):
                    continue
            if entry.importance < query.min_importance:
                continue
            if query.priority and entry.priority != query.priority:
                continue
            if query.time_range_start:
                if entry.created_at < query.time_range_start:
                    continue
            if query.time_range_end:
                if entry.created_at > query.time_range_end:
                    continue

            # 相关性评分
            score = 0.0
            matched = not keywords  # 无关键词时全部匹配
            if keywords:
                content_lower = (
                    entry.title + " " + entry.content + " " + " ".join(entry.tags)
                ).lower()
                for kw in keywords:
                    if kw in content_lower:
                        score += 1.0 / (len(keywords) or 1)
                        matched = True

            # 跳过无关键词匹配的条目
            if not matched:
                continue

            # 结合重要性
            if query.sort_by == "importance":
                score = entry.importance
            elif query.sort_by == "recency":
                dt = entry.last_accessed
                score = dt.timestamp()
            # relevance - 默认使用关键词匹配得分加权重要性
            else:
                score = score * 0.6 + entry.importance * 0.4

            scored_entries.append((score, entry))

        scored_entries.sort(key=lambda x: x[0], reverse=True)
        results = [e for _, e in scored_entries[: query.max_results]]

        # 批量更新访问记录（一次读写，避免 N 次 IO）
        if track_access and results:
            data_index: dict[str, int] = {
                item.get("id", ""): i for i, item in enumerate(data)
            }
            for entry in results:
                entry.update_access()
                idx = data_index.get(entry.id)
                if idx is not None:
                    data[idx] = entry.model_dump(mode="json")
            self._save_ltm(uid, data)

        return results

    # ==================== 记忆注入（组合三层） ====================

    def get_full_injection_context(self, max_tokens: int = 4000) -> str:
        """组合三层记忆为完整注入上下文"""
        parts = []

        # 1. 短期记忆（最近对话）
        stm_ctx = self.get_stm_context()
        if stm_ctx:
            parts.append(f"## 短期记忆\n{stm_ctx}")

        # 2. 工作记忆（任务相关）
        wm_ctx = self.get_wm_context(max_tokens=max_tokens // 2)
        if wm_ctx:
            parts.append(f"## 工作记忆\n{wm_ctx}")

        # 3. 长期记忆（高优先级条目）
        if self._current_user_id:
            ltm = self.search_long_term(
                MemoryRetrievalQuery(
                    user_id=self._current_user_id,
                    priority=MemoryPriority.CRITICAL,
                    max_results=5,
                ),
                track_access=False,
            )
            if ltm:
                ltm_text = "\n".join(
                    f"- [{e.category.value}] {e.title}: {e.content[:150]}"
                    for e in ltm
                )
                parts.append(f"## 关键长期记忆\n{ltm_text}")

        return "\n\n".join(parts)

    # ==================== 统计 ====================

    def get_stats(self) -> MemorySystemStats:
        """获取记忆系统统计"""
        stats = MemorySystemStats()

        # 短期记忆统计
        stm_count = len(self._stm)
        stm_tokens = sum(s.current_tokens for s in self._stm.values())
        stats.by_layer["short_term"] = stm_count
        stats.total_tokens_stm = stm_tokens

        # 工作记忆统计
        wm_count = len(self._wm)
        stats.by_layer["working"] = wm_count

        # 长期记忆统计
        if self._current_user_id:
            data = self._load_ltm(self._current_user_id)
            stats.by_layer["long_term"] = len(data)
            stats.total_memories = stm_count + wm_count + len(data)

            # 分类统计
            category_counts: dict[str, int] = {}
            priority_counts: dict[str, int] = {}
            importance_sum = 0.0
            manual_count = 0
            tag_counts: dict[str, int] = {}
            access_list: list[dict[str, Any]] = []

            for item in data:
                cat = item.get("category", "unknown")
                category_counts[cat] = category_counts.get(cat, 0) + 1

                pri = item.get("priority", "medium")
                priority_counts[pri] = priority_counts.get(pri, 0) + 1

                importance_sum += item.get("importance", 0.5)

                if item.get("source") == "user_manual":
                    manual_count += 1

                for tag in item.get("tags", []):
                    tag_counts[tag] = tag_counts.get(tag, 0) + 1

                access_list.append({
                    "id": item.get("id"),
                    "title": item.get("title", ""),
                    "access_count": item.get("access_count", 0),
                })

            stats.by_category = category_counts
            stats.by_priority = priority_counts
            if len(data) > 0:
                stats.avg_importance = importance_sum / len(data)
            stats.total_manual_entries = manual_count

            # 最多访问
            access_list.sort(key=lambda x: x["access_count"], reverse=True)
            stats.most_accessed = access_list[:5]

            # 热门标签
            sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)
            stats.top_tags = sorted_tags[:10]

            # 存储大小
            filepath = self._get_ltm_file(self._current_user_id)
            if filepath.exists():
                stats.storage_size_bytes = filepath.stat().st_size

        stats.last_updated = datetime.now(timezone.utc)
        return stats

    # ==================== 自动提取辅助 ====================

    @staticmethod
    def _extract_keywords(text: str, max_keywords: int = 5) -> list[str]:
        """简单关键词提取（实际可用 LLM 或 TF-IDF）"""
        stop_words = {
            "的", "是", "在", "了", "和", "与", "或", "这", "那", "我", "你", "他",
            "the", "is", "are", "was", "were", "a", "an", "and", "or", "of",
            "to", "in", "for", "on", "with", "this", "that",
        }
        words = [w.lower() for w in text.split() if len(w) > 2 and w.lower() not in stop_words]
        word_freq: dict[str, int] = {}
        for w in words:
            word_freq[w] = word_freq.get(w, 0) + 1
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [w for w, _ in sorted_words[:max_keywords]]

    def auto_store_from_feedback(
        self,
        content: str,
        category: LongTermCategory = LongTermCategory.USER,
        importance: float = 0.5,
    ) -> LongTermMemoryEntry | None:
        """从用户反馈自动存储为长期记忆"""
        if not self._current_user_id:
            return None

        entry = LongTermMemoryEntry(
            user_id=self._current_user_id,
            category=category,
            title=content[:100],
            content=content,
            summary=content[:200],
            tags=self._extract_keywords(content),
            priority=MemoryPriority.MEDIUM,
            importance=importance,
            source="auto_feedback",
        )
        return self.store_long_term(entry)

    def promote_to_long_term(self, wm_entry: LongTermMemoryEntry) -> LongTermMemoryEntry:
        """将工作记忆条目提升为长期记忆"""
        wm_entry.layer = MemoryLayer.LONG_TERM
        return self.store_long_term(wm_entry)


_layered_manager: LayeredMemoryManager | None = None


def get_layered_memory_manager(storage_dir: str = "./data/memory") -> LayeredMemoryManager:
    """获取单例三层记忆管理器"""
    global _layered_manager
    if _layered_manager is None:
        _layered_manager = LayeredMemoryManager(storage_dir=storage_dir)
    return _layered_manager
