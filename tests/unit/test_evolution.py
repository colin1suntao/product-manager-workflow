"""自我进化功能测试"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock

from pm_workstation.agents.evolution.evolution_models import (
    ExperienceQuality,
    ExperienceType,
    AgentEvolutionConfig,
    EvolutionStatus,
)
from pm_workstation.agents.evolution.experience_collector import ExperienceCollector
from pm_workstation.agents.evolution.evolution_manager import AgentEvolutionManager
from pm_workstation.orchestrator.workflow_state import WorkflowState
from pm_workstation.models.core import WorkflowRun, WorkflowStatus


class TestExperienceCollector:
    """经验收集器测试"""
    
    def test_collect_from_successful_workflow(self, tmp_path):
        """测试从成功的工作流中收集经验"""
        collector = ExperienceCollector(storage_dir=str(tmp_path / "experiences"))
        
        # 创建工作流状态
        run = WorkflowRun(
            id="test-wf-1",
            user_id="test-user",
            requirement_text="创建一个博客系统",
            status=WorkflowStatus.COMPLETED,
        )
        state = WorkflowState(workflow_run=run)
        state.prototype_html = "<html>...</html>"
        state.prd_document = "# PRD 文档"
        
        # 收集经验
        experience = collector.collect_from_workflow(state)
        
        assert experience.success is True
        assert experience.quality in [ExperienceQuality.EXCELLENT, ExperienceQuality.GOOD]
        assert experience.task_type in ["prototype_generation", "document_generation", "general_task"]
    
    def test_collect_from_failed_workflow(self, tmp_path):
        """测试从失败的工作流中收集经验"""
        collector = ExperienceCollector(storage_dir=str(tmp_path / "experiences"))
        
        run = WorkflowRun(
            id="test-wf-2",
            user_id="test-user",
            requirement_text="测试需求",
            status=WorkflowStatus.FAILED,
            error_message="Test error",
        )
        state = WorkflowState(workflow_run=run)
        
        experience = collector.collect_from_workflow(state)
        
        assert experience.success is False
        assert experience.quality == ExperienceQuality.POOR
        assert experience.error_message == "Test error"
    
    def test_list_experiences(self, tmp_path):
        """测试列出经验"""
        collector = ExperienceCollector(storage_dir=str(tmp_path / "experiences"))
        
        # 创建多个经验
        for i in range(5):
            run = WorkflowRun(
                id=f"test-wf-{i}",
                user_id="test-user",
                requirement_text=f"测试需求 {i}",
                status=WorkflowStatus.COMPLETED,
            )
            state = WorkflowState(workflow_run=run)
            collector.collect_from_workflow(state)
        
        # 列出所有经验
        experiences = collector.list_experiences(limit=10)
        assert len(experiences) == 5
        
        # 过滤成功的经验
        successful = collector.list_experiences(success=True)
        assert len(successful) == 5


class TestEvolutionManager:
    """进化管理器测试"""
    
    def test_collect_experience(self, tmp_path):
        """测试收集经验"""
        manager = AgentEvolutionManager(storage_dir=str(tmp_path / "evolution"))
        
        run = WorkflowRun(
            id="test-wf",
            user_id="test-user",
            requirement_text="测试",
            status=WorkflowStatus.COMPLETED,
        )
        state = WorkflowState(workflow_run=run)
        
        result = manager.collect_experience(state)
        
        assert result["status"] == "collected"
        assert "experience_id" in result
    
    def test_trigger_evolution_insufficient_data(self, tmp_path):
        """测试触发进化 - 数据不足"""
        manager = AgentEvolutionManager(
            storage_dir=str(tmp_path / "evolution"),
            config=AgentEvolutionConfig(min_experiences_for_analysis=10),
        )
        
        # 只创建少量经验
        for i in range(3):
            run = WorkflowRun(
                id=f"test-wf-{i}",
                user_id="test-user",
                requirement_text=f"测试 {i}",
                status=WorkflowStatus.COMPLETED,
            )
            state = WorkflowState(workflow_run=run)
            manager.collect_experience(state)
        
        # 触发进化（应该因为数据不足而跳过）
        result = manager.trigger_evolution()
        
        assert result["status"] == "skipped"
        assert result["reason"] == "insufficient_data"
    
    def test_evolution_metrics(self, tmp_path):
        """测试进化指标"""
        manager = AgentEvolutionManager(storage_dir=str(tmp_path / "evolution"))
        
        # 创建一些经验
        for i in range(10):
            run = WorkflowRun(
                id=f"test-wf-{i}",
                user_id="test-user",
                requirement_text=f"测试 {i}",
                status=WorkflowStatus.COMPLETED,
            )
            state = WorkflowState(workflow_run=run)
            manager.collect_experience(state)
        
        metrics = manager.get_evolution_metrics()
        
        assert metrics.total_experiences == 10
        assert metrics.overall_success_rate == 1.0  # 全部成功
    
    def test_evolution_status(self, tmp_path):
        """测试进化状态"""
        manager = AgentEvolutionManager(storage_dir=str(tmp_path / "evolution"))
        
        status = manager.get_evolution_status()
        
        assert "status" in status
        assert "enabled" in status
        assert "metrics" in status


class TestIntegration:
    """集成测试"""
    
    def test_full_evolution_cycle(self, tmp_path):
        """测试完整的进化周期"""
        manager = AgentEvolutionManager(
            storage_dir=str(tmp_path / "evolution"),
            config=AgentEvolutionConfig(
                min_experiences_for_analysis=5,
                analysis_interval_hours=0,  # 禁用时间检查
            ),
        )
        
        # 1. 收集足够的经验
        for i in range(10):
            status = WorkflowStatus.COMPLETED if i < 8 else WorkflowStatus.FAILED
            run = WorkflowRun(
                id=f"test-wf-{i}",
                user_id="test-user",
                requirement_text=f"测试需求 {i}",
                status=status,
            )
            state = WorkflowState(workflow_run=run)
            if status == WorkflowStatus.COMPLETED:
                state.prototype_html = "<html>Prototype</html>"
            manager.collect_experience(state)
        
        # 2. 触发进化
        result = manager.trigger_evolution()
        
        # 3. 验证结果
        assert result["status"] == "completed"
        assert "distillation_summary" in result
        
        # 4. 获取指标
        metrics = manager.get_evolution_metrics()
        assert metrics.total_experiences == 10
        assert metrics.overall_success_rate == 0.8  # 80% 成功率
        
        # 5. 获取优化建议
        suggestions = manager.get_optimization_suggestions()
        assert isinstance(suggestions, list)
