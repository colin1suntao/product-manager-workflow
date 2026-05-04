"""内存组件存储实现"""

import re
from datetime import datetime
from typing import Optional
from uuid import uuid4

from pm_workstation.models.component import (
    Component,
    ComponentCategory,
    ComponentSearchRequest,
    ComponentSearchResult,
    ComponentStatus,
    ComponentVersion,
)
from pm_workstation.storage.component_store import ComponentStore


class InMemoryComponentStore(ComponentStore):
    """内存组件存储实现
    
    用于开发和测试，所有数据存储在内存中。
    """
    
    def __init__(self):
        self._components: dict[str, Component] = {}
        self._versions: dict[str, list[ComponentVersion]] = {}  # component_id -> [versions]
    
    async def create_component(self, component: Component) -> Component:
        if component.id in self._components:
            raise ValueError(f"Component with id '{component.id}' already exists")
        
        if not component.id:
            component.id = str(uuid4())
        
        self._components[component.id] = component
        self._versions[component.id] = []
        return component
    
    async def get_component(self, component_id: str) -> Optional[Component]:
        return self._components.get(component_id)
    
    async def update_component(self, component_id: str, **kwargs) -> Optional[Component]:
        if component_id not in self._components:
            return None
        
        component = self._components[component_id]
        for key, value in kwargs.items():
            if hasattr(component, key):
                setattr(component, key, value)
        
        component.updated_at = datetime.now()
        return component
    
    async def delete_component(self, component_id: str) -> bool:
        if component_id not in self._components:
            return False
        
        del self._components[component_id]
        self._versions.pop(component_id, None)
        return True
    
    async def list_components(
        self,
        category: Optional[str] = None,
        status: Optional[str] = None,
        tags: Optional[list[str]] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Component]:
        results = list(self._components.values())
        
        if category:
            results = [c for c in results if c.category.value == category]
        
        if status:
            results = [c for c in results if c.status.value == status]
        
        if tags:
            results = [c for c in results if all(tag in c.tags for tag in tags)]
        
        return results[offset:offset + limit]
    
    async def create_version(self, version: ComponentVersion) -> ComponentVersion:
        component_id = version.component_id
        
        if component_id not in self._components:
            raise ValueError(f"Component '{component_id}' not found")
        
        # 标记旧版本为非最新
        for v in self._versions.get(component_id, []):
            v.is_latest = False
        
        if component_id not in self._versions:
            self._versions[component_id] = []
        
        self._versions[component_id].append(version)
        
        # 更新组件当前版本
        component = self._components[component_id]
        component.current_version = version.version
        component.updated_at = datetime.now()
        
        return version
    
    async def get_version(
        self,
        component_id: str,
        version: str,
    ) -> Optional[ComponentVersion]:
        versions = self._versions.get(component_id, [])
        for v in versions:
            if v.version == version:
                return v
        return None
    
    async def get_latest_version(self, component_id: str) -> Optional[ComponentVersion]:
        versions = self._versions.get(component_id, [])
        for v in versions:
            if v.is_latest:
                return v
        return None
    
    async def list_versions(
        self,
        component_id: str,
        limit: int = 20,
    ) -> list[ComponentVersion]:
        versions = self._versions.get(component_id, [])
        # 按创建时间倒序
        sorted_versions = sorted(
            versions,
            key=lambda v: v.created_at,
            reverse=True,
        )
        return sorted_versions[:limit]
    
    async def search(self, request: ComponentSearchRequest) -> list[ComponentSearchResult]:
        results = []
        
        for component in self._components.values():
            # 过滤状态
            if request.status and component.status != request.status:
                continue
            
            # 过滤分类
            if request.category and component.category != request.category:
                continue
            
            # 过滤标签
            if request.tags and not all(tag in component.tags for tag in request.tags):
                continue
            
            # 计算相似度
            score, reason = self._calculate_similarity(
                component,
                request.query,
            )
            
            if score >= request.min_similarity:
                latest_version = await self.get_latest_version(component.id)
                results.append(ComponentSearchResult(
                    component=component,
                    version=latest_version,
                    similarity_score=score,
                    match_reason=reason,
                ))
        
        # 按相似度排序
        results.sort(key=lambda r: r.similarity_score, reverse=True)
        return results[:request.limit]
    
    async def match_component(
        self,
        description: str,
        category_hint: Optional[str] = None,
        min_similarity: float = 0.4,
    ) -> Optional[ComponentSearchResult]:
        request = ComponentSearchRequest(
            query=description,
            category=ComponentCategory(category_hint) if category_hint else None,
            min_similarity=min_similarity,
            limit=1,
        )
        
        results = await self.search(request)
        return results[0] if results else None
    
    def _calculate_similarity(
        self,
        component: Component,
        query: str,
    ) -> tuple[float, str]:
        """计算查询与组件的相似度
        
        使用简单的关键词匹配算法。
        在生产环境中应使用语义向量模型。
        """
        if not query:
            return 0.5, "No query provided"
        
        query_lower = query.lower()
        query_words = set(re.findall(r'\w+', query_lower))
        
        # 构建组件文本（包含名称、描述、标签、分类）
        component_text = " ".join([
            component.name,
            component.display_name,
            component.description,
            " ".join(component.tags),
            component.category.value,
        ]).lower()
        
        # 将驼峰命名拆分为单独的词
        component_text = re.sub(r'([a-z])([A-Z])', r'\1 \2', component_text)
        component_text = re.sub(r'[_-]', ' ', component_text)
        
        component_words = set(re.findall(r'\w+', component_text))
        
        # Jaccard 相似度
        if not component_words:
            return 0.0, "Component has no searchable content"
        
        intersection = query_words & component_words
        union = query_words | component_words
        
        similarity = len(intersection) / len(union) if union else 0.0
        
        # 提升名称匹配的权重
        name_lower = component.name.lower()
        # 处理驼峰命名（在转小写之前）
        name_split = re.sub(r'([a-z])([A-Z])', r'\1 \2', component.name)
        name_split = re.sub(r'[_-]', ' ', name_split).lower()
        name_words = set(re.findall(r'\w+', name_split))
        
        reason = "No direct match"  # 默认值
        
        if query_words & name_words or query_lower in name_lower or name_lower in query_lower:
            similarity = min(similarity * 1.5, 1.0)
            reason = f"Name match: {component.name}"
        elif intersection:
            reason = f"Keyword match: {', '.join(intersection)}"
            # 提升描述/标签匹配的权重
            if query_words & set(component.tags):
                similarity = max(similarity, 0.6)
                reason += " (tag match)"
        
        # 检查子串匹配（处理单复数、词形变化等）
        for word in query_words:
            for cword in component_words:
                if word != cword and (word in cword or cword in word):
                    similarity = max(similarity, 0.5)
                    if "Partial" not in reason:
                        reason = f"Partial match: {word}"
                    break
        
        return round(similarity, 3), reason
