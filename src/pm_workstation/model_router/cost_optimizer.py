"""成本优化器"""


from pm_workstation.model_router.base import LLMResponse
from pm_workstation.model_router.model_selector import ModelProfile, ModelSelector
from pm_workstation.model_router.task_classifier import TaskClassification


class CostOptimizer:
    """成本优化器 - 平衡效果和成本"""

    def __init__(
        self,
        model_selector: ModelSelector,
        budget_limit: float | None = None,  # 预算上限（美元）
    ):
        """初始化成本优化器

        Args:
            model_selector: 模型选择器
            budget_limit: 单次任务预算上限
        """
        self.model_selector = model_selector
        self.budget_limit = budget_limit

    def optimize(
        self,
        task: TaskClassification,
        available_models: list[str] | None = None,
    ) -> str:
        """优化模型选择

        Args:
            task: 任务分类
            available_models: 可用模型列表

        Returns:
            优化后的模型名称
        """
        selected_model = self.model_selector.select_model(task)

        # 检查预算
        if self.budget_limit:
            profile = self.model_selector.get_model_profile(selected_model)
            if profile:
                estimated_cost = self._estimate_cost(profile, task)

                if estimated_cost > self.budget_limit:
                    # 选择更便宜的模型
                    selected_model = self._find_cheapest_within_budget(
                        task,
                        self.budget_limit,
                        available_models,
                    )

        return selected_model

    def estimate_cost(
        self,
        model_name: str,
        task: TaskClassification,
    ) -> float:
        """预估任务成本

        Args:
            model_name: 模型名称
            task: 任务分类

        Returns:
            预估成本（美元）
        """
        profile = self.model_selector.get_model_profile(model_name)
        if not profile:
            return float('inf')

        return self._estimate_cost(profile, task)

    def _estimate_cost(
        self,
        profile: ModelProfile,
        task: TaskClassification,
    ) -> float:
        """计算成本"""
        input_tokens = task.estimated_tokens
        output_tokens = input_tokens * 2

        input_cost = (input_tokens / 1000) * profile.cost_per_1k_input
        output_cost = (output_tokens / 1000) * profile.cost_per_1k_output

        return input_cost + output_cost

    def _find_cheapest_within_budget(
        self,
        task: TaskClassification,
        budget: float,
        available_models: list[str] | None = None,
    ) -> str:
        """在预算内找到最便宜的可用模型

        Args:
            task: 任务分类
            budget: 预算
            available_models: 可用模型列表

        Returns:
            最便宜的模型名称
        """
        candidates = available_models or list(self.model_selector.MODEL_PROFILES.keys())

        valid_models = []
        for model_name in candidates:
            profile = self.model_selector.get_model_profile(model_name)
            if not profile:
                continue

            cost = self._estimate_cost(profile, task)
            if cost <= budget:
                valid_models.append((model_name, profile, cost))

        if not valid_models:
            # 没有符合预算的模型，返回最便宜的
            valid_models = [
                (name, profile, self._estimate_cost(profile, task))
                for name, profile in self.model_selector.MODEL_PROFILES.items()
            ]

        # 返回最便宜的
        cheapest = min(valid_models, key=lambda x: x[2])
        return cheapest[0]

    def track_usage(
        self,
        model_name: str,
        response: LLMResponse,
    ) -> dict:
        """跟踪使用情况

        Args:
            model_name: 模型名称
            response: LLM响应

        Returns:
            使用统计
        """
        profile = self.model_selector.get_model_profile(model_name)
        if not profile or not response.usage:
            return {}

        input_tokens = response.usage.get("prompt_tokens", 0)
        output_tokens = response.usage.get("completion_tokens", 0)

        input_cost = (input_tokens / 1000) * profile.cost_per_1k_input
        output_cost = (output_tokens / 1000) * profile.cost_per_1k_output

        return {
            "model": model_name,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "input_cost": input_cost,
            "output_cost": output_cost,
            "total_cost": input_cost + output_cost,
        }
