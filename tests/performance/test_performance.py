"""性能测试

测试工作流系统的性能指标，包括：
- 推理性能（LLM 调用延迟）
- 生成性能（原型/文档生成速度）
- 并发性能（多工作流同时执行）
"""

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from pm_workstation.models.component import (
    Component,
    ComponentCategory,
    ComponentSearchRequest,
    ComponentStatus,
)
from pm_workstation.orchestrator.workflow_manager import WorkflowManager
from pm_workstation.storage.component_store_memory import InMemoryComponentStore


@pytest.fixture
def workflow_manager():
    return WorkflowManager()


class TestInferencePerformance:
    """推理性能测试"""

    def test_single_workflow_creation_time(self, workflow_manager):
        """测试单个工作流创建时间"""
        iterations = 100
        times = []

        for _ in range(iterations):
            start = time.monotonic()
            workflow_manager.start_workflow(
                user_id="perf-user",
                requirement_text="性能测试需求" * 10,
            )
            elapsed = time.monotonic() - start
            times.append(elapsed)

        avg_time = sum(times) / len(times)
        max_time = max(times)
        min_time = min(times)

        assert avg_time < 0.1, f"Average creation time {avg_time:.4f}s exceeds 100ms"
        assert max_time < 0.5, f"Max creation time {max_time:.4f}s exceeds 500ms"

    def test_workflow_status_query_performance(self, workflow_manager):
        """测试工作流状态查询性能"""
        runs = []
        for i in range(50):
            run = workflow_manager.start_workflow(
                user_id="perf-user",
                requirement_text=f"需求 {i}",
                workflow_id=f"wf-perf-{i:03d}",
            )
            runs.append(run)

        iterations = 200
        times = []

        for _ in range(iterations):
            start = time.monotonic()
            for run in runs:
                workflow_manager.get_workflow_status(run.id)
            elapsed = time.monotonic() - start
            times.append(elapsed)

        avg_time = sum(times) / len(times)
        assert avg_time < 0.05, f"Average query time {avg_time:.4f}s exceeds 50ms"

    def test_workflow_pause_resume_performance(self, workflow_manager):
        """测试暂停/恢复性能"""
        runs = []
        for i in range(20):
            run = workflow_manager.start_workflow(
                user_id="perf-user",
                requirement_text=f"暂停性能需求 {i}",
                workflow_id=f"wf-pause-perf-{i:03d}",
            )
            runs.append(run)

        times = []

        for run in runs:
            start = time.monotonic()
            workflow_manager.pause_workflow(run.id)
            workflow_manager.resume_workflow(run.id)
            elapsed = time.monotonic() - start
            times.append(elapsed)

        avg_time = sum(times) / len(times)
        assert avg_time < 0.01, f"Average pause/resume time {avg_time:.4f}s exceeds 10ms"


class TestGenerationPerformance:
    """生成性能测试"""

    def test_component_store_performance(self):
        """测试组件库存储性能"""
        store = InMemoryComponentStore()

        async def run_test():
            iterations = 100
            times = []

            for i in range(iterations):
                component = Component(
                    id=f"perf-comp-{i:03d}",
                    name=f"Performance Button {i}",
                    description="A button for performance testing" * 5,
                    category=ComponentCategory.BUTTON,
                    tags=["perf", "test", "button"],
                    status=ComponentStatus.PUBLISHED,
                )
                start = time.monotonic()
                await store.create_component(component)
                elapsed = time.monotonic() - start
                times.append(elapsed)

            avg_time = sum(times) / len(times)
            assert avg_time < 0.01, f"Average save time {avg_time:.4f}s exceeds 10ms"

        asyncio.run(run_test())

    def test_component_search_performance(self):
        """测试组件搜索性能"""

        async def run_test():
            store = InMemoryComponentStore()

            for i in range(50):
                component = Component(
                    id=f"search-comp-{i:03d}",
                    name=f"Component {i}",
                    description=f"Description {i}",
                    category=ComponentCategory.BUTTON if i % 2 == 0 else ComponentCategory.FORM,
                    tags=[f"tag-{i % 5}"],
                    status=ComponentStatus.PUBLISHED,
                )
                await store.create_component(component)

            iterations = 50
            times = []

            for _ in range(iterations):
                start = time.monotonic()
                request = ComponentSearchRequest(
                    query="",
                    category=ComponentCategory.BUTTON,
                    min_similarity=0.0,
                )
                await store.search(request)
                elapsed = time.monotonic() - start
                times.append(elapsed)

            avg_time = sum(times) / len(times)
            assert avg_time < 0.01, f"Average search time {avg_time:.4f}s exceeds 10ms"

        asyncio.run(run_test())


class TestConcurrencyPerformance:
    """并发性能测试"""

    def test_concurrent_workflow_creation(self, workflow_manager):
        """测试并发工作流创建"""
        num_workers = 10
        workflows_per_worker = 10

        def create_workflows(worker_id: int) -> int:
            count = 0
            for i in range(workflows_per_worker):
                workflow_manager.start_workflow(
                    user_id=f"worker-{worker_id}",
                    requirement_text=f"Worker {worker_id} task {i}",
                )
                count += 1
            return count

        start = time.monotonic()
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [
                executor.submit(create_workflows, worker_id)
                for worker_id in range(num_workers)
            ]
            results = [f.result() for f in futures]
        elapsed = time.monotonic() - start

        total_created = sum(results)
        assert total_created == num_workers * workflows_per_worker
        assert elapsed < 5.0, f"Concurrent creation took {elapsed:.2f}s, exceeds 5s"

    def test_concurrent_status_queries(self, workflow_manager):
        """测试并发状态查询"""
        for i in range(50):
            workflow_manager.start_workflow(
                user_id="concurrent-user",
                requirement_text=f"并发查询需求 {i}",
                workflow_id=f"wf-concurrent-{i:03d}",
            )

        num_workers = 10
        queries_per_worker = 50

        def query_workflows(worker_id: int) -> int:
            count = 0
            for i in range(queries_per_worker):
                workflow_id = f"wf-concurrent-{i % 50:03d}"
                result = workflow_manager.get_workflow_status(workflow_id)
                if result is not None:
                    count += 1
            return count

        start = time.monotonic()
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [
                executor.submit(query_workflows, worker_id)
                for worker_id in range(num_workers)
            ]
            results = [f.result() for f in futures]
        elapsed = time.monotonic() - start

        total_queries = sum(results)
        assert total_queries == num_workers * queries_per_worker
        assert elapsed < 5.0, f"Concurrent queries took {elapsed:.2f}s, exceeds 5s"

    def test_concurrent_pause_resume(self, workflow_manager):
        """测试并发暂停/恢复"""
        runs = []
        for i in range(20):
            run = workflow_manager.start_workflow(
                user_id="concurrent-user",
                requirement_text=f"并发暂停需求 {i}",
                workflow_id=f"wf-concurrent-pause-{i:03d}",
            )
            runs.append(run)

        num_workers = 5

        def pause_resume_worker(worker_id: int) -> int:
            count = 0
            for i in range(4):
                run_index = (worker_id * 4 + i) % len(runs)
                run = runs[run_index]
                workflow_manager.pause_workflow(run.id)
                workflow_manager.resume_workflow(run.id)
                count += 1
            return count

        start = time.monotonic()
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [
                executor.submit(pause_resume_worker, worker_id)
                for worker_id in range(num_workers)
            ]
            results = [f.result() for f in futures]
        elapsed = time.monotonic() - start

        total_ops = sum(results)
        assert total_ops == num_workers * 4
        assert elapsed < 5.0, f"Concurrent pause/resume took {elapsed:.2f}s, exceeds 5s"


class TestMemoryPerformance:
    """内存性能测试"""

    def test_large_workflow_list_memory(self, workflow_manager):
        """测试大量工作流的内存使用"""
        num_workflows = 500

        for i in range(num_workflows):
            workflow_manager.start_workflow(
                user_id="memory-user",
                requirement_text="需求文本" * 20,
                workflow_id=f"wf-memory-{i:04d}",
            )

        all_workflows = workflow_manager.list_workflows()
        assert len(all_workflows) == num_workflows

    def test_large_component_store_memory(self):
        """测试大量组件的内存使用"""

        async def run_test():
            store = InMemoryComponentStore()
            num_components = 200

            for i in range(num_components):
                component = Component(
                    id=f"memory-comp-{i:04d}",
                    name=f"Memory Component {i}",
                    description="Description" * 10,
                    category=ComponentCategory.BUTTON,
                    tags=[f"tag-{i % 20}"],
                    status=ComponentStatus.PUBLISHED,
                )
                await store.create_component(component)

            request = ComponentSearchRequest(
                query="",
                min_similarity=0.0,
                limit=100,
            )
            result = await store.search(request)
            assert len(result) >= num_components - 100

        asyncio.run(run_test())
