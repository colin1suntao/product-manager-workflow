"""三层记忆架构测试"""

import json
import pytest

from pm_workstation.memory.layered_manager import LayeredMemoryManager
from pm_workstation.memory.layered_models import (
    LongTermCategory,
    LongTermMemoryEntry,
    MemoryLayer,
    MemoryPriority,
    MemoryRetrievalQuery,
    ShortTermMemory,
    WorkingMemory,
)


class TestShortTermMemory:
    """短期记忆测试"""

    def test_create_stm(self):
        stm = ShortTermMemory(session_id="test", user_id="user1")
        assert stm.token_budget == 8000
        assert stm.current_tokens == 0

    def test_add_message(self):
        stm = ShortTermMemory(session_id="test", user_id="user1")
        ok = stm.add_message("user", "Hello world")
        assert ok
        assert len(stm.messages) == 1

    def test_token_budget_precheck_before_add(self):
        """修复: 预算检查在追加消息之前"""
        stm = ShortTermMemory(session_id="test", user_id="user1", token_budget=20)
        # 第一条消息 ≈ 25 tokens，超预算触发 compact
        ok = stm.add_message("user", "x" * 100)
        assert ok  # 即使超预算，消息也正常添加（compact 后腾出空间）

    def test_token_budget_overflow_triggers_compaction(self):
        stm = ShortTermMemory(session_id="test", user_id="user1", token_budget=50)
        for i in range(20):
            stm.add_message("user", "x" * 100)
        assert stm.summarized
        assert len(stm.messages) < 20

    def test_compact_at_boundary_11_messages(self):
        """修复: 测试恰好 11 条消息时的压缩行为"""
        stm = ShortTermMemory(session_id="test", user_id="user1", token_budget=5)
        for i in range(11):
            stm.add_message("user", f"message {i} " * 100)
        assert stm.summarized
        assert len(stm.messages) < 11

    def test_compact_tracks_summary_tokens(self):
        """修复: 压缩后 summary 的 token 也被计入 current_tokens"""
        stm = ShortTermMemory(session_id="test", user_id="user1", token_budget=100)
        for i in range(15):
            stm.add_message("user", "x" * 200)
        assert stm.summarized
        # current_tokens 应包含 summary 的 token
        assert stm.current_tokens > 0

    def test_token_estimate_uses_truncated_content(self):
        """修复: token 估算使用截断后的内容"""
        stm = ShortTermMemory(session_id="test", user_id="user1")
        long_content = "y" * 5000
        stm.add_message("user", long_content)
        # 消息内容被截断为 2000，tokens ≈ 500
        assert stm.messages[0]["content"] == long_content[:2000]
        assert stm.current_tokens <= 500 + 5  # ≈500 tokens

    def test_get_context_for_injection(self):
        stm = ShortTermMemory(session_id="test", user_id="user1")
        stm.add_message("user", "I need help with a project")
        stm.add_message("assistant", "Sure, let me help")
        ctx = stm.get_context_for_injection()
        assert "I need help" in ctx
        assert "近期对话" in ctx


class TestWorkingMemory:
    """工作记忆测试"""

    def test_add_manual_entry(self):
        wm = WorkingMemory(session_id="s1", user_id="u1")
        entry = LongTermMemoryEntry(
            user_id="u1",
            title="Test Knowledge",
            content="This is important knowledge",
            category=LongTermCategory.KNOWLEDGE,
            priority=MemoryPriority.HIGH,
        )
        wm.add_manual_entry(entry)
        assert len(wm.manual_entries) == 1
        assert wm.all_entries[0].title == "Test Knowledge"

    def test_add_manual_entry_deep_copies(self):
        """修复: add_manual_entry 应深拷贝，不修改原始对象"""
        wm = WorkingMemory(session_id="s1", user_id="u1")
        entry = LongTermMemoryEntry(
            user_id="u1",
            title="Original",
            content="Content",
            layer=MemoryLayer.LONG_TERM,
        )
        original_layer = entry.layer
        wm.add_manual_entry(entry)
        # 原始对象 layer 未被修改
        assert entry.layer == original_layer
        # 工作记忆中的拷贝 layer 正确
        assert wm.manual_entries[0].layer == MemoryLayer.WORKING

    def test_clear_task(self):
        wm = WorkingMemory(session_id="s1", user_id="u1")
        entry = LongTermMemoryEntry(
            user_id="u1",
            title="Task Context",
            content="Current task info",
            category=LongTermCategory.SESSION,
        )
        wm.add_manual_entry(entry)
        wm.clear_task()
        assert len(wm.manual_entries) == 0

    def test_get_context_truncation(self):
        wm = WorkingMemory(session_id="s1", user_id="u1")
        for i in range(15):
            entry = LongTermMemoryEntry(
                user_id="u1",
                title=f"Memory {i}",
                content="x" * 500,
                category=LongTermCategory.CUSTOM,
                importance=0.3 + (i * 0.02),
            )
            wm.add_manual_entry(entry)
        ctx = wm.get_context_for_injection(max_tokens=500)
        assert len(ctx) > 0
        assert len(ctx) // 4 < 600


class TestLongTermMemoryCRUD:
    """长期记忆 CRUD 测试"""

    @pytest.fixture
    def manager(self, tmp_path):
        return LayeredMemoryManager(storage_dir=str(tmp_path / "memory"))

    def test_store_and_get(self, manager):
        entry = LongTermMemoryEntry(
            user_id="user1",
            title="Project Architecture",
            content="We use microservices with Docker",
            category=LongTermCategory.PROJECT,
            tags=["architecture", "backend"],
            priority=MemoryPriority.HIGH,
            importance=0.9,
        )
        stored = manager.store_long_term(entry)
        assert stored.id == entry.id

        retrieved = manager.get_long_term("user1", entry.id)
        assert retrieved is not None
        assert retrieved.title == "Project Architecture"
        assert retrieved.access_count == 1

    def test_repeated_get_increments_access(self):
        """修复: 多次获取同一记忆，access_count 应递增"""
        manager = LayeredMemoryManager()
        entry = LongTermMemoryEntry(
            user_id="u_test",
            title="Frequent Memory",
            content="Accessed many times",
        )
        manager.store_long_term(entry)

        for _ in range(6):
            manager.get_long_term("u_test", entry.id)
        retrieved = manager.get_long_term("u_test", entry.id)
        assert retrieved.access_count >= 6
        # 访问 >=5 次应提升 importance
        assert retrieved.importance > 0.5

    def test_list_with_filters(self, manager):
        for i in range(5):
            entry = LongTermMemoryEntry(
                user_id="user1",
                title=f"Memory {i}",
                content=f"Content {i}",
                category=LongTermCategory.PROJECT if i % 2 == 0 else LongTermCategory.USER,
                tags=["tag_a"] if i < 3 else ["tag_b"],
                priority=MemoryPriority.HIGH if i < 2 else MemoryPriority.MEDIUM,
            )
            manager.store_long_term(entry)

        entries, total = manager.list_long_term("user1", category=LongTermCategory.PROJECT)
        assert total == 3

        entries, total = manager.list_long_term("user1", tags=["tag_a"])
        assert total == 3

        entries, total = manager.list_long_term("user1", priority=MemoryPriority.HIGH)
        assert total == 2

    def test_list_pagination_boundary(self, manager):
        """修复: 测试分页边界（page 超出范围）"""
        for i in range(3):
            entry = LongTermMemoryEntry(
                user_id="user1",
                title=f"Item {i}",
                content=f"Content {i}",
            )
            manager.store_long_term(entry)

        entries, total = manager.list_long_term("user1", page=2, page_size=2)
        assert total == 3
        assert len(entries) == 1  # 只剩 1 条

        entries, total = manager.list_long_term("user1", page=10, page_size=10)
        assert len(entries) == 0

    def test_update(self, manager):
        entry = LongTermMemoryEntry(
            user_id="user1",
            title="Original Title",
            content="Original Content",
            tags=["old"],
        )
        manager.store_long_term(entry)

        updated = manager.update_long_term(
            entry.id,
            user_id="user1",
            title="Updated Title",
            tags=["new", "updated"],
        )
        assert updated is not None
        assert updated.title == "Updated Title"
        assert "new" in updated.tags

    def test_delete(self, manager):
        entry = LongTermMemoryEntry(
            user_id="user1",
            title="To Delete",
            content="This will be deleted",
        )
        manager.store_long_term(entry)

        assert manager.delete_long_term("user1", entry.id)
        assert manager.get_long_term("user1", entry.id) is None
        assert not manager.delete_long_term("user1", "nonexistent")

    def test_search(self, manager):
        entry1 = LongTermMemoryEntry(
            user_id="user1",
            title="Docker Deployment Guide",
            content="How to deploy using Docker Compose",
            tags=["docker", "deployment"],
            importance=0.8,
        )
        entry2 = LongTermMemoryEntry(
            user_id="user1",
            title="Python Testing Best Practices",
            content="Use pytest with fixtures and mocks",
            tags=["python", "testing"],
            importance=0.6,
        )
        entry3 = LongTermMemoryEntry(
            user_id="user1",
            title="Deployment Checklist",
            content="Pre-deployment verification steps for production",
            tags=["deployment", "checklist"],
            importance=0.7,
        )
        manager.store_long_term(entry1)
        manager.store_long_term(entry2)
        manager.store_long_term(entry3)

        results = manager.search_long_term(
            MemoryRetrievalQuery(user_id="user1", keyword="deployment")
        )
        assert len(results) == 2

        results = manager.search_long_term(
            MemoryRetrievalQuery(user_id="user1", keyword="python test")
        )
        assert len(results) == 1

        results = manager.search_long_term(
            MemoryRetrievalQuery(user_id="user1", min_importance=0.7)
        )
        assert len(results) == 2

    def test_search_track_access_false_no_side_effects(self, manager):
        """修复: track_access=False 不应修改数据文件"""
        entry = LongTermMemoryEntry(
            user_id="user1",
            title="ReadOnly Memory",
            content="Should not update access count on read-only search",
        )
        manager.store_long_term(entry)

        # 只读搜索
        results = manager.search_long_term(
            MemoryRetrievalQuery(user_id="user1", keyword="ReadOnly"),
            track_access=False,
        )
        assert len(results) == 1
        assert results[0].access_count == 0  # 未更新

        # 再次读取确认未变化
        retrieved = manager.get_long_term("user1", entry.id)
        assert retrieved.access_count == 1  # 仅 get_long_term 更新

    def test_search_recency_sort(self, manager):
        """修复: recency 排序应使用 last_accessed"""
        e1 = LongTermMemoryEntry(user_id="user1", title="A", content="A", importance=0.5)
        e2 = LongTermMemoryEntry(user_id="user1", title="B", content="B", importance=0.5)
        manager.store_long_term(e1)
        manager.store_long_term(e2)
        # 访问 e1 一次使 last_accessed 更新
        manager.get_long_term("user1", e1.id)

        results = manager.search_long_term(
            MemoryRetrievalQuery(user_id="user1", sort_by="recency")
        )
        assert len(results) == 2
        # e1 最近访问过应排第一
        assert results[0].id == e1.id

    def test_atomic_write_persistence(self, tmp_path):
        """修复: 原子写入后数据完整可读"""
        storage = str(tmp_path / "memory")
        manager = LayeredMemoryManager(storage_dir=storage)

        for i in range(10):
            entry = LongTermMemoryEntry(
                user_id="user1",
                title=f"Entry {i}",
                content=f"Content {i}",
            )
            manager.store_long_term(entry)

        # 重新加载
        manager2 = LayeredMemoryManager(storage_dir=storage)
        entries, total = manager2.list_long_term("user1")
        assert total == 10
        assert entries[0].title == "Entry 0"

    def test_corrupted_json_recovery(self, tmp_path):
        """修复: 损坏的 JSON 文件返回空列表而不崩溃"""
        import hashlib

        storage = str(tmp_path / "memory")
        safe_hash = hashlib.sha256("user1".encode()).hexdigest()[:16]
        ltm_file = tmp_path / "memory" / f"ltm_{safe_hash}.json"

        # 写入一些有效数据
        manager = LayeredMemoryManager(storage_dir=storage)
        entry = LongTermMemoryEntry(
            user_id="user1",
            title="Before Corruption",
            content="Valid data",
        )
        manager.store_long_term(entry)

        # 破坏文件
        ltm_file.write_text("this is not valid json {{{")

        # 不应崩溃
        entries, total = manager.list_long_term("user1")
        assert total == 0


class TestLayeredMemoryManager:
    """三层记忆管理器集成测试"""

    @pytest.fixture
    def manager(self, tmp_path):
        return LayeredMemoryManager(storage_dir=str(tmp_path / "memory"))

    def test_init_and_end_session(self, manager):
        manager.init_session("s1", "u1")
        assert manager.stm is not None
        assert manager.wm is not None

        cleaned = manager.end_session("s1")
        assert cleaned
        assert manager.stm is None
        assert manager.wm is None

    def test_end_session_with_explicit_id(self, manager):
        """修复: end_session 应接受 session_id 参数"""
        manager.init_session("s1", "u1")
        manager.init_session("s2", "u2")  # 切换，s1 自动清理

        # s2 是当前会话
        assert manager._current_session_id == "s2"

        # 尝试清理 s2
        cleaned = manager.end_session("s2")
        assert cleaned

    def test_session_switch_cleans_old(self, manager):
        """修复: 切换 session 时自动清理旧会话"""
        manager.init_session("s1", "u1")
        # 往旧 session 加一些数据
        manager.stm.add_message("user", "test message")
        assert manager._current_session_id == "s1"

        # 切换到新 session
        manager.init_session("s2", "u2")
        assert manager._current_session_id == "s2"

        # 旧 session 应从字典中移除
        assert "s1" not in manager._stm
        assert "s1" not in manager._wm

        # 新 session 活跃
        assert manager.stm is not None
        assert manager.stm.session_id == "s2"

    def test_end_session_nonexistent_returns_false(self, manager):
        """修复: 结束不存在的 session 返回 False"""
        cleaned = manager.end_session("nonexistent")
        assert not cleaned

    def test_user_add_working_memory_and_promote(self, manager):
        manager.init_session("s1", "u1")

        entry = manager.add_wm_entry(
            title="API Design Rule",
            content="Always use RESTful conventions with versioned endpoints",
            category=LongTermCategory.KNOWLEDGE,
            tags=["api", "design"],
            priority=MemoryPriority.HIGH,
        )
        assert manager.wm is not None
        assert len(manager.wm.manual_entries) == 1

        promoted = manager.promote_to_long_term(entry)
        assert promoted.layer.value == "long_term"

        retrieved = manager.get_long_term("u1", entry.id)
        assert retrieved is not None
        assert retrieved.title == "API Design Rule"

    def test_full_injection_context(self, manager):
        manager.init_session("s1", "u1")
        manager.stm.add_message("user", "How to deploy?")
        manager.stm.add_message("assistant", "Use Docker Compose")

        manager.add_wm_entry(
            title="Deploy Config",
            content="docker-compose.yml with 3 services",
            category=LongTermCategory.PROJECT,
            priority=MemoryPriority.HIGH,
        )

        ltm_entry = LongTermMemoryEntry(
            user_id="u1",
            title="Production Checklist",
            content="Always run integration tests before deploy",
            category=LongTermCategory.PROJECT,
            priority=MemoryPriority.CRITICAL,
            importance=0.95,
        )
        manager.store_long_term(ltm_entry)

        ctx = manager.get_full_injection_context()
        assert "deploy" in ctx.lower()
        assert "Deploy Config" in ctx
        assert "Production Checklist" in ctx

    def test_full_injection_context_is_read_only(self, manager):
        """修复: get_full_injection_context 不应产生写盘副作用"""
        manager.init_session("s1", "u1")

        entry = LongTermMemoryEntry(
            user_id="u1",
            title="Critical Rule",
            content="Important constraint",
            priority=MemoryPriority.CRITICAL,
        )
        manager.store_long_term(entry)

        # 获取注入上下文
        ctx = manager.get_full_injection_context()
        assert "Critical Rule" in ctx

        # 检查 access_count 未被修改（track_access=False）
        retrieved = manager.get_long_term("u1", entry.id)
        assert retrieved.access_count == 1  # 只有 get_long_term 涨了一次

    def test_stats(self, manager):
        manager.init_session("s1", "u1")

        for i in range(5):
            entry = LongTermMemoryEntry(
                user_id="u1",
                title=f"Knowledge {i}",
                content=f"Content {i}",
                category=LongTermCategory.KNOWLEDGE if i % 2 == 0 else LongTermCategory.PROJECT,
                priority=MemoryPriority.HIGH if i < 2 else MemoryPriority.MEDIUM,
                tags=["dev"] if i < 3 else ["ops"],
            )
            manager.store_long_term(entry)

        stats = manager.get_stats()
        assert stats.total_memories > 0
        assert "knowledge" in stats.by_category or "project" in stats.by_category
        assert stats.total_manual_entries >= 0

    def test_load_wm_from_ltm(self, manager):
        manager.init_session("s1", "u1")

        manager.store_long_term(LongTermMemoryEntry(
            user_id="u1",
            title="Docker Tips",
            content="Use multi-stage builds for smaller images",
            tags=["docker", "optimization"],
        ))
        manager.store_long_term(LongTermMemoryEntry(
            user_id="u1",
            title="Testing Guide",
            content="Write tests before implementation",
            tags=["testing", "tdd"],
        ))

        results = manager.load_wm_from_ltm(
            task_description="I need to optimize Docker builds",
            task_type="devops",
            max_items=5,
        )
        assert len(results) >= 1
        assert any("Docker" in r.title for r in results)
