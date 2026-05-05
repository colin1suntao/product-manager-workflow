"""适配器注册表

管理所有集成适配器的注册和获取。
"""

from typing import Type

from pm_workstation.integrations.adapters.base import BaseIntegrationAdapter
from pm_workstation.integrations.models import IntegrationConfig, IntegrationType

_adapter_registry: dict[IntegrationType, Type[BaseIntegrationAdapter]] = {}


def register_adapter(
    integration_type: IntegrationType,
) -> callable:
    """注册适配器装饰器

    Args:
        integration_type: 对应的集成类型

    Returns:
        装饰器函数
    """
    def decorator(adapter_cls: Type[BaseIntegrationAdapter]) -> Type[BaseIntegrationAdapter]:
        _adapter_registry[integration_type] = adapter_cls
        return adapter_cls
    return decorator


def get_adapter(config: IntegrationConfig) -> BaseIntegrationAdapter:
    """获取集成适配器实例

    Args:
        config: 集成配置

    Returns:
        适配器实例

    Raises:
        ValueError: 当不支持该集成类型时
    """
    adapter_cls = _adapter_registry.get(config.integration_type)
    if adapter_cls is None:
        raise ValueError(
            f"No adapter registered for integration type: {config.integration_type.value}"
        )
    return adapter_cls(config)


def list_registered_adapters() -> dict[str, str]:
    """列出所有已注册的适配器

    Returns:
        适配器名称映射 {类型值: 适配器名称}
    """
    return {
        type_val.value: cls(config=IntegrationConfig(
            id="", name="", integration_type=type_val
        )).name
        for type_val, cls in _adapter_registry.items()
    }


def auto_discover_adapters() -> None:
    """自动发现并注册所有内置适配器

    导入所有适配器子模块以触发装饰器注册。
    """
    from pm_workstation.integrations.adapters import (  # noqa: F401
        jira_adapter,
        trello_adapter,
        feishu_adapter,
        figma_adapter,
        sketch_adapter,
        github_adapter,
        gitlab_adapter,
    )
