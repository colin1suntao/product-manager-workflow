"""LLM 工厂

根据配置创建对应的 LLM 适配器实例。
"""

from pm_workstation.llm.models import LLMProviderConfig, LLMProviderType
from pm_workstation.model_router.base import LLMBackend, LLMConfig


class LLMFactory:
    """LLM 适配器工厂"""

    @staticmethod
    def create_adapter(config: LLMProviderConfig) -> LLMBackend:
        """根据配置创建 LLM 适配器

        Args:
            config: LLM Provider 配置

        Returns:
            LLM 适配器实例

        Raises:
            ValueError: 不支持的 Provider 类型
        """
        llm_config = LLMConfig(
            model=config.default_model,
            api_key=config.api_key,
            base_url=config.base_url,
        )

        if config.provider_type == LLMProviderType.OPENAI:
            from pm_workstation.model_router.openai_adapter import OpenAIAdapter

            return OpenAIAdapter(config=llm_config)
        elif config.provider_type == LLMProviderType.ANTHROPIC:
            from pm_workstation.model_router.anthropic_adapter import AnthropicAdapter

            return AnthropicAdapter(config=llm_config)
        elif config.provider_type == LLMProviderType.CUSTOM:
            if not config.base_url:
                raise ValueError("自定义供应商必须提供 base_url")
            from pm_workstation.model_router.openai_adapter import OpenAIAdapter

            return OpenAIAdapter(config=llm_config)
        else:
            raise ValueError(f"不支持的 Provider 类型: {config.provider_type}")
