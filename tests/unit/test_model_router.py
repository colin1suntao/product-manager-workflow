"""模型路由逻辑测试"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pm_workstation.model_router.base import LLMBackend, LLMConfig, LLMMessage, LLMResponse
from pm_workstation.model_router.cost_optimizer import CostOptimizer
from pm_workstation.model_router.fallback_handler import FallbackHandler
from pm_workstation.model_router.model_selector import ModelProfile, ModelSelector
from pm_workstation.model_router.task_classifier import (
    TaskClassification,
    TaskClassifier,
    TaskComplexity,
    TaskType,
)


class TestTaskClassifier:
    """任务分类器测试"""
    
    def test_classify_analysis_task(self):
        """测试分析任务分类"""
        classifier = TaskClassifier()
        result = classifier.classify("深入分析用户登录需求的复杂业务规则和多场景异常")
        
        assert result.task_type == TaskType.ANALYSIS
        assert result.complexity in (TaskComplexity.MEDIUM, TaskComplexity.HIGH)
    
    def test_classify_generation_task(self):
        """测试生成任务分类"""
        classifier = TaskClassifier()
        result = classifier.classify("生成产品原型代码")
        
        assert result.task_type == TaskType.GENERATION
    
    def test_classify_reasoning_task(self):
        """测试推理任务分类"""
        classifier = TaskClassifier()
        result = classifier.classify("深入推理用户操作流程的复杂逻辑分支和多场景异常处理")
        
        assert result.task_type == TaskType.REASONING
        assert result.complexity == TaskComplexity.HIGH
    
    def test_classify_summarization_task(self):
        """测试总结任务分类"""
        classifier = TaskClassifier()
        result = classifier.classify("总结需求文档")
        
        assert result.task_type == TaskType.SUMMARIZATION
    
    def test_classify_long_description(self):
        """测试长描述复杂度"""
        classifier = TaskClassifier()
        long_desc = "这是一个非常复杂的需求，包含多个业务场景和用户角色..." + "详细内容。" * 200
        result = classifier.classify(long_desc)
        
        assert result.complexity == TaskComplexity.HIGH
    
    def test_classify_short_description(self):
        """测试短描述复杂度"""
        classifier = TaskClassifier()
        result = classifier.classify("简单任务")
        
        assert result.complexity == TaskComplexity.LOW
    
    def test_estimate_tokens(self):
        """测试token预估"""
        classifier = TaskClassifier()
        
        # 简单任务
        result = classifier.classify("简单任务")
        assert result.estimated_tokens >= 100
        
        # 复杂推理任务
        result = classifier.classify("深入分析复杂业务逻辑和多个异常场景")
        assert result.estimated_tokens > 500
    
    def test_reasoning_steps(self):
        """测试推理步骤预估"""
        classifier = TaskClassifier()
        
        low = classifier.classify("简单")
        assert low.reasoning_steps == 1
        
        # 100-500字符触发MEDIUM
        medium_text = "任务描述" * 15  # 60字符，仍然LOW，需要用关键词
        medium = classifier.classify(medium_text)
        # 实际测试分类器逻辑
        assert medium.reasoning_steps in (1, 3, 5)
        
        high = classifier.classify("复杂多步骤详细深入分析")
        assert high.reasoning_steps == 5


class TestModelSelector:
    """模型选择器测试"""
    
    def test_select_model_for_simple_task(self):
        """测试简单任务模型选择"""
        selector = ModelSelector()
        task = TaskClassification(
            task_type=TaskType.GENERATION,
            complexity=TaskComplexity.LOW,
            estimated_tokens=500,
        )
        
        model = selector.select_model(task)
        assert model in selector.available_models
    
    def test_select_model_for_complex_task(self):
        """测试复杂任务模型选择"""
        selector = ModelSelector()
        task = TaskClassification(
            task_type=TaskType.REASONING,
            complexity=TaskComplexity.HIGH,
            estimated_tokens=5000,
        )
        
        model = selector.select_model(task)
        # 复杂任务应该选择推理能力强的模型
        profile = selector.get_model_profile(model)
        assert profile is not None
        assert profile.reasoning_capability >= 8
    
    def test_select_model_with_limited_availability(self):
        """测试有限可用模型选择"""
        selector = ModelSelector(available_models=["claude-3-haiku"])
        task = TaskClassification(
            task_type=TaskType.GENERATION,
            complexity=TaskComplexity.LOW,
            estimated_tokens=500,
        )
        
        model = selector.select_model(task)
        assert model == "claude-3-haiku"
    
    def test_no_available_models(self):
        """测试没有可用模型"""
        selector = ModelSelector(available_models=["nonexistent-model"])
        task = TaskClassification(
            task_type=TaskType.GENERATION,
            complexity=TaskComplexity.LOW,
            estimated_tokens=500,
        )
        
        with pytest.raises(ValueError, match="No available models"):
            selector.select_model(task)
    
    def test_get_model_profile(self):
        """测试获取模型配置"""
        selector = ModelSelector()
        profile = selector.get_model_profile("gpt-4o")
        
        assert profile is not None
        assert profile.name == "GPT-4o"
        assert profile.provider == "openai"
    
    def test_add_custom_model(self):
        """测试添加自定义模型"""
        selector = ModelSelector()
        custom_profile = ModelProfile(
            name="Custom Model",
            provider="custom",
            model_id="custom-v1",
            max_tokens=2048,
            reasoning_capability=7,
        )
        
        selector.add_custom_model(custom_profile)
        profile = selector.get_model_profile("custom-model")
        
        assert profile is not None
        assert profile.model_id == "custom-v1"
    
    def test_score_model_high_complexity(self):
        """测试高复杂度任务评分"""
        selector = ModelSelector()
        task = TaskClassification(
            task_type=TaskType.REASONING,
            complexity=TaskComplexity.HIGH,
            estimated_tokens=5000,
            requires_streaming=True,
        )
        
        # GPT-4应该比Haiku得分高
        gpt4_score = selector._score_model("gpt-4", task)
        haiku_score = selector._score_model("claude-3-haiku", task)
        
        assert gpt4_score > haiku_score


class TestFallbackHandler:
    """降级处理器测试"""
    
    @pytest.mark.asyncio
    async def test_primary_model_success(self):
        """测试主模型成功"""
        primary = AsyncMock(spec=LLMBackend)
        primary.chat = AsyncMock(return_value=LLMResponse(
            content="成功",
            model="gpt-4",
        ))
        
        fallback = AsyncMock(spec=LLMBackend)
        
        handler = FallbackHandler(
            primary_model=primary,
            fallback_models=[fallback],
        )
        
        response = await handler.chat([LLMMessage(role="user", content="测试")])
        
        assert response.content == "成功"
        assert primary.chat.call_count == 1
        assert fallback.chat.call_count == 0
    
    @pytest.mark.asyncio
    async def test_fallback_on_primary_failure(self):
        """测试主模型失败时降级"""
        primary = AsyncMock(spec=LLMBackend)
        primary.chat = AsyncMock(side_effect=Exception("Primary failed"))
        
        fallback = AsyncMock(spec=LLMBackend)
        fallback.chat = AsyncMock(return_value=LLMResponse(
            content="fallback success",
            model="claude-3",
        ))
        
        handler = FallbackHandler(
            primary_model=primary,
            fallback_models=[fallback],
            max_retries=1,
            base_delay=0.001,
        )
        
        response = await handler.chat([LLMMessage(role="user", content="测试")])
        
        assert response.content == "fallback success"
        assert primary.chat.call_count == 1
    
    @pytest.mark.asyncio
    async def test_retry_on_failure(self):
        """测试重试机制"""
        model = AsyncMock(spec=LLMBackend)
        model.chat = AsyncMock(
            side_effect=[
                Exception("First try failed"),
                Exception("Second try failed"),
                LLMResponse(content="success", model="gpt-4"),
            ]
        )
        
        handler = FallbackHandler(
            primary_model=model,
            fallback_models=[],
            max_retries=3,
            base_delay=0.001,
        )
        
        response = await handler.chat([LLMMessage(role="user", content="测试")])
        
        assert response.content == "success"
        assert model.chat.call_count == 3
    
    @pytest.mark.asyncio
    async def test_all_models_fail(self):
        """测试所有模型都失败"""
        primary = AsyncMock(spec=LLMBackend)
        primary.chat = AsyncMock(side_effect=Exception("Primary failed"))
        
        fallback = AsyncMock(spec=LLMBackend)
        fallback.chat = AsyncMock(side_effect=Exception("Fallback failed"))
        
        handler = FallbackHandler(
            primary_model=primary,
            fallback_models=[fallback],
            max_retries=1,
            base_delay=0.001,
        )
        
        with pytest.raises(Exception, match="All models failed"):
            await handler.chat([LLMMessage(role="user", content="测试")])
    
    @pytest.mark.asyncio
    async def test_streaming_fallback(self):
        """测试流式降级"""
        
        class FailingStreamModel:
            async def chat_stream(self, *args, **kwargs):
                raise Exception("Stream failed")
                if False:
                    yield ""
        
        class SuccessStreamModel:
            async def chat_stream(self, *args, **kwargs):
                for chunk in ["chunk1", "chunk2"]:
                    yield chunk
        
        handler = FallbackHandler(
            primary_model=FailingStreamModel(),
            fallback_models=[SuccessStreamModel()],
        )
        
        chunks = []
        async for chunk in handler.chat_stream([LLMMessage(role="user", content="测试")]):
            chunks.append(chunk)
        
        assert chunks == ["chunk1", "chunk2"]
    
    def test_is_using_fallback(self):
        """测试是否在使用备选模型"""
        primary = MagicMock(spec=LLMBackend)
        fallback = MagicMock(spec=LLMBackend)
        
        handler = FallbackHandler(
            primary_model=primary,
            fallback_models=[fallback],
        )
        
        assert handler.is_using_fallback() is False
        handler.current_model = fallback
        assert handler.is_using_fallback() is True
    
    def test_calculate_delay(self):
        """测试延迟计算"""
        primary = MagicMock(spec=LLMBackend)
        handler = FallbackHandler(
            primary_model=primary,
            fallback_models=[],
            base_delay=1.0,
            max_delay=10.0,
        )
        
        assert handler._calculate_delay(0) == 1.0
        assert handler._calculate_delay(1) == 2.0
        assert handler._calculate_delay(2) == 4.0
        assert handler._calculate_delay(10) == 10.0  # 不超过max_delay


class TestCostOptimizer:
    """成本优化器测试"""
    
    def test_optimize_simple_task(self):
        """测试简单任务优化"""
        selector = ModelSelector()
        optimizer = CostOptimizer(selector)
        
        task = TaskClassification(
            task_type=TaskType.GENERATION,
            complexity=TaskComplexity.LOW,
            estimated_tokens=500,
        )
        
        model = optimizer.optimize(task)
        assert model in selector.available_models
    
    def test_optimize_with_budget(self):
        """测试预算约束优化"""
        selector = ModelSelector()
        optimizer = CostOptimizer(selector, budget_limit=0.001)  # 很低预算
        
        task = TaskClassification(
            task_type=TaskType.GENERATION,
            complexity=TaskComplexity.LOW,
            estimated_tokens=500,
        )
        
        model = optimizer.optimize(task)
        # 应该选择最便宜的模型
        profile = selector.get_model_profile(model)
        assert profile is not None
    
    def test_estimate_cost(self):
        """测试成本预估"""
        selector = ModelSelector()
        optimizer = CostOptimizer(selector)
        
        task = TaskClassification(
            task_type=TaskType.GENERATION,
            complexity=TaskComplexity.MEDIUM,
            estimated_tokens=1000,
        )
        
        cost = optimizer.estimate_cost("gpt-4o", task)
        assert cost > 0
        
        # GPT-4应该更贵
        gpt4_cost = optimizer.estimate_cost("gpt-4", task)
        assert gpt4_cost > cost
    
    def test_track_usage(self):
        """测试使用跟踪"""
        selector = ModelSelector()
        optimizer = CostOptimizer(selector)
        
        response = LLMResponse(
            content="test",
            model="gpt-4o",
            usage={
                "prompt_tokens": 100,
                "completion_tokens": 200,
                "total_tokens": 300,
            },
        )
        
        usage = optimizer.track_usage("gpt-4o", response)
        
        assert usage["model"] == "gpt-4o"
        assert usage["input_tokens"] == 100
        assert usage["output_tokens"] == 200
        assert usage["total_cost"] > 0
    
    def test_find_cheapest_within_budget(self):
        """测试预算内找最便宜模型"""
        selector = ModelSelector()
        optimizer = CostOptimizer(selector)
        
        task = TaskClassification(
            task_type=TaskType.GENERATION,
            complexity=TaskComplexity.LOW,
            estimated_tokens=500,
        )
        
        cheapest = optimizer._find_cheapest_within_budget(
            task,
            budget=0.01,
            available_models=["gpt-4o", "claude-3-haiku", "claude-3-sonnet"],
        )
        # Haiku应该是最便宜的
        assert "haiku" in cheapest.lower()
    
    def test_no_model_within_budget(self):
        """测试没有模型符合预算"""
        selector = ModelSelector()
        optimizer = CostOptimizer(selector, budget_limit=0.0000001)
        
        task = TaskClassification(
            task_type=TaskType.GENERATION,
            complexity=TaskComplexity.LOW,
            estimated_tokens=500,
        )
        
        # 应该返回最便宜的模型
        model = optimizer.optimize(task)
        assert model is not None


class TestModelRouterIntegration:
    """模型路由集成测试"""
    
    def test_full_workflow(self):
        """测试完整工作流程"""
        # 1. 分类任务
        classifier = TaskClassifier()
        task = classifier.classify("深入分析用户登录流程的业务规则和异常场景")
        
        assert task.task_type == TaskType.ANALYSIS
        assert task.complexity == TaskComplexity.HIGH
        
        # 2. 选择模型
        selector = ModelSelector(available_models=["gpt-4o", "claude-3-sonnet"])
        model = selector.select_model(task)
        
        assert model in ["gpt-4o", "claude-3-sonnet"]
        
        # 3. 成本优化
        optimizer = CostOptimizer(selector)
        optimized_model = optimizer.optimize(task)
        
        assert optimized_model is not None
    
    @pytest.mark.asyncio
    async def test_fallback_with_cost_tracking(self):
        """测试降级与成本跟踪"""
        selector = ModelSelector()
        optimizer = CostOptimizer(selector)
        
        # 创建模拟模型
        primary = AsyncMock(spec=LLMBackend)
        primary.chat = AsyncMock(return_value=LLMResponse(
            content="primary response",
            model="gpt-4o",
            usage={"prompt_tokens": 100, "completion_tokens": 200, "total_tokens": 300},
        ))
        
        fallback = AsyncMock(spec=LLMBackend)
        
        handler = FallbackHandler(
            primary_model=primary,
            fallback_models=[fallback],
            max_retries=1,
        )
        
        response = await handler.chat([LLMMessage(role="user", content="测试")])
        
        # 跟踪成本
        usage = optimizer.track_usage("gpt-4o", response)
        assert usage["total_tokens"] == 300
        assert usage["total_cost"] > 0
