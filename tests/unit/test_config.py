"""配置模块测试"""

import os
from pathlib import Path

import pytest

from pm_workstation.config import Settings


class TestSettings:
    """Settings配置测试"""
    
    def test_default_values(self):
        """测试默认配置值"""
        settings = Settings()
        
        assert settings.app_name == "PM Workstation"
        assert settings.app_version == "0.1.0"
        assert settings.debug is False
        assert settings.default_model == "openai"
        assert settings.database_url == "sqlite:///./pm_workstation.db"
        assert settings.redis_url == "redis://localhost:6379/0"
        assert settings.storage_type == "local"
        assert settings.max_concurrent_workflows == 3
        assert settings.max_deliverable_size_mb == 100
    
    def test_env_file_loading(self, tmp_path):
        """测试从.env文件加载配置"""
        env_file = tmp_path / ".env"
        env_file.write_text("DEFAULT_MODEL=anthropic\nDEBUG=true\n")
        
        # 切换到临时目录
        original_cwd = os.getcwd()
        os.chdir(tmp_path)
        
        try:
            settings = Settings(_env_file=env_file)
            assert settings.default_model == "anthropic"
            assert settings.debug is True
        finally:
            os.chdir(original_cwd)
    
    def test_save_config(self, tmp_path):
        """测试保存配置到.env文件"""
        settings = Settings(
            default_model="anthropic",
            openai_api_key="test-key"
        )
        
        # 切换到临时目录
        original_cwd = os.getcwd()
        os.chdir(tmp_path)
        
        try:
            settings.save()
            env_path = Path(".env")
            assert env_path.exists()
            
            content = env_path.read_text()
            assert "DEFAULT_MODEL=anthropic" in content
            assert "OPENAI_API_KEY=test-key" in content
        finally:
            os.chdir(original_cwd)
    
    def test_case_insensitive_env(self, tmp_path):
        """测试环境变量大小写不敏感"""
        env_file = tmp_path / ".env"
        env_file.write_text("default_model=anthropic\n")
        
        original_cwd = os.getcwd()
        os.chdir(tmp_path)
        
        try:
            settings = Settings(_env_file=env_file)
            assert settings.default_model == "anthropic"
        finally:
            os.chdir(original_cwd)
