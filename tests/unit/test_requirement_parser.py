"""需求解析Agent测试"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from pm_workstation.agents.entity_extractor import EntityExtractor
from pm_workstation.agents.requirement_parser import RequirementParser
from pm_workstation.agents.role_identifier import RoleIdentifier
from pm_workstation.model_router.base import LLMBackend, LLMMessage, LLMResponse


class TestRequirementParser:
    """RequirementParser测试"""
    
    @pytest.mark.asyncio
    async def test_parse_requirement(self):
        """测试解析需求"""
        mock_llm = AsyncMock(spec=LLMBackend)
        mock_llm.chat = AsyncMock(return_value=LLMResponse(
            content='''```json
{
    "entities": [
        {
            "name": "User",
            "description": "用户实体",
            "attributes": [
                {"name": "username", "type": "string", "description": "用户名", "required": true}
            ],
            "relationships": []
        }
    ],
    "roles": [
        {"name": "admin", "description": "管理员", "permissions": ["read", "write"]}
    ],
    "rules": {
        "rule_text": "用户必须登录",
        "conditions": [],
        "actions": [],
        "children": [],
        "depth": 0
    },
    "flows": [],
    "branches": [],
    "edge_cases": [],
    "clarifications": []
}
```''',
            model="gpt-4",
        ))
        
        parser = RequirementParser(llm_handler=mock_llm)
        result = await parser.parse("实现用户登录功能")
        
        assert len(result.entities) == 1
        assert result.entities[0].name == "User"
        assert len(result.roles) == 1
        assert result.roles[0].name == "admin"
        assert result.rules.rule_text == "用户必须登录"
    
    @pytest.mark.asyncio
    async def test_parse_with_code_block(self):
        """测试解析带代码块的响应"""
        mock_llm = AsyncMock(spec=LLMBackend)
        mock_llm.chat = AsyncMock(return_value=LLMResponse(
            content='''
一些说明文字

```json
{
    "entities": [],
    "roles": [],
    "rules": {"rule_text": "规则"},
    "flows": [],
    "branches": [],
    "edge_cases": [],
    "clarifications": []
}
```

结束说明
''',
            model="gpt-4",
        ))
        
        parser = RequirementParser(llm_handler=mock_llm)
        result = await parser.parse("测试需求")
        
        assert result.rules.rule_text == "规则"
    
    @pytest.mark.asyncio
    async def test_parse_without_code_block(self):
        """测试解析无代码块的响应"""
        mock_llm = AsyncMock(spec=LLMBackend)
        mock_llm.chat = AsyncMock(return_value=LLMResponse(
            content='''{
    "entities": [],
    "roles": [],
    "rules": {"rule_text": "简单规则"},
    "flows": [],
    "branches": [],
    "edge_cases": [],
    "clarifications": []
}''',
            model="gpt-4",
        ))
        
        parser = RequirementParser(llm_handler=mock_llm)
        result = await parser.parse("测试需求")
        
        assert result.rules.rule_text == "简单规则"
    
    def test_system_prompt(self):
        """测试系统提示词"""
        mock_llm = MagicMock(spec=LLMBackend)
        parser = RequirementParser(llm_handler=mock_llm)
        
        prompt = parser._get_system_prompt()
        
        assert "需求分析师" in prompt
        assert "业务实体" in prompt
        assert "JSON" in prompt
    
    def test_build_parse_prompt(self):
        """测试构建解析提示词"""
        mock_llm = MagicMock(spec=LLMBackend)
        parser = RequirementParser(llm_handler=mock_llm)
        
        prompt = parser._build_parse_prompt("实现登录功能")
        
        assert "实现登录功能" in prompt
        assert "entities" in prompt
        assert "rules" in prompt


class TestEntityExtractor:
    """EntityExtractor测试"""
    
    @pytest.mark.asyncio
    async def test_extract_entities(self):
        """测试提取实体"""
        mock_llm = AsyncMock(spec=LLMBackend)
        mock_llm.chat = AsyncMock(return_value=LLMResponse(
            content='''```json
[
    {
        "name": "Order",
        "description": "订单实体",
        "attributes": [
            {"name": "order_id", "type": "string", "description": "订单ID", "required": true}
        ],
        "relationships": []
    }
]
```''',
            model="gpt-4",
        ))
        
        extractor = EntityExtractor(llm_handler=mock_llm)
        entities = await extractor.extract("用户下单购买")
        
        assert len(entities) == 1
        assert entities[0].name == "Order"
        assert len(entities[0].attributes) == 1
    
    @pytest.mark.asyncio
    async def test_extract_empty_entities(self):
        """测试提取空实体"""
        mock_llm = AsyncMock(spec=LLMBackend)
        mock_llm.chat = AsyncMock(return_value=LLMResponse(
            content="[]",
            model="gpt-4",
        ))
        
        extractor = EntityExtractor(llm_handler=mock_llm)
        entities = await extractor.extract("简单需求")
        
        assert entities == []
    
    def test_extract_json_from_response(self):
        """测试从响应提取JSON"""
        mock_llm = MagicMock(spec=LLMBackend)
        extractor = EntityExtractor(llm_handler=mock_llm)
        
        # 带```json标记
        content1 = '''说明文字
```json
{"test": true}
```'''
        assert extractor._extract_json(content1) == '{"test": true}'
        
        # 带```标记
        content2 = '''```
{"test": true}
```'''
        assert extractor._extract_json(content2) == '{"test": true}'
        
        # 纯JSON
        content3 = '{"test": true}'
        assert extractor._extract_json(content3) == '{"test": true}'


class TestRoleIdentifier:
    """RoleIdentifier测试"""
    
    @pytest.mark.asyncio
    async def test_identify_roles(self):
        """测试识别角色"""
        mock_llm = AsyncMock(spec=LLMBackend)
        mock_llm.chat = AsyncMock(return_value=LLMResponse(
            content='''```json
[
    {
        "name": "customer",
        "description": "客户",
        "permissions": ["browse", "purchase"]
    },
    {
        "name": "admin",
        "description": "管理员",
        "permissions": ["manage"]
    }
]
```''',
            model="gpt-4",
        ))
        
        identifier = RoleIdentifier(llm_handler=mock_llm)
        roles = await identifier.identify("客户购买，管理员管理")
        
        assert len(roles) == 2
        assert roles[0].name == "customer"
        assert roles[1].name == "admin"
    
    @pytest.mark.asyncio
    async def test_identify_no_roles(self):
        """测试无角色"""
        mock_llm = AsyncMock(spec=LLMBackend)
        mock_llm.chat = AsyncMock(return_value=LLMResponse(
            content="[]",
            model="gpt-4",
        ))
        
        identifier = RoleIdentifier(llm_handler=mock_llm)
        roles = await identifier.identify("简单需求")
        
        assert roles == []
