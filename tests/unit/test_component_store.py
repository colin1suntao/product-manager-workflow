"""组件库存储测试"""

from datetime import datetime

import pytest

from pm_workstation.models.component import (
    Component,
    ComponentCategory,
    ComponentMatchRequest,
    ComponentSearchRequest,
    ComponentStatus,
    ComponentVersion,
)
from pm_workstation.storage.component_store_memory import InMemoryComponentStore


@pytest.fixture
def store():
    """创建内存存储实例"""
    return InMemoryComponentStore()


@pytest.fixture
def sample_component():
    """创建示例组件"""
    return Component(
        id="comp-001",
        name="DataTable",
        display_name="数据表格",
        description="A responsive data table with sorting and filtering",
        category=ComponentCategory.DATA_DISPLAY,
        tags=["table", "data", "grid", "sorting", "filter"],
        status=ComponentStatus.PUBLISHED,
    )


@pytest.fixture
def sample_version():
    """创建示例版本"""
    return ComponentVersion(
        component_id="comp-001",
        version="1.0.0",
        html_template="<table>{{rows}}</table>",
        css_content="table { width: 100%; }",
        js_content="function init() {}",
        changelog="Initial release",
    )


class TestInMemoryComponentStoreCreate:
    """创建组件测试"""
    
    @pytest.mark.asyncio
    async def test_create_component(self, store, sample_component):
        """测试创建组件"""
        result = await store.create_component(sample_component)
        
        assert result.id == "comp-001"
        assert result.name == "DataTable"
        assert result.status == ComponentStatus.PUBLISHED
    
    @pytest.mark.asyncio
    async def test_create_component_auto_id(self, store):
        """测试自动ID生成"""
        component = Component(
            id="",  # 空ID应自动生成
            name="AutoIDComponent",
        )
        
        result = await store.create_component(component)
        assert result.id is not None
        assert len(result.id) > 0
    
    @pytest.mark.asyncio
    async def test_create_duplicate_component(self, store, sample_component):
        """测试重复组件创建"""
        await store.create_component(sample_component)
        
        with pytest.raises(ValueError, match="already exists"):
            await store.create_component(sample_component)
    
    @pytest.mark.asyncio
    async def test_create_version(self, store, sample_component, sample_version):
        """测试创建版本"""
        await store.create_component(sample_component)
        result = await store.create_version(sample_version)
        
        assert result.component_id == "comp-001"
        assert result.version == "1.0.0"
        assert result.is_latest is True
    
    @pytest.mark.asyncio
    async def test_create_version_nonexistent_component(self, store, sample_version):
        """测试为不存在的组件创建版本"""
        with pytest.raises(ValueError, match="not found"):
            await store.create_version(sample_version)
    
    @pytest.mark.asyncio
    async def test_create_version_marks_previous_non_latest(
        self, store, sample_component
    ):
        """测试创建新版本时标记旧版本"""
        await store.create_component(sample_component)
        
        v1 = ComponentVersion(
            component_id="comp-001",
            version="1.0.0",
        )
        await store.create_version(v1)
        
        v2 = ComponentVersion(
            component_id="comp-001",
            version="2.0.0",
        )
        await store.create_version(v2)
        
        assert v1.is_latest is False
        assert v2.is_latest is True


class TestInMemoryComponentStoreRead:
    """读取组件测试"""
    
    @pytest.mark.asyncio
    async def test_get_component(self, store, sample_component):
        """测试获取组件"""
        await store.create_component(sample_component)
        result = await store.get_component("comp-001")
        
        assert result is not None
        assert result.name == "DataTable"
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_component(self, store):
        """测试获取不存在的组件"""
        result = await store.get_component("nonexistent")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_version(self, store, sample_component, sample_version):
        """测试获取版本"""
        await store.create_component(sample_component)
        await store.create_version(sample_version)
        
        result = await store.get_version("comp-001", "1.0.0")
        assert result is not None
        assert result.version == "1.0.0"
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_version(self, store, sample_component):
        """测试获取不存在的版本"""
        await store.create_component(sample_component)
        
        result = await store.get_version("comp-001", "99.0.0")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_latest_version(self, store, sample_component):
        """测试获取最新版本"""
        await store.create_component(sample_component)
        
        v1 = ComponentVersion(component_id="comp-001", version="1.0.0")
        v2 = ComponentVersion(component_id="comp-001", version="2.0.0")
        
        await store.create_version(v1)
        await store.create_version(v2)
        
        result = await store.get_latest_version("comp-001")
        assert result.version == "2.0.0"
        assert result.is_latest is True
    
    @pytest.mark.asyncio
    async def test_list_components(self, store):
        """测试列出组件"""
        components = [
            Component(id="c1", name="Comp1", category=ComponentCategory.BUTTON),
            Component(id="c2", name="Comp2", category=ComponentCategory.FORM),
            Component(id="c3", name="Comp3", category=ComponentCategory.BUTTON),
        ]
        
        for c in components:
            await store.create_component(c)
        
        result = await store.list_components()
        assert len(result) == 3
    
    @pytest.mark.asyncio
    async def test_list_components_filter_category(self, store):
        """测试按分类过滤"""
        await store.create_component(
            Component(id="c1", name="Button", category=ComponentCategory.BUTTON)
        )
        await store.create_component(
            Component(id="c2", name="Form", category=ComponentCategory.FORM)
        )
        
        result = await store.list_components(category="button")
        assert len(result) == 1
        assert result[0].category == ComponentCategory.BUTTON
    
    @pytest.mark.asyncio
    async def test_list_components_filter_status(self, store):
        """测试按状态过滤"""
        await store.create_component(
            Component(id="c1", name="Pub", status=ComponentStatus.PUBLISHED)
        )
        await store.create_component(
            Component(id="c2", name="Draft", status=ComponentStatus.DRAFT)
        )
        
        result = await store.list_components(status="published")
        assert len(result) == 1
    
    @pytest.mark.asyncio
    async def test_list_components_filter_tags(self, store):
        """测试按标签过滤"""
        await store.create_component(
            Component(id="c1", name="Table", tags=["table", "data"])
        )
        await store.create_component(
            Component(id="c2", name="Form", tags=["form", "input"])
        )
        
        result = await store.list_components(tags=["table"])
        assert len(result) == 1
    
    @pytest.mark.asyncio
    async def test_list_components_pagination(self, store):
        """测试分页"""
        for i in range(10):
            await store.create_component(
                Component(id=f"c{i}", name=f"Comp{i}")
            )
        
        result = await store.list_components(limit=3, offset=2)
        assert len(result) == 3
    
    @pytest.mark.asyncio
    async def test_list_versions(self, store, sample_component):
        """测试列出版本"""
        await store.create_component(sample_component)
        
        for v in ["1.0.0", "1.1.0", "2.0.0"]:
            await store.create_version(
                ComponentVersion(component_id="comp-001", version=v)
            )
        
        result = await store.list_versions("comp-001")
        assert len(result) == 3
        # 最新创建的版本应该排在前面
        assert result[0].version == "2.0.0"
    
    @pytest.mark.asyncio
    async def test_list_versions_limit(self, store, sample_component):
        """测试版本列表限制"""
        await store.create_component(sample_component)
        
        for v in range(5):
            await store.create_version(
                ComponentVersion(
                    component_id="comp-001",
                    version=f"{v}.0.0",
                )
            )
        
        result = await store.list_versions("comp-001", limit=2)
        assert len(result) == 2


class TestInMemoryComponentStoreUpdate:
    """更新组件测试"""
    
    @pytest.mark.asyncio
    async def test_update_component(self, store, sample_component):
        """测试更新组件"""
        await store.create_component(sample_component)
        
        result = await store.update_component(
            "comp-001",
            description="Updated description",
            status=ComponentStatus.DEPRECATED,
        )
        
        assert result is not None
        assert result.description == "Updated description"
        assert result.status == ComponentStatus.DEPRECATED
    
    @pytest.mark.asyncio
    async def test_update_nonexistent_component(self, store):
        """测试更新不存在的组件"""
        result = await store.update_component("nonexistent", name="New")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_update_component_timestamp(self, store, sample_component):
        """测试更新时间戳"""
        await store.create_component(sample_component)
        
        original_time = sample_component.updated_at
        await store.update_component("comp-001", description="Updated")
        
        component = await store.get_component("comp-001")
        assert component.updated_at > original_time


class TestInMemoryComponentStoreDelete:
    """删除组件测试"""
    
    @pytest.mark.asyncio
    async def test_delete_component(self, store, sample_component):
        """测试删除组件"""
        await store.create_component(sample_component)
        
        result = await store.delete_component("comp-001")
        assert result is True
        
        # 确认组件已删除
        component = await store.get_component("comp-001")
        assert component is None
    
    @pytest.mark.asyncio
    async def test_delete_nonexistent_component(self, store):
        """测试删除不存在的组件"""
        result = await store.delete_component("nonexistent")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_delete_component_removes_versions(
        self, store, sample_component, sample_version
    ):
        """测试删除组件同时删除版本"""
        await store.create_component(sample_component)
        await store.create_version(sample_version)
        
        await store.delete_component("comp-001")
        
        versions = await store.list_versions("comp-001")
        assert len(versions) == 0


class TestInMemoryComponentStoreSearch:
    """搜索组件测试"""
    
    @pytest.mark.asyncio
    async def test_search_by_name(self, store):
        """测试按名称搜索"""
        await store.create_component(
            Component(
                id="c1",
                name="DataTable",
                description="A data table component",
                tags=["table", "data"],
            )
        )
        await store.create_component(
            Component(
                id="c2",
                name="FormInput",
                description="A form input component",
                tags=["form", "input"],
            )
        )
        
        request = ComponentSearchRequest(query="data table")
        results = await store.search(request)
        
        assert len(results) >= 1
        assert results[0].component.name == "DataTable"
    
    @pytest.mark.asyncio
    async def test_search_by_description(self, store):
        """测试按描述搜索"""
        await store.create_component(
            Component(
                id="c1",
                name="Modal",
                description="A modal dialog for displaying alerts and confirmations",
            )
        )
        
        request = ComponentSearchRequest(query="alert dialog")
        results = await store.search(request)
        
        assert len(results) >= 1
        assert results[0].component.name == "Modal"
    
    @pytest.mark.asyncio
    async def test_search_by_tags(self, store):
        """测试按标签搜索"""
        await store.create_component(
            Component(id="c1", name="Button", tags=["button", "primary"])
        )
        await store.create_component(
            Component(id="c2", name="Card", tags=["card", "layout"])
        )
        
        request = ComponentSearchRequest(query="primary")
        results = await store.search(request)
        
        # 包含"primary"标签的组件应该排在前面
        assert any(r.component.name == "Button" for r in results)
    
    @pytest.mark.asyncio
    async def test_search_with_category_filter(self, store):
        """测试搜索带分类过滤"""
        await store.create_component(
            Component(
                id="c1",
                name="Button",
                description="A clickable button",
                category=ComponentCategory.BUTTON,
            )
        )
        await store.create_component(
            Component(
                id="c2",
                name="Table",
                description="A data table",
                category=ComponentCategory.DATA_DISPLAY,
            )
        )
        
        request = ComponentSearchRequest(
            query="data",
            category=ComponentCategory.DATA_DISPLAY,
        )
        results = await store.search(request)
        
        assert all(r.component.category == ComponentCategory.DATA_DISPLAY for r in results)
    
    @pytest.mark.asyncio
    async def test_search_with_status_filter(self, store):
        """测试搜索带状态过滤"""
        await store.create_component(
            Component(id="c1", name="Active", status=ComponentStatus.PUBLISHED)
        )
        await store.create_component(
            Component(id="c2", name="Deprecated", status=ComponentStatus.DEPRECATED)
        )
        
        request = ComponentSearchRequest(
            query="active deprecated",
            status=ComponentStatus.PUBLISHED,
        )
        results = await store.search(request)
        
        assert all(r.component.status == ComponentStatus.PUBLISHED for r in results)
    
    @pytest.mark.asyncio
    async def test_search_with_tags_filter(self, store):
        """测试搜索带标签过滤"""
        await store.create_component(
            Component(id="c1", name="Table", tags=["table", "data"])
        )
        await store.create_component(
            Component(id="c2", name="Form", tags=["form", "input"])
        )
        
        request = ComponentSearchRequest(
            query="table form",
            tags=["table"],
        )
        results = await store.search(request)
        
        assert all("table" in r.component.tags for r in results)
    
    @pytest.mark.asyncio
    async def test_search_similarity_threshold(self, store):
        """测试相似度阈值"""
        await store.create_component(
            Component(
                id="c1",
                name="ExactMatch",
                description="This is an exact match component",
            )
        )
        await store.create_component(
            Component(
                id="c2",
                name="Unrelated",
                description="Completely different thing",
            )
        )
        
        request = ComponentSearchRequest(
            query="exact match",
            min_similarity=0.8,
        )
        results = await store.search(request)
        
        # 只有高相似度的应该返回
        assert all(r.similarity_score >= 0.8 for r in results)
    
    @pytest.mark.asyncio
    async def test_search_limit(self, store):
        """测试搜索数量限制"""
        for i in range(5):
            await store.create_component(
                Component(
                    id=f"c{i}",
                    name=f"Searchable{i}",
                    description="This component is searchable",
                )
            )
        
        request = ComponentSearchRequest(query="searchable", limit=2)
        results = await store.search(request)
        
        assert len(results) <= 2
    
    @pytest.mark.asyncio
    async def test_search_sorted_by_similarity(self, store):
        """测试结果按相似度排序"""
        await store.create_component(
            Component(
                id="c1",
                name="PerfectMatch",
                description="A perfect match for the query",
            )
        )
        await store.create_component(
            Component(
                id="c2",
                name="PartialMatch",
                description="Only partially related content",
            )
        )
        
        request = ComponentSearchRequest(query="perfect match")
        results = await store.search(request)
        
        # 第一个结果应该是 PerfectMatch
        if len(results) >= 2:
            assert results[0].similarity_score >= results[1].similarity_score
    
    @pytest.mark.asyncio
    async def test_search_no_query(self, store):
        """测试无查询词搜索"""
        await store.create_component(
            Component(id="c1", name="Component", tags=["test"])
        )
        
        request = ComponentSearchRequest(query="")
        results = await store.search(request)
        
        # 无查询时应返回所有匹配的组件
        assert len(results) >= 1
    
    @pytest.mark.asyncio
    async def test_search_no_results(self, store):
        """测试无匹配结果"""
        request = ComponentSearchRequest(query="nonexistent component xyz")
        results = await store.search(request)
        
        assert len(results) == 0


class TestInMemoryComponentStoreMatch:
    """组件匹配测试"""
    
    @pytest.mark.asyncio
    async def test_match_component(self, store):
        """测试匹配最佳组件"""
        await store.create_component(
            Component(
                id="c1",
                name="DataGrid",
                description="A data grid component with sorting and filtering",
                category=ComponentCategory.DATA_DISPLAY,
                tags=["table", "grid", "data"],
            )
        )
        await store.create_component(
            Component(
                id="c2",
                name="Button",
                description="A clickable button component",
                category=ComponentCategory.BUTTON,
            )
        )
        
        result = await store.match_component(
            description="I need a component to display tabular data with sorting",
            category_hint="data_display",
        )
        
        assert result is not None
        assert result.component.name == "DataGrid"
    
    @pytest.mark.asyncio
    async def test_match_no_result(self, store):
        """测试无匹配"""
        result = await store.match_component(
            description="completely unrelated query",
            min_similarity=0.9,
        )
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_match_with_category_hint(self, store):
        """测试带分类提示的匹配"""
        await store.create_component(
            Component(
                id="c1",
                name="FormInput",
                description="Text input for forms",
                category=ComponentCategory.FORM,
            )
        )
        await store.create_component(
            Component(
                id="c2",
                name="Table",
                description="Data table display",
                category=ComponentCategory.DATA_DISPLAY,
            )
        )
        
        result = await store.match_component(
            description="input field",
            category_hint="form",
        )
        
        assert result is not None
        assert result.component.category == ComponentCategory.FORM


class TestComponentModels:
    """组件数据模型测试"""
    
    def test_component_creation(self):
        """测试创建组件"""
        component = Component(
            id="test-1",
            name="TestComponent",
            display_name="Test Component",
            description="A test component",
            category=ComponentCategory.BUTTON,
            tags=["test", "button"],
            status=ComponentStatus.PUBLISHED,
        )
        
        assert component.id == "test-1"
        assert component.category == ComponentCategory.BUTTON
        assert len(component.tags) == 2
    
    def test_component_version_creation(self):
        """测试创建版本"""
        version = ComponentVersion(
            component_id="comp-1",
            version="1.2.3",
            html_template="<div>Test</div>",
            changelog="Added feature",
        )
        
        assert version.component_id == "comp-1"
        assert version.version == "1.2.3"
        assert version.is_latest is True
    
    def test_component_search_request(self):
        """测试搜索请求"""
        request = ComponentSearchRequest(
            query="data table",
            category=ComponentCategory.DATA_DISPLAY,
            tags=["responsive"],
            min_similarity=0.7,
            limit=5,
        )
        
        assert request.category == ComponentCategory.DATA_DISPLAY
        assert request.min_similarity == 0.7
    
    def test_component_match_request(self):
        """测试匹配请求"""
        request = ComponentMatchRequest(
            description="I need a button",
            required_props=["onClick", "disabled"],
            category_hint=ComponentCategory.BUTTON,
            min_similarity=0.5,
        )
        
        assert len(request.required_props) == 2
        assert request.category_hint == ComponentCategory.BUTTON
