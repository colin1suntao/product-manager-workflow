"""数据库和存储测试"""

import io
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from pm_workstation.models.core import WorkflowStatus, WorkflowRun
from pm_workstation.models.database import Base, get_db, init_db
from pm_workstation.models.orm import WorkflowRunORM
from pm_workstation.storage.base import StorageObject
from pm_workstation.storage.local import LocalStorage


class TestDatabase:
    """数据库测试"""
    
    @pytest.fixture
    def db_engine(self, tmp_path):
        """创建临时数据库引擎"""
        db_path = tmp_path / "test.db"
        engine = create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(engine)
        return engine
    
    @pytest.fixture
    def db_session(self, db_engine):
        """创建数据库会话"""
        Session = sessionmaker(bind=db_engine)
        session = Session()
        try:
            yield session
        finally:
            session.close()
    
    def test_create_tables(self, db_engine):
        """测试创建表"""
        # 检查表是否创建成功
        from sqlalchemy import inspect
        inspector = inspect(db_engine)
        tables = inspector.get_table_names()
        
        assert "workflow_runs" in tables
        assert "components" in tables
    
    def test_create_workflow_run(self, db_session):
        """测试创建工作流运行记录"""
        run_orm = WorkflowRunORM(
            id="run-001",
            user_id="user-123",
            requirement_text="测试需求",
            status=WorkflowStatus.INIT,
        )
        
        db_session.add(run_orm)
        db_session.commit()
        
        # 查询验证
        result = db_session.query(WorkflowRunORM).filter_by(id="run-001").first()
        assert result is not None
        assert result.user_id == "user-123"
        assert result.requirement_text == "测试需求"
        assert result.status == WorkflowStatus.INIT
    
    def test_update_workflow_status(self, db_session):
        """测试更新工作流状态"""
        run_orm = WorkflowRunORM(
            id="run-002",
            user_id="user-123",
            requirement_text="测试需求",
            status=WorkflowStatus.INIT,
        )
        
        db_session.add(run_orm)
        db_session.commit()
        
        # 更新状态
        run_orm.status = WorkflowStatus.PARSING
        db_session.commit()
        
        # 验证更新
        result = db_session.query(WorkflowRunORM).filter_by(id="run-002").first()
        assert result.status == WorkflowStatus.PARSING
    
    def test_store_structured_requirement(self, db_session):
        """测试存储结构化需求JSON"""
        from pm_workstation.models.core import (
            RuleTreeNode,
            StructuredRequirement,
        )
        
        requirement = StructuredRequirement(
            rules=RuleTreeNode(rule_text="业务规则")
        )
        
        run_orm = WorkflowRunORM(
            id="run-003",
            user_id="user-123",
            requirement_text="测试需求",
            structured_requirement=requirement.model_dump(),
        )
        
        db_session.add(run_orm)
        db_session.commit()
        
        # 验证JSON存储
        result = db_session.query(WorkflowRunORM).filter_by(id="run-003").first()
        assert result.structured_requirement is not None
        assert result.structured_requirement["rules"]["rule_text"] == "业务规则"
    
    def test_query_by_user_id(self, db_session):
        """测试按用户ID查询"""
        # 创建多条记录
        for i in range(3):
            run_orm = WorkflowRunORM(
                id=f"run-{i}",
                user_id="user-123",
                requirement_text=f"测试需求{i}",
            )
            db_session.add(run_orm)
        
        db_session.commit()
        
        # 查询
        results = db_session.query(WorkflowRunORM).filter_by(user_id="user-123").all()
        assert len(results) == 3


class TestLocalStorage:
    """本地存储测试"""
    
    @pytest.fixture
    def storage(self, tmp_path):
        """创建临时存储"""
        return LocalStorage(base_path=str(tmp_path))
    
    @pytest.mark.asyncio
    async def test_upload_file(self, storage):
        """测试上传文件"""
        data = io.BytesIO(b"test content")
        result = await storage.upload(
            key="test.txt",
            data=data,
            content_type="text/plain",
        )
        
        assert result.key == "test.txt"
        assert result.size == 12
        assert result.content_type == "text/plain"
    
    @pytest.mark.asyncio
    async def test_download_file(self, storage):
        """测试下载文件"""
        # 先上传
        data = io.BytesIO(b"test content")
        await storage.upload(key="test.txt", data=data)
        
        # 再下载
        downloaded = await storage.download("test.txt")
        assert downloaded.read() == b"test content"
    
    @pytest.mark.asyncio
    async def test_delete_file(self, storage):
        """测试删除文件"""
        # 先上传
        data = io.BytesIO(b"test content")
        await storage.upload(key="test.txt", data=data)
        
        # 删除
        result = await storage.delete("test.txt")
        assert result is True
        
        # 验证不存在
        exists = await storage.exists("test.txt")
        assert exists is False
    
    @pytest.mark.asyncio
    async def test_delete_nonexistent_file(self, storage):
        """测试删除不存在的文件"""
        result = await storage.delete("nonexistent.txt")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_file_exists(self, storage):
        """测试文件存在检查"""
        # 上传文件
        data = io.BytesIO(b"test content")
        await storage.upload(key="test.txt", data=data)
        
        # 检查存在
        exists = await storage.exists("test.txt")
        assert exists is True
        
        # 检查不存在
        exists = await storage.exists("nonexistent.txt")
        assert exists is False
    
    @pytest.mark.asyncio
    async def test_get_url(self, storage):
        """测试获取URL"""
        data = io.BytesIO(b"test content")
        await storage.upload(key="test.txt", data=data)
        
        url = await storage.get_url("test.txt")
        assert url.startswith("file://")
        assert "test.txt" in url
    
    @pytest.mark.asyncio
    async def test_upload_nested_path(self, storage):
        """测试上传到嵌套路径"""
        data = io.BytesIO(b"nested content")
        result = await storage.upload(
            key="nested/path/test.txt",
            data=data,
        )
        
        assert result.key == "nested/path/test.txt"
        assert result.size == 14
        
        # 验证文件存在
        exists = await storage.exists("nested/path/test.txt")
        assert exists is True


class TestStorageFactory:
    """存储工厂测试"""
    
    def test_get_local_storage(self):
        """测试获取本地存储"""
        from pm_workstation.storage.factory import get_storage
        
        storage = get_storage(storage_type="local")
        assert isinstance(storage, LocalStorage)
    
    def test_get_default_storage(self):
        """测试获取默认存储"""
        from pm_workstation.storage.factory import get_storage
        
        # 默认应该是local
        storage = get_storage()
        assert isinstance(storage, LocalStorage)
    
    def test_get_unknown_storage(self):
        """测试获取未知存储类型"""
        from pm_workstation.storage.factory import get_storage
        
        with pytest.raises(ValueError, match="Unknown storage type"):
            get_storage(storage_type="unknown")
