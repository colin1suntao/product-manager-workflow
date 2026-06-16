"""三层记忆架构测试"""

import pytest

from pm_workstation.memory.layered_manager import LayeredMemoryManager
from pm_workstation.memory.layered_models import (
    LongTermCategory,
    LongTermMemoryEntry,
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

    def test_token_budget_overflow_triggers_compaction(self):
        stm = ShortTermMemory(session_id="test", user_id="user1", token_budget=50)
        for i in range(20):
            stm.add_message("user", "x" * 100)
        assert stm.summarized
        assert len(stm.messages) < 20

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


class TestLayeredMemoryManager:
    """三层记忆管理器集成测试"""

    @pytest.fixture
    def manager(self, tmp_path):
        return LayeredMemoryManager(storage_dir=str(tmp_path / "memory"))

    def test_init_and_end_session(self, manager):
        manager.init_session("s1", "u1")
        assert manager.stm is not None
        assert manager.wm is not None

        manager.end_session()
        assert manager.stm is None
        assert manager.wm is None

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

        # 提升为长期记忆
        promoted = manager.promote_to_long_term(entry)
        assert promoted.layer.value == "long_term"

        # 验证在长期记忆中持久化
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

        # 添加长期记忆
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
