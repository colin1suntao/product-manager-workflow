"""SQLAlchemy ORM模型"""

from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, Enum, Integer, String, Text
from sqlalchemy.orm import relationship

from pm_workstation.models.core import WorkflowStatus
from pm_workstation.models.database import Base


class WorkflowRunORM(Base):
    """工作流运行记录ORM模型"""
    
    __tablename__ = "workflow_runs"
    
    id = Column(String(64), primary_key=True, index=True, comment="唯一标识")
    user_id = Column(String(64), index=True, comment="用户ID")
    requirement_text = Column(Text, nullable=False, comment="原始需求文本")
    status = Column(
        Enum(WorkflowStatus),
        default=WorkflowStatus.INIT,
        nullable=False,
        comment="当前状态",
    )
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, comment="更新时间")
    
    # JSON字段存储复杂数据
    structured_requirement = Column(JSON, nullable=True, comment="结构化需求")
    verification_report = Column(JSON, nullable=True, comment="校验报告")
    
    # URL字段
    prototype_url = Column(String(512), nullable=True, comment="原型访问URL")
    prd_document_url = Column(String(512), nullable=True, comment="PRD文档URL")
    
    # 错误信息
    error_message = Column(Text, nullable=True, comment="错误信息")


class ComponentORM(Base):
    """组件ORM模型"""
    
    __tablename__ = "components"
    
    id = Column(String(64), primary_key=True, index=True, comment="组件ID")
    name = Column(String(128), nullable=False, index=True, comment="组件名称")
    version = Column(String(32), nullable=False, comment="版本号")
    
    # 组件内容
    html_template = Column(Text, nullable=False, comment="HTML模板")
    css_styles = Column(Text, nullable=False, comment="CSS样式")
    js_interactions = Column(Text, nullable=False, comment="JS交互逻辑")
    
    # 元数据
    props = Column(JSON, nullable=False, comment="属性定义")
    tags = Column(JSON, nullable=False, comment="标签")
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, comment="更新时间")
