"""配置管理"""

from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )
    
    # 应用基础配置
    app_name: str = "PM Workstation"
    app_version: str = "0.1.0"
    debug: bool = False
    
    # LLM模型配置
    default_model: str = "openai"
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    anthropic_base_url: str = "https://api.anthropic.com"
    
    # 数据库配置
    database_url: str = "sqlite:///./pm_workstation.db"
    redis_url: str = "redis://localhost:6379/0"
    
    # 存储配置
    storage_type: str = "local"  # local, minio, s3
    storage_path: str = "./data/deliverables"
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = ""
    minio_secret_key: str = ""
    minio_bucket: str = "pm-workstation"
    
    # 外部系统集成
    jira_base_url: str = ""
    jira_api_token: str = ""
    figma_access_token: str = ""
    github_token: str = ""
    gitlab_token: str = ""
    
    # 性能配置
    max_concurrent_workflows: int = 3
    max_deliverable_size_mb: int = 100
    llm_max_retries: int = 3
    external_api_max_retries: int = 5
    
    def save(self):
        """保存配置到.env文件"""
        env_path = Path(".env")
        content = ""
        for field_name in Settings.model_fields.keys():
            value = getattr(self, field_name)
            if value:
                content += f"{field_name.upper()}={value}\n"
        env_path.write_text(content)


# 全局配置实例
settings = Settings()
