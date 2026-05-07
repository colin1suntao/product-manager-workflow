"""模型选择器"""


from pydantic import BaseModel

from pm_workstation.model_router.task_classifier import TaskClassification, TaskComplexity


class ModelProfile(BaseModel):
    """模型配置档案"""
    name: str
    provider: str  # openai, anthropic
    model_id: str
    max_tokens: int
    supports_streaming: bool = True
    cost_per_1k_input: float = 0.0  # 每1k输入token成本
    cost_per_1k_output: float = 0.0  # 每1k输出token成本
    reasoning_capability: int = 5  # 推理能力评分 (1-10)


class ModelSelector:
    """模型选择器"""

    # 预定义模型配置
    MODEL_PROFILES = {
        "gpt-4o": ModelProfile(
            name="GPT-4o",
            provider="openai",
            model_id="gpt-4o",
            max_tokens=4096,
            cost_per_1k_input=0.005,
            cost_per_1k_output=0.015,
            reasoning_capability=9,
        ),
        "gpt-4": ModelProfile(
            name="GPT-4",
            provider="openai",
            model_id="gpt-4",
            max_tokens=8192,
            cost_per_1k_input=0.03,
            cost_per_1k_output=0.06,
            reasoning_capability=10,
        ),
        "claude-3-opus": ModelProfile(
            name="Claude 3 Opus",
            provider="anthropic",
            model_id="claude-3-opus-20240229",
            max_tokens=4096,
            cost_per_1k_input=0.015,
            cost_per_1k_output=0.075,
            reasoning_capability=10,
        ),
        "claude-3-sonnet": ModelProfile(
            name="Claude 3 Sonnet",
            provider="anthropic",
            model_id="claude-3-sonnet-20240229",
            max_tokens=4096,
            cost_per_1k_input=0.003,
            cost_per_1k_output=0.015,
            reasoning_capability=8,
        ),
        "claude-3-haiku": ModelProfile(
            name="Claude 3 Haiku",
            provider="anthropic",
            model_id="claude-3-haiku-20240307",
            max_tokens=4096,
            cost_per_1k_input=0.00025,
            cost_per_1k_output=0.00125,
            reasoning_capability=6,
        ),
    }

    def __init__(self, available_models: list[str] | None = None):
        """初始化模型选择器

        Args:
            available_models: 可用模型列表，None时使用所有预定义模型
        """
        self.available_models = available_models or list(self.MODEL_PROFILES.keys())

    def select_model(self, task: TaskClassification) -> str:
        """根据任务选择最优模型

        Args:
            task: 任务分类结果

        Returns:
            选中的模型名称
        """
        candidates = self._filter_available()

        if not candidates:
            raise ValueError("No available models")

        # 根据任务类型和复杂度评分
        scored_models = [
            (model, self._score_model(model, task))
            for model in candidates
        ]

        # 返回评分最高的模型
        best_model = max(scored_models, key=lambda x: x[1])
        return best_model[0]

    def _filter_available(self) -> list[str]:
        """过滤可用模型"""
        return [
            model for model in self.available_models
            if model in self.MODEL_PROFILES
        ]

    def _score_model(self, model_name: str, task: TaskClassification) -> float:
        """为模型评分

        Args:
            model_name: 模型名称
            task: 任务分类

        Returns:
            评分 (越高越好)
        """
        profile = self.MODEL_PROFILES[model_name]
        score = 0.0

        # 推理能力匹配 (权重 40%)
        required_capability = {
            TaskComplexity.LOW: 3,
            TaskComplexity.MEDIUM: 6,
            TaskComplexity.HIGH: 8,
        }.get(task.complexity, 5)

        capability_score = min(profile.reasoning_capability / required_capability, 1.0)
        score += capability_score * 0.4

        # 成本效率 (权重 30%)
        estimated_cost = self._estimate_cost(profile, task)
        # 成本越低，分数越高 (归一化到0-1)
        cost_score = max(0, 1.0 - (estimated_cost / 1.0))
        score += cost_score * 0.3

        # 功能匹配 (权重 30%)
        feature_score = 0.0

        # 流式支持
        if task.requires_streaming and profile.supports_streaming:
            feature_score += 0.5

        # Token限制
        if profile.max_tokens >= task.estimated_tokens:
            feature_score += 0.5

        score += feature_score * 0.3

        return score

    def _estimate_cost(
        self,
        profile: ModelProfile,
        task: TaskClassification,
    ) -> float:
        """预估成本

        Args:
            profile: 模型配置
            task: 任务分类

        Returns:
            预估成本 (美元)
        """
        input_tokens = task.estimated_tokens
        output_tokens = input_tokens * 2  # 假设输出是输入的2倍

        input_cost = (input_tokens / 1000) * profile.cost_per_1k_input
        output_cost = (output_tokens / 1000) * profile.cost_per_1k_output

        return input_cost + output_cost

    def get_model_profile(self, model_name: str) -> ModelProfile | None:
        """获取模型配置

        Args:
            model_name: 模型名称

        Returns:
            模型配置
        """
        return self.MODEL_PROFILES.get(model_name)

    def add_custom_model(self, profile: ModelProfile):
        """添加自定义模型

        Args:
            profile: 模型配置
        """
        self.MODEL_PROFILES[profile.name.lower().replace(" ", "-")] = profile
