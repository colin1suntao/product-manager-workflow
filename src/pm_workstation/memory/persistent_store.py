"""Persistent Memory Store - 持久化记忆存储

将记忆持久化到文件系统，支持项目级、会话级、用户级记忆。
"""

import gzip
import hashlib
import json
import logging
import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path

from .persistent_models import (
    MemoryLevel,
    MemorySearchResult,
    MemoryStats,
    PersistentMemoryEntry,
    ProjectMemory,
    SessionMemory,
    UserPreference,
)

logger = logging.getLogger(__name__)


class PersistentMemoryStore:
    """持久化记忆存储

    将记忆存储到 .monkeycode/ 目录：
    - users/{user_id}/preferences/ - 用户偏好
    - projects/{project_id}/memory/ - 项目记忆
    - sessions/{session_id}/memory/ - 会话记忆
    - archived/ - 归档记忆

    支持原子写入、自动索引、去重检查。
    """

    DEFAULT_BASE_PATH = ".monkeycode"
    DEFAULT_CACHE_SIZE = 1000

    def __init__(
        self,
        base_path: str | None = None,
        cache_size: int | None = None,
    ):
        self.base_path = Path(base_path or self.DEFAULT_BASE_PATH)
        self.cache_size = cache_size or self.DEFAULT_CACHE_SIZE

        self._cache: dict[str, PersistentMemoryEntry] = {}
        self._user_preferences: dict[str, list[UserPreference]] = {}
        self._project_memories: dict[str, list[ProjectMemory]] = {}
        self._session_memories: dict[str, list[SessionMemory]] = {}

        self._keyword_index: dict[str, list[str]] = {}
        self._hash_index: dict[str, str] = {}

        self._initialized = False

    async def initialize(self) -> None:
        """初始化存储，加载所有记忆"""
        if self._initialized:
            return

        self.base_path.mkdir(parents=True, exist_ok=True)

        (self.base_path / "users").mkdir(exist_ok=True)
        (self.base_path / "projects").mkdir(exist_ok=True)
        (self.base_path / "sessions").mkdir(exist_ok=True)
        (self.base_path / "archived").mkdir(exist_ok=True)
        (self.base_path / "global").mkdir(exist_ok=True)

        await self.load_all()
        await self.rebuild_indexes()

        self._initialized = True
        logger.info(f"PersistentMemoryStore initialized at {self.base_path}")

    async def load_all(self) -> None:
        """加载所有记忆到缓存"""
        await self._load_user_preferences()
        await self._load_project_memories()
        await self._load_session_memories()

        logger.info(f"Loaded {len(self._cache)} memories into cache")

    async def _load_user_preferences(self) -> None:
        """加载用户偏好"""
        users_dir = self.base_path / "users"

        for user_dir in users_dir.iterdir():
            if not user_dir.is_dir():
                continue

            user_id = user_dir.name
            prefs_dir = user_dir / "preferences"

            if not prefs_dir.exists():
                continue

            preferences = []
            for pref_file in prefs_dir.glob("*.json"):
                if pref_file.name == "preferences_index.json":
                    continue

                try:
                    with open(pref_file, encoding="utf-8") as f:
                        data = json.load(f)

                    if isinstance(data, dict) and "preferences" in data:
                        for pref in data["preferences"]:
                            pref_obj = UserPreference.model_validate(pref)
                            pref_obj.file_path = str(pref_file)
                            preferences.append(pref_obj)
                    elif isinstance(data, list):
                        for pref in data:
                            pref_obj = UserPreference.model_validate(pref)
                            pref_obj.file_path = str(pref_file)
                            preferences.append(pref_obj)

                except (json.JSONDecodeError, Exception) as e:
                    logger.warning(f"Failed to load preference file {pref_file}: {e}")

            self._user_preferences[user_id] = preferences

    async def _load_project_memories(self) -> None:
        """加载项目记忆"""
        projects_dir = self.base_path / "projects"

        for project_dir in projects_dir.iterdir():
            if not project_dir.is_dir():
                continue

            project_id = project_dir.name
            memory_dir = project_dir / "memory"

            if not memory_dir.exists():
                continue

            memories = []
            for memory_file in memory_dir.glob("*.json"):
                if memory_file.name == "memory_index.json":
                    continue

                try:
                    with open(memory_file, encoding="utf-8") as f:
                        data = json.load(f)

                    if isinstance(data, dict) and "memories" in data:
                        for mem in data["memories"]:
                            mem_obj = ProjectMemory.model_validate(mem)
                            mem_obj.file_path = str(memory_file)
                            memories.append(mem_obj)

                except (json.JSONDecodeError, Exception) as e:
                    logger.warning(f"Failed to load project memory {memory_file}: {e}")

            self._project_memories[project_id] = memories

    async def _load_session_memories(self) -> None:
        """加载会话记忆"""
        sessions_dir = self.base_path / "sessions"

        for session_dir in sessions_dir.iterdir():
            if not session_dir.is_dir():
                continue

            session_id = session_dir.name
            memory_dir = session_dir / "memory"

            if not memory_dir.exists():
                continue

            memories = []
            for memory_file in memory_dir.glob("*.json"):
                if memory_file.name == "session_index.json":
                    continue

                try:
                    with open(memory_file, encoding="utf-8") as f:
                        data = json.load(f)

                    if isinstance(data, dict) and "memories" in data:
                        for mem in data["memories"]:
                            mem_obj = SessionMemory.model_validate(mem)
                            mem_obj.file_path = str(memory_file)
                            memories.append(mem_obj)

                except (json.JSONDecodeError, Exception) as e:
                    logger.warning(f"Failed to load session memory {memory_file}: {e}")

            self._session_memories[session_id] = memories

    async def rebuild_indexes(self) -> None:
        """重建索引"""
        self._keyword_index.clear()
        self._hash_index.clear()

        for memory in self._cache.values():
            for keyword in memory.keywords:
                if keyword not in self._keyword_index:
                    self._keyword_index[keyword] = []
                self._keyword_index[keyword].append(memory.id)

            hash_key = memory.content_hash or memory.compute_hash()
            self._hash_index[hash_key] = memory.id

        logger.info(f"Rebuilt indexes: {len(self._keyword_index)} keywords, {len(self._hash_index)} hashes")

    async def save(
        self,
        memory: PersistentMemoryEntry,
    ) -> PersistentMemoryEntry:
        """保存记忆"""
        if not self._initialized:
            await self.initialize()

        memory.content_hash = memory.compute_hash()
        memory.updated_at = datetime.now()

        file_path = self._get_file_path(memory)

        self._atomic_write(file_path, memory.model_dump())

        memory.file_path = str(file_path)

        self._cache[memory.id] = memory

        for keyword in memory.keywords:
            if keyword not in self._keyword_index:
                self._keyword_index[keyword] = []
            if memory.id not in self._keyword_index[keyword]:
                self._keyword_index[keyword].append(memory.id)

        self._hash_index[memory.content_hash] = memory.id

        logger.debug(f"Saved memory {memory.id} to {file_path}")

        return memory

    async def save_user_preference(
        self,
        preference: UserPreference,
    ) -> UserPreference:
        """保存用户偏好"""
        if not self._initialized:
            await self.initialize()

        preference.updated_at = datetime.now()

        user_dir = self.base_path / "users" / preference.user_id
        prefs_dir = user_dir / "preferences"
        prefs_dir.mkdir(parents=True, exist_ok=True)

        file_path = prefs_dir / f"{preference.category.value}.json"

        existing_prefs = self._user_preferences.get(preference.user_id, [])

        {p.category: p for p in existing_prefs}

        if preference.key in [p.key for p in existing_prefs if p.category == preference.category]:
            existing_prefs = [
                p if p.key != preference.key or p.category != preference.category
                else preference
                for p in existing_prefs
            ]
        else:
            existing_prefs.append(preference)

        data = {
            "user_id": preference.user_id,
            "preferences": [p.model_dump() for p in existing_prefs],
            "version": 1,
            "last_updated": datetime.now().isoformat(),
        }

        self._atomic_write(file_path, data)

        preference.file_path = str(file_path)

        self._user_preferences[preference.user_id] = existing_prefs

        logger.debug(f"Saved preference {preference.key} for user {preference.user_id}")

        return preference

    async def save_project_memory(
        self,
        memory: ProjectMemory,
    ) -> ProjectMemory:
        """保存项目记忆"""
        if not self._initialized:
            await self.initialize()

        memory.updated_at = datetime.now()

        project_dir = self.base_path / "projects" / memory.project_id
        memory_dir = project_dir / "memory"
        memory_dir.mkdir(parents=True, exist_ok=True)

        file_path = memory_dir / f"{memory.memory_type.value}.json"

        existing_memories = self._project_memories.get(memory.project_id, [])

        existing_memories.append(memory)

        data = {
            "project_id": memory.project_id,
            "memories": [m.model_dump() for m in existing_memories],
            "version": 1,
        }

        self._atomic_write(file_path, data)

        memory.file_path = str(file_path)

        self._project_memories[memory.project_id] = existing_memories

        logger.debug(f"Saved project memory {memory.title} for project {memory.project_id}")

        return memory

    async def save_session_memory(
        self,
        memory: SessionMemory,
    ) -> SessionMemory:
        """保存会话记忆"""
        if not self._initialized:
            await self.initialize()

        session_dir = self.base_path / "sessions" / memory.session_id
        memory_dir = session_dir / "memory"
        memory_dir.mkdir(parents=True, exist_ok=True)

        file_path = memory_dir / f"{memory.memory_type.value}.json"

        existing_memories = self._session_memories.get(memory.session_id, [])

        existing_memories.append(memory)

        data = {
            "session_id": memory.session_id,
            "memories": [m.model_dump() for m in existing_memories],
            "version": 1,
        }

        self._atomic_write(file_path, data)

        memory.file_path = str(file_path)

        self._session_memories[memory.session_id] = existing_memories

        logger.debug(f"Saved session memory for session {memory.session_id}")

        return memory

    def _get_file_path(
        self,
        memory: PersistentMemoryEntry,
    ) -> Path:
        """获取记忆文件路径"""
        if memory.level == MemoryLevel.USER:
            user_dir = self.base_path / "users" / memory.user_id
            return user_dir / "memory" / f"{memory.memory_type}_{memory.id[:8]}.json"

        elif memory.level == MemoryLevel.PROJECT:
            project_id = memory.project_id or "default"
            project_dir = self.base_path / "projects" / project_id
            return project_dir / "memory" / f"{memory.memory_type}_{memory.id[:8]}.json"

        elif memory.level == MemoryLevel.SESSION:
            session_id = memory.session_id or "default"
            session_dir = self.base_path / "sessions" / session_id
            return session_dir / "memory" / f"{memory.memory_type}_{memory.id[:8]}.json"

        else:
            return self.base_path / "global" / f"{memory.id}.json"

    def _atomic_write(
        self,
        file_path: Path,
        data: dict,
    ) -> None:
        """原子写入"""
        file_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = file_path.with_suffix(".tmp")

        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)

            shutil.move(str(temp_path), str(file_path))

        except Exception as e:
            if temp_path.exists():
                temp_path.unlink()
            raise e

    async def get(
        self,
        memory_id: str,
    ) -> PersistentMemoryEntry | None:
        """获取记忆"""
        memory = self._cache.get(memory_id)

        if memory:
            memory.update_access()

        return memory

    async def update(
        self,
        memory_id: str,
        updates: dict,
    ) -> PersistentMemoryEntry | None:
        """更新记忆"""
        memory = self._cache.get(memory_id)

        if not memory:
            return None

        for key, value in updates.items():
            if hasattr(memory, key):
                setattr(memory, key, value)

        memory.updated_at = datetime.now()

        file_path = Path(memory.file_path) if memory.file_path else self._get_file_path(memory)
        self._atomic_write(file_path, memory.model_dump())

        return memory

    async def delete(
        self,
        memory_id: str,
    ) -> bool:
        """删除记忆"""
        memory = self._cache.get(memory_id)

        if not memory:
            return False

        if memory.file_path and os.path.exists(memory.file_path):
            try:
                os.remove(memory.file_path)
            except Exception as e:
                logger.warning(f"Failed to delete memory file: {e}")

        self._cache.pop(memory_id, None)

        for keyword in memory.keywords:
            if keyword in self._keyword_index:
                self._keyword_index[keyword] = [
                    id for id in self._keyword_index[keyword] if id != memory_id
                ]

        self._hash_index.pop(memory.content_hash, None)

        return True

    async def search(
        self,
        query: str,
        user_id: str,
        project_id: str | None = None,
        session_id: str | None = None,
        limit: int = 20,
    ) -> list[MemorySearchResult]:
        """搜索记忆"""
        keywords = self._extract_keywords(query)

        matching_ids = set()
        for keyword in keywords:
            if keyword in self._keyword_index:
                matching_ids.update(self._keyword_index[keyword])

        results = []
        for memory_id in matching_ids:
            memory = self._cache.get(memory_id)

            if not memory:
                continue

            if memory.user_id != user_id:
                continue

            if project_id and memory.project_id != project_id:
                continue

            if session_id and memory.session_id != session_id:
                continue

            relevance = self._compute_relevance(memory, keywords)

            results.append(MemorySearchResult(
                memory=memory,
                relevance_score=relevance,
                match_reason=f"Matched keywords: {keywords}",
                matched_keywords=keywords,
            ))

        results.sort(key=lambda r: r.relevance_score, reverse=True)

        return results[:limit]

    async def search_similar(
        self,
        content: str,
        user_id: str,
        threshold: float = 0.8,
    ) -> PersistentMemoryEntry | None:
        """搜索相似记忆"""
        content_hash = hashlib.md5(content.strip().lower().encode()).hexdigest()

        if content_hash in self._hash_index:
            memory_id = self._hash_index[content_hash]
            memory = self._cache.get(memory_id)

            if memory and memory.user_id == user_id:
                return memory

        return None

    async def list_by_level(
        self,
        level: MemoryLevel,
        user_id: str,
        project_id: str | None = None,
        session_id: str | None = None,
        limit: int = 100,
    ) -> list[PersistentMemoryEntry]:
        """按层级列出记忆"""
        memories = [
            m for m in self._cache.values()
            if m.level == level and m.user_id == user_id
        ]

        if project_id:
            memories = [m for m in memories if m.project_id == project_id]

        if session_id:
            memories = [m for m in memories if m.session_id == session_id]

        memories.sort(key=lambda m: m.importance, reverse=True)

        return memories[:limit]

    async def get_user_preferences(
        self,
        user_id: str,
        category: str | None = None,
    ) -> list[UserPreference]:
        """获取用户偏好"""
        preferences = self._user_preferences.get(user_id, [])

        if category:
            preferences = [p for p in preferences if p.category.value == category]

        return preferences

    async def get_project_memories(
        self,
        project_id: str,
        memory_type: str | None = None,
    ) -> list[ProjectMemory]:
        """获取项目记忆"""
        memories = self._project_memories.get(project_id, [])

        if memory_type:
            memories = [m for m in memories if m.memory_type.value == memory_type]

        return memories

    async def get_session_memories(
        self,
        session_id: str,
    ) -> list[SessionMemory]:
        """获取会话记忆"""
        return self._session_memories.get(session_id, [])

    async def archive_old(
        self,
        max_age_days: int = 30,
        min_access_count: int = 1,
    ) -> int:
        """归档旧记忆"""
        now = datetime.now()
        threshold = now - timedelta(days=max_age_days)

        archived_count = 0

        for session_id, memories in list(self._session_memories.items()):
            old_memories = [
                m for m in memories
                if m.created_at < threshold and m.importance < 0.5
            ]

            if old_memories:
                archive_path = self.base_path / "archived" / now.strftime("%Y%m") / f"session_{session_id}.json.gz"
                archive_path.parent.mkdir(parents=True, exist_ok=True)

                with gzip.open(archive_path, "wt", encoding="utf-8") as f:
                    json.dump([m.model_dump() for m in old_memories], f)

                memories = [m for m in memories if m not in old_memories]
                self._session_memories[session_id] = memories

                archived_count += len(old_memories)

        logger.info(f"Archived {archived_count} old memories")

        return archived_count

    async def get_stats(
        self,
        user_id: str | None = None,
    ) -> MemoryStats:
        """获取记忆统计"""
        stats = MemoryStats()

        stats.total_memories = len(self._cache)
        stats.total_preferences = sum(len(p) for p in self._user_preferences.values())
        stats.total_project_memories = sum(len(m) for m in self._project_memories.values())
        stats.total_session_memories = sum(len(m) for m in self._session_memories.values())

        for memory in self._cache.values():
            level_key = memory.level.value
            stats.by_level[level_key] = stats.by_level.get(level_key, 0) + 1

            type_key = memory.memory_type
            stats.by_type[type_key] = stats.by_type.get(type_key, 0) + 1

        stats.last_updated = datetime.now()

        return stats

    def _extract_keywords(
        self,
        text: str,
    ) -> list[str]:
        """提取关键词"""
        keywords = []

        words = text.lower().split()

        for word in words:
            if len(word) >= 3:
                keywords.append(word)

        return keywords[:10]

    def _compute_relevance(
        self,
        memory: PersistentMemoryEntry,
        keywords: list[str],
    ) -> float:
        """计算相关性"""
        matched_count = sum(
            1 for k in keywords if k in memory.keywords or k in memory.content.lower()
        )

        keyword_score = matched_count / len(keywords) if keywords else 0

        importance_score = memory.importance

        access_score = min(memory.access_count / 10, 1) * 0.1

        relevance = (keyword_score * 0.6 + importance_score * 0.3 + access_score * 0.1)

        return min(relevance, 1.0)


_global_store: PersistentMemoryStore | None = None


def get_persistent_memory_store() -> PersistentMemoryStore:
    """获取全局持久化记忆存储实例"""
    global _global_store
    if _global_store is None:
        _global_store = PersistentMemoryStore()
    return _global_store
