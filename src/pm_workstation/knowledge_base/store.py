import logging
from datetime import datetime

from pm_workstation.knowledge_base.models import Template, TemplateType

logger = logging.getLogger(__name__)


class TemplateStore:
    def __init__(self):
        self._templates: dict[str, Template] = {}
        self._load_defaults()

    def _load_defaults(self) -> None:
        defaults = [
            Template(
                id="default-doc-1",
                name="标准 PRD 模板",
                description="标准的产品需求文档模板，包含完整的 PRD 章节结构",
                type=TemplateType.DOCUMENT,
                content="""你是一个专业的产品经理。请根据需求生成标准 PRD 文档。

## PRD 文档结构

### 1. 文档概述
- 文档版本历史
- 产品背景与目标
- 目标用户群体
- 成功指标 (OKR/KPI)

### 2. 功能需求
- 功能列表（按优先级排序：P0/P1/P2）
- 每个功能的详细描述
- 用户故事 (User Story)
- 验收标准 (Acceptance Criteria)

### 3. 交互流程
- 用户流程图
- 页面流转说明
- 异常流程处理

### 4. 数据需求
- 数据模型
- 数据字段定义
- 数据校验规则

### 5. 非功能需求
- 性能要求
- 安全要求
- 兼容性要求
- 可访问性要求

### 6. 附录
- 术语表
- 参考资料
- 待确认事项""",
                tags=["PRD", "标准", "完整"],
            ),
            Template(
                id="default-doc-2",
                name="敏捷需求模板",
                description="适用于敏捷开发团队的精简需求文档模板",
                type=TemplateType.DOCUMENT,
                content="""你是一个敏捷产品经理。请根据需求生成敏捷需求文档。

## 文档结构

### 1. Epic / Feature 概述
- 一句话描述
- 业务价值
- 关联目标

### 2. User Stories
- 每个 Story 格式：As a [角色], I want [功能], so that [价值]
- 优先级标注 (Must/Should/Could/Won't)
- 估算 (Story Points)

### 3. 验收条件 (Acceptance Criteria)
- Given/When/Then 格式
- 正常流程
- 异常流程

### 4. 设计稿 / 原型参考
- 相关链接

### 5. 技术备注
- 依赖服务
- 数据变更
- 埋点需求""",
                tags=["敏捷", "Scrum", "精简"],
            ),
        ]
        for t in defaults:
            self._templates[t.id] = t

    async def list_all(self, type_filter: TemplateType | None = None) -> list[Template]:
        if type_filter:
            return [t for t in self._templates.values() if t.type == type_filter]
        return list(self._templates.values())

    async def get(self, template_id: str) -> Template | None:
        return self._templates.get(template_id)

    async def create(self, template: Template) -> Template:
        self._templates[template.id] = template
        return template

    async def update(self, template_id: str, updates: dict) -> Template | None:
        template = self._templates.get(template_id)
        if not template:
            return None
        for key, value in updates.items():
            if hasattr(template, key) and value is not None:
                setattr(template, key, value)
        template.updated_at = datetime.now()
        return template

    async def delete(self, template_id: str) -> bool:
        return self._templates.pop(template_id, None) is not None
