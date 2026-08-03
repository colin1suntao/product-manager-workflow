import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class TemplateType(StrEnum):
    PROTOTYPE = "prototype"
    DOCUMENT = "document"


TEMPLATE_TYPE_LABELS: dict[TemplateType, str] = {
    TemplateType.PROTOTYPE: "原型组件模板",
    TemplateType.DOCUMENT: "产品文档模板",
}


class Template(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str
    description: str = ""
    type: TemplateType
    content: str = ""
    tags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
