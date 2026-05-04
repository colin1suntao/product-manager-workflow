"""长链推理核心测试"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from pm_workstation.agents.branch_analyzer import BranchAnalyzer
from pm_workstation.agents.gap_detector import GapDetectionResult, GapDetector, GapItem
from pm_workstation.agents.rule_decomposer import RuleDecomposer
from pm_workstation.model_router.base import LLMBackend, LLMMessage, LLMResponse
from pm_workstation.models.core import RuleTreeNode


class TestRuleDecomposer:
    """RuleDecomposer测试"""
    
    @pytest.mark.asyncio
    async def test_decompose_simple_rule(self):
        """测试拆解简单规则"""
        mock_llm = AsyncMock(spec=LLMBackend)
        mock_llm.chat = AsyncMock(return_value=LLMResponse(
            content='''```json
{
    "rule_text": "用户必须年满18岁才能注册",
    "conditions": [
        {"field": "age", "operator": ">=", "value": "18"}
    ],
    "actions": [
        {"action_type": "allow", "description": "允许注册", "parameters": {}}
    ],
    "children": [],
    "depth": 0
}
```''',
            model="gpt-4",
        ))
        
        decomposer = RuleDecomposer(llm_handler=mock_llm, max_depth=5)
        tree = await decomposer.decompose(
            requirement_text="实现用户注册功能，要求用户年满18岁",
            rule_description="年龄验证规则",
        )
        
        assert tree.rule_text == "用户必须年满18岁才能注册"
        assert len(tree.conditions) == 1
        assert tree.conditions[0].field == "age"
        assert len(tree.actions) == 1
    
    @pytest.mark.asyncio
    async def test_decompose_complex_rule(self):
        """测试拆解复杂规则（带子规则）"""
        mock_llm = AsyncMock(spec=LLMBackend)
        mock_llm.chat = AsyncMock(return_value=LLMResponse(
            content='''```json
{
    "rule_text": "用户登录验证",
    "conditions": [],
    "actions": [],
    "children": [
        {
            "rule_text": "密码正确",
            "conditions": [
                {"field": "password", "operator": "==", "value": "stored_password"}
            ],
            "actions": [
                {"action_type": "login_success", "description": "登录成功", "parameters": {}}
            ],
            "children": [],
            "depth": 1
        },
        {
            "rule_text": "密码错误",
            "conditions": [
                {"field": "password", "operator": "!=", "value": "stored_password"}
            ],
            "actions": [
                {"action_type": "show_error", "description": "显示错误提示", "parameters": {}}
            ],
            "children": [],
            "depth": 1
        }
    ],
    "depth": 0
}
```''',
            model="gpt-4",
        ))
        
        decomposer = RuleDecomposer(llm_handler=mock_llm)
        tree = await decomposer.decompose(
            requirement_text="用户登录功能",
            rule_description="登录验证规则",
        )
        
        assert tree.rule_text == "用户登录验证"
        assert len(tree.children) == 2
        assert tree.children[0].rule_text == "密码正确"
        assert tree.children[1].rule_text == "密码错误"
    
    @pytest.mark.asyncio
    async def test_decompose_multiple_rules(self):
        """测试拆解多个规则"""
        mock_llm = AsyncMock(spec=LLMBackend)
        mock_llm.chat = AsyncMock(return_value=LLMResponse(
            content='''```json
{
    "rule_text": "规则",
    "conditions": [],
    "actions": [],
    "children": [],
    "depth": 0
}
```''',
            model="gpt-4",
        ))
        
        decomposer = RuleDecomposer(llm_handler=mock_llm)
        trees = await decomposer.decompose_complex_rules(
            requirement_text="需求描述",
            rules=["规则1", "规则2", "规则3"],
        )
        
        assert len(trees) == 3
        assert all(isinstance(t, RuleTreeNode) for t in trees)
    
    def test_max_depth_config(self):
        """测试最大深度配置"""
        mock_llm = MagicMock(spec=LLMBackend)
        decomposer = RuleDecomposer(llm_handler=mock_llm, max_depth=3)
        
        assert decomposer.max_depth == 3
    
    def test_system_prompt(self):
        """测试系统提示词"""
        mock_llm = MagicMock(spec=LLMBackend)
        decomposer = RuleDecomposer(llm_handler=mock_llm)
        
        prompt = decomposer._get_system_prompt()
        
        assert "规则树" in prompt
        assert "条件" in prompt
        assert "动作" in prompt


class TestBranchAnalyzer:
    """BranchAnalyzer测试"""
    
    @pytest.mark.asyncio
    async def test_analyze_branches(self):
        """测试分析分支"""
        mock_llm = AsyncMock(spec=LLMBackend)
        mock_llm.chat = AsyncMock(return_value=LLMResponse(
            content='''```json
[
    {
        "name": "正常登录",
        "branch_type": "normal",
        "condition": "用户名和密码正确",
        "steps": [
            {"step_number": 1, "description": "验证通过", "action": "登录", "expected_result": "进入首页"}
        ]
    },
    {
        "name": "密码错误",
        "branch_type": "exception",
        "condition": "密码验证失败",
        "steps": [
            {"step_number": 1, "description": "显示错误", "action": "提示", "expected_result": "用户看到错误"}
        ]
    },
    {
        "name": "空用户名",
        "branch_type": "boundary",
        "condition": "用户名为空",
        "steps": [
            {"step_number": 1, "description": "提示输入", "action": "验证", "expected_result": "提示必填"}
        ]
    }
]
```''',
            model="gpt-4",
        ))
        
        analyzer = BranchAnalyzer(llm_handler=mock_llm)
        branches = await analyzer.analyze(
            requirement_text="用户登录功能",
            flow_name="登录流程",
        )
        
        assert len(branches) == 3
        
        # 验证正常分支
        normal = [b for b in branches if b.branch_type == "normal"][0]
        assert normal.name == "正常登录"
        
        # 验证异常分支
        exception = [b for b in branches if b.branch_type == "exception"][0]
        assert exception.name == "密码错误"
        
        # 验证边界分支
        boundary = [b for b in branches if b.branch_type == "boundary"][0]
        assert boundary.name == "空用户名"
    
    @pytest.mark.asyncio
    async def test_analyze_empty_branches(self):
        """测试分析空分支"""
        mock_llm = AsyncMock(spec=LLMBackend)
        mock_llm.chat = AsyncMock(return_value=LLMResponse(
            content="[]",
            model="gpt-4",
        ))
        
        analyzer = BranchAnalyzer(llm_handler=mock_llm)
        branches = await analyzer.analyze(
            requirement_text="简单需求",
            flow_name="流程",
        )
        
        assert branches == []
    
    def test_system_prompt(self):
        """测试系统提示词"""
        mock_llm = MagicMock(spec=LLMBackend)
        analyzer = BranchAnalyzer(llm_handler=mock_llm)
        
        prompt = analyzer._get_system_prompt()
        
        assert "normal" in prompt
        assert "exception" in prompt
        assert "boundary" in prompt


class TestGapDetector:
    """GapDetector测试"""
    
    @pytest.mark.asyncio
    async def test_detect_gaps(self):
        """测试检测疏漏"""
        mock_llm = AsyncMock(spec=LLMBackend)
        mock_llm.chat = AsyncMock(return_value=LLMResponse(
            content='''```json
{
    "gaps": [
        {
            "description": "缺少密码错误次数限制",
            "severity": "high",
            "suggestion": "添加连续失败锁定机制"
        },
        {
            "description": "未考虑网络超时场景",
            "severity": "medium",
            "suggestion": "添加重试和超时处理"
        }
    ],
    "clarifications": [
        {
            "question": "是否需要支持第三方登录？",
            "context": "登录方式",
            "options": ["是", "否"]
        }
    ],
    "is_complete": false
}
```''',
            model="gpt-4",
        ))
        
        detector = GapDetector(llm_handler=mock_llm)
        result = await detector.detect(
            requirement_text="用户登录功能",
            structured_data="已解析的结构化数据",
        )
        
        assert isinstance(result, GapDetectionResult)
        assert len(result.gaps) == 2
        assert result.gaps[0].severity == "high"
        assert len(result.clarifications) == 1
        assert result.is_complete is False
    
    @pytest.mark.asyncio
    async def test_detect_no_gaps(self):
        """测试无疏漏"""
        mock_llm = AsyncMock(spec=LLMBackend)
        mock_llm.chat = AsyncMock(return_value=LLMResponse(
            content='''```json
{
    "gaps": [],
    "clarifications": [],
    "is_complete": true
}
```''',
            model="gpt-4",
        ))
        
        detector = GapDetector(llm_handler=mock_llm)
        result = await detector.detect(
            requirement_text="完整的需求",
            structured_data="完整的结构化数据",
        )
        
        assert result.gaps == []
        assert result.clarifications == []
        assert result.is_complete is True
    
    def test_system_prompt(self):
        """测试系统提示词"""
        mock_llm = MagicMock(spec=LLMBackend)
        detector = GapDetector(llm_handler=mock_llm)
        
        prompt = detector._get_system_prompt()
        
        assert "异常处理" in prompt
        assert "边界条件" in prompt
        assert "权限" in prompt


class TestReasoningIntegration:
    """推理核心集成测试"""
    
    @pytest.mark.asyncio
    async def test_full_reasoning_workflow(self):
        """测试完整推理流程"""
        mock_llm = AsyncMock(spec=LLMBackend)
        
        # 规则拆解响应
        mock_llm.chat = AsyncMock(return_value=LLMResponse(
            content='''```json
{
    "rule_text": "登录规则",
    "conditions": [],
    "actions": [],
    "children": [],
    "depth": 0
}
```''',
            model="gpt-4",
        ))
        
        decomposer = RuleDecomposer(llm_handler=mock_llm)
        tree = await decomposer.decompose(
            requirement_text="用户登录",
            rule_description="登录规则",
        )
        
        assert tree.rule_text == "登录规则"
        
        # 分支分析响应
        mock_llm.chat = AsyncMock(return_value=LLMResponse(
            content='''[
                {"name": "成功", "branch_type": "normal", "condition": "", "steps": []}
            ]''',
            model="gpt-4",
        ))
        
        analyzer = BranchAnalyzer(llm_handler=mock_llm)
        branches = await analyzer.analyze(
            requirement_text="用户登录",
            flow_name="登录流程",
        )
        
        assert len(branches) == 1
        
        # 疏漏检测响应
        mock_llm.chat = AsyncMock(return_value=LLMResponse(
            content='''{
                "gaps": [],
                "clarifications": [],
                "is_complete": true
            }''',
            model="gpt-4",
        ))
        
        detector = GapDetector(llm_handler=mock_llm)
        result = await detector.detect(
            requirement_text="用户登录",
            structured_data="{}",
        )
        
        assert result.is_complete is True
