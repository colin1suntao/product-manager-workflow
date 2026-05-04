"""结构化数据输出测试"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from pm_workstation.agents.clarification_generator import (
    ClarificationGenerator,
    ClarificationRequest,
)
from pm_workstation.agents.reasoning_tracer import ReasoningStep, ReasoningTrace, ReasoningTracer
from pm_workstation.model_router.base import LLMBackend, LLMResponse
from pm_workstation.models.core import Question, StructuredRequirement


class TestClarificationGenerator:
    """ClarificationGenerator测试"""
    
    @pytest.mark.asyncio
    async def test_generate_questions(self):
        """测试生成澄清问题"""
        mock_llm = AsyncMock(spec=LLMBackend)
        mock_llm.chat = AsyncMock(return_value=LLMResponse(
            content='''```json
[
    {
        "question": "是否需要支持批量删除？",
        "context": "在删除功能中",
        "options": ["是", "否"]
    },
    {
        "question": "删除后是否可恢复？",
        "context": "数据保留策略",
        "options": ["可恢复", "不可恢复"]
    }
]
```''',
            model="gpt-4",
        ))
        
        generator = ClarificationGenerator(llm_handler=mock_llm)
        questions = await generator.generate(
            requirement_text="实现删除功能",
            ambiguous_parts=["删除的范围不明确"],
            missing_info=["删除后是否可恢复"],
        )
        
        assert len(questions) == 2
        assert questions[0].question == "是否需要支持批量删除？"
        assert len(questions[0].options) == 2
    
    @pytest.mark.asyncio
    async def test_generate_from_analysis(self):
        """测试基于分析结果生成问题"""
        mock_llm = AsyncMock(spec=LLMBackend)
        mock_llm.chat = AsyncMock(return_value=LLMResponse(
            content='''[
                {
                    "question": "登录失败几次后锁定？",
                    "context": "安全策略",
                    "options": ["3次", "5次", "10次"]
                }
            ]''',
            model="gpt-4",
        ))
        
        generator = ClarificationGenerator(llm_handler=mock_llm)
        questions = await generator.generate_from_analysis(
            requirement_text="用户登录功能",
            analysis_result="识别到需要安全策略",
        )
        
        assert len(questions) == 1
        assert questions[0].question == "登录失败几次后锁定？"
    
    @pytest.mark.asyncio
    async def test_generate_empty_questions(self):
        """测试生成空问题"""
        mock_llm = AsyncMock(spec=LLMBackend)
        mock_llm.chat = AsyncMock(return_value=LLMResponse(
            content="[]",
            model="gpt-4",
        ))
        
        generator = ClarificationGenerator(llm_handler=mock_llm)
        questions = await generator.generate(
            requirement_text="非常完整的需求",
        )
        
        assert questions == []
    
    def test_build_prompt_with_parts(self):
        """测试构建提示词（有歧义和缺失）"""
        mock_llm = MagicMock(spec=LLMBackend)
        generator = ClarificationGenerator(llm_handler=mock_llm)
        
        request = ClarificationRequest(
            requirement_text="测试需求",
            ambiguous_parts=["部分A", "部分B"],
            missing_info=["信息X"],
        )
        
        prompt = generator._build_prompt(request)
        
        assert "测试需求" in prompt
        assert "部分A" in prompt
        assert "信息X" in prompt
    
    def test_build_prompt_without_parts(self):
        """测试构建提示词（无歧义和缺失）"""
        mock_llm = MagicMock(spec=LLMBackend)
        generator = ClarificationGenerator(llm_handler=mock_llm)
        
        request = ClarificationRequest(
            requirement_text="简单需求",
        )
        
        prompt = generator._build_prompt(request)
        
        assert "简单需求" in prompt
        assert "歧义部分" not in prompt


class TestReasoningTrace:
    """ReasoningTrace测试"""
    
    def test_create_trace(self):
        """测试创建推理路径"""
        trace = ReasoningTrace(
            trace_id="trace-001",
            requirement_text="测试需求",
        )
        
        assert trace.trace_id == "trace-001"
        assert trace.requirement_text == "测试需求"
        assert trace.status == "in_progress"
        assert trace.steps == []
    
    def test_add_step(self):
        """测试添加推理步骤"""
        trace = ReasoningTrace(
            trace_id="trace-001",
            requirement_text="测试需求",
        )
        
        step1 = trace.add_step(
            action="parse",
            description="解析需求文本",
            input_data="需求摘要",
            duration_ms=100,
        )
        
        assert step1.step_number == 1
        assert step1.action == "parse"
        assert step1.duration_ms == 100
        assert len(trace.steps) == 1
        
        step2 = trace.add_step(
            action="analyze",
            description="分析业务规则",
            duration_ms=200,
        )
        
        assert step2.step_number == 2
        assert len(trace.steps) == 2
    
    def test_complete_success(self):
        """测试成功完成"""
        trace = ReasoningTrace(
            trace_id="trace-001",
            requirement_text="测试需求",
        )
        
        trace.add_step("parse", "解析", duration_ms=100)
        trace.add_step("analyze", "分析", duration_ms=200)
        trace.complete()
        
        assert trace.status == "completed"
        assert trace.completed_at is not None
        assert trace.total_duration_ms == 300
        assert trace.error_message is None
    
    def test_complete_with_error(self):
        """测试失败完成"""
        trace = ReasoningTrace(
            trace_id="trace-001",
            requirement_text="测试需求",
        )
        
        trace.add_step("parse", "解析", duration_ms=100)
        trace.complete(error_message="解析失败")
        
        assert trace.status == "failed"
        assert trace.error_message == "解析失败"
    
    def test_get_summary(self):
        """测试获取摘要"""
        trace = ReasoningTrace(
            trace_id="trace-001",
            requirement_text="测试需求",
        )
        
        trace.add_step("parse", "解析需求", duration_ms=100)
        trace.add_step("analyze", "分析规则", duration_ms=200)
        trace.complete()
        
        summary = trace.get_summary()
        
        assert "trace-001" in summary
        assert "completed" in summary
        assert "解析需求" in summary
        assert "分析规则" in summary
        assert "300ms" in summary
    
    def test_get_summary_with_error(self):
        """测试获取错误摘要"""
        trace = ReasoningTrace(
            trace_id="trace-001",
            requirement_text="测试需求",
        )
        
        trace.complete(error_message="测试错误")
        
        summary = trace.get_summary()
        
        assert "failed" in summary
        assert "测试错误" in summary


class TestReasoningTracer:
    """ReasoningTracer测试"""
    
    def test_start_trace(self):
        """测试开始追踪"""
        tracer = ReasoningTracer()
        
        trace = tracer.start_trace(
            trace_id="trace-001",
            requirement_text="测试需求",
        )
        
        assert trace.trace_id == "trace-001"
        assert len(tracer.traces) == 1
    
    def test_get_trace(self):
        """测试获取追踪"""
        tracer = ReasoningTracer()
        tracer.start_trace("trace-001", "需求1")
        tracer.start_trace("trace-002", "需求2")
        
        trace = tracer.get_trace("trace-001")
        assert trace is not None
        assert trace.requirement_text == "需求1"
        
        # 不存在的追踪
        trace = tracer.get_trace("trace-999")
        assert trace is None
    
    def test_get_all_traces(self):
        """测试获取所有追踪"""
        tracer = ReasoningTracer()
        tracer.start_trace("trace-001", "需求1")
        tracer.start_trace("trace-002", "需求2")
        
        traces = tracer.get_all_traces()
        assert len(traces) == 2
    
    def test_clear_traces(self):
        """测试清除追踪"""
        tracer = ReasoningTracer()
        tracer.start_trace("trace-001", "需求1")
        tracer.start_trace("trace-002", "需求2")
        
        tracer.clear_traces()
        
        assert len(tracer.traces) == 0


class TestStructuredRequirementSerialization:
    """StructuredRequirement序列化测试"""
    
    def test_full_serialization(self):
        """测试完整序列化"""
        from pm_workstation.models.core import (
            Branch,
            BusinessEntity,
            EdgeCase,
            FlowStep,
            Role,
            RuleTreeNode,
            UserFlow,
        )
        
        requirement = StructuredRequirement(
            entities=[
                BusinessEntity(
                    name="User",
                    description="用户",
                    attributes=[],
                    relationships=[],
                )
            ],
            roles=[Role(name="admin", description="管理员")],
            rules=RuleTreeNode(rule_text="规则"),
            flows=[
                UserFlow(
                    name="登录",
                    role="user",
                    steps=[FlowStep(step_number=1, description="输入密码")],
                    branches=[Branch(name="成功", branch_type="normal")],
                )
            ],
            branches=[Branch(name="异常", branch_type="exception")],
            edge_cases=[EdgeCase(description="边界", condition="条件", expected_behavior="行为")],
            clarifications=[Question(question="问题？")],
            reasoning_trace="推理路径",
        )
        
        # 序列化
        json_str = requirement.model_dump_json()
        assert json_str is not None
        assert "User" in json_str
        assert "登录" in json_str
        
        # 反序列化
        data = requirement.model_dump()
        assert data["entities"][0]["name"] == "User"
        assert data["rules"]["rule_text"] == "规则"
    
    def test_minimal_serialization(self):
        """测试最小序列化"""
        from pm_workstation.models.core import RuleTreeNode
        
        requirement = StructuredRequirement(
            rules=RuleTreeNode(rule_text="简单规则")
        )
        
        json_str = requirement.model_dump_json()
        assert json_str is not None
        
        data = requirement.model_dump()
        assert data["rules"]["rule_text"] == "简单规则"
        assert data["entities"] == []


class TestOutputIntegration:
    """输出集成测试"""
    
    @pytest.mark.asyncio
    async def test_full_output_workflow(self):
        """测试完整输出流程"""
        # 1. 创建推理追踪
        tracer = ReasoningTracer()
        trace = tracer.start_trace("trace-001", "用户登录功能")
        
        # 2. 添加推理步骤
        trace.add_step("parse", "解析需求", duration_ms=100)
        trace.add_step("decompose", "拆解规则", duration_ms=200)
        
        # 3. 生成澄清问题
        mock_llm = AsyncMock(spec=LLMBackend)
        mock_llm.chat = AsyncMock(return_value=LLMResponse(
            content='[{"question": "需要验证码吗？", "context": "安全", "options": ["是", "否"]}]',
            model="gpt-4",
        ))
        
        generator = ClarificationGenerator(llm_handler=mock_llm)
        questions = await generator.generate(
            requirement_text="用户登录功能",
            missing_info=["是否需要验证码"],
        )
        
        assert len(questions) == 1
        
        # 4. 完成推理
        trace.add_step("clarify", "生成澄清问题", duration_ms=50)
        trace.complete()
        
        assert trace.status == "completed"
        assert trace.total_duration_ms == 350
        assert len(trace.steps) == 3
        
        # 5. 验证摘要
        summary = trace.get_summary()
        assert "trace-001" in summary
        assert "350ms" in summary
