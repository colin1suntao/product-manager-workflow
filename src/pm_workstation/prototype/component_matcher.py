"""组件匹配器

为页面结构和需求元素匹配最佳组件。
"""

from typing import Optional

from pm_workstation.models.component import (
    Component,
    ComponentCategory,
    ComponentSearchResult,
    ComponentVersion,
)
from pm_workstation.storage.component_store import ComponentStore


class ComponentMatcher:
    """组件匹配器
    
    根据页面元素描述和需求上下文，从组件库中匹配最佳组件。
    """
    
    def __init__(self, store: ComponentStore):
        self._store = store
    
    async def match_for_page(
        self,
        page_description: str,
        suggested_components: Optional[list[str]] = None,
        category_hint: Optional[str] = None,
    ) -> list[tuple[str, ComponentSearchResult]]:
        """为页面匹配组件
        
        Args:
            page_description: 页面描述
            suggested_components: 建议的组件名称列表
            category_hint: 分类提示
            
        Returns:
            组件名称与搜索结果的元组列表
        """
        results = []
        
        # 如果有建议组件，优先按名称搜索
        if suggested_components:
            for comp_name in suggested_components:
                result = await self._search_by_name(comp_name)
                if result:
                    results.append((comp_name, result))
        
        # 根据页面描述搜索
        desc_result = await self._store.match_component(
            description=page_description,
            category_hint=category_hint,
            min_similarity=0.3,
        )
        if desc_result:
            results.append(("description_match", desc_result))
        
        return results
    
    async def match_for_operation(
        self,
        operation: str,
        context: Optional[str] = None,
    ) -> Optional[ComponentSearchResult]:
        """为操作匹配组件
        
        Args:
            operation: 操作描述（如"列表展示"、"搜索"、"创建"）
            context: 上下文信息
            
        Returns:
            最佳匹配结果
        """
        category = self._infer_category_from_operation(operation)
        
        return await self._store.match_component(
            description=f"{operation} {context or ''}",
            category_hint=category.value if category else None,
            min_similarity=0.3,
        )
    
    async def match_for_entity(
        self,
        entity_name: str,
        entity_description: str,
        attributes: Optional[list[dict]] = None,
    ) -> list[ComponentSearchResult]:
        """为实体匹配展示组件
        
        Args:
            entity_name: 实体名称
            entity_description: 实体描述
            attributes: 属性列表
            
        Returns:
            匹配的组件列表
        """
        results = []
        
        # 搜索列表展示组件
        list_result = await self._store.match_component(
            description=f"display {entity_name} list",
            category_hint="data_display",
            min_similarity=0.3,
        )
        if list_result:
            results.append(list_result)
        
        # 搜索表单组件
        if attributes and len(attributes) > 0:
            form_result = await self._store.match_component(
                description=f"form for {entity_name} with {len(attributes)} fields",
                category_hint="form",
                min_similarity=0.3,
            )
            if form_result:
                results.append(form_result)
        
        return results
    
    def _infer_category_from_operation(self, operation: str) -> Optional[ComponentCategory]:
        """从操作推断组件分类"""
        operation_lower = operation.lower()
        
        category_map = {
            "列表": ComponentCategory.DATA_DISPLAY,
            "list": ComponentCategory.DATA_DISPLAY,
            "table": ComponentCategory.DATA_DISPLAY,
            "搜索": ComponentCategory.INPUT,
            "search": ComponentCategory.INPUT,
            "filter": ComponentCategory.FORM,
            "筛选": ComponentCategory.FORM,
            "创建": ComponentCategory.FORM,
            "create": ComponentCategory.FORM,
            "编辑": ComponentCategory.FORM,
            "edit": ComponentCategory.FORM,
            "form": ComponentCategory.FORM,
            "表单": ComponentCategory.FORM,
            "删除": ComponentCategory.BUTTON,
            "delete": ComponentCategory.BUTTON,
            "button": ComponentCategory.BUTTON,
            "按钮": ComponentCategory.BUTTON,
            "导航": ComponentCategory.NAVIGATION,
            "navigation": ComponentCategory.NAVIGATION,
            "menu": ComponentCategory.NAVIGATION,
            "提示": ComponentCategory.FEEDBACK,
            "alert": ComponentCategory.FEEDBACK,
            "modal": ComponentCategory.FEEDBACK,
            "弹窗": ComponentCategory.FEEDBACK,
        }
        
        for keyword, category in category_map.items():
            if keyword in operation_lower:
                return category
        
        return None
    
    async def _search_by_name(self, name: str) -> Optional[ComponentSearchResult]:
        """按名称搜索组件"""
        from pm_workstation.models.component import ComponentSearchRequest
        
        request = ComponentSearchRequest(
            query=name,
            min_similarity=0.4,
            limit=1,
        )
        
        results = await self._store.search(request)
        return results[0] if results else None
