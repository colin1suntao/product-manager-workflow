"""需求解析Agent"""

from typing import Any, Optional

from pm_workstation.model_router.base import LLMBackend, LLMMessage, LLMResponse
from pm_workstation.model_router.fallback_handler import FallbackHandler
from pm_workstation.models.core import (
    BusinessEntity,
    EdgeCase,
    Question,
    Role,
    StructuredRequirement,
    UserFlow,
)
from pm_workstation.models.core import RuleTreeNode as RuleTree


class RequirementParser:
    """需求文本解析器 - 提取业务实体、角色、操作流程"""
    
    def __init__(self, llm_handler: LLMBackend | FallbackHandler):
        """初始化需求解析器
        
        Args:
            llm_handler: LLM处理器
        """
        self.llm_handler = llm_handler
    
    async def parse(self, requirement_text: str) -> StructuredRequirement:
        """解析需求文本
        
        Args:
            requirement_text: 原始需求文本
            
        Returns:
            结构化需求
        """
        prompt = self._build_parse_prompt(requirement_text)
        
        response = await self.llm_handler.chat([
            LLMMessage(role="system", content=self._get_system_prompt()),
            LLMMessage(role="user", content=prompt),
        ])
        
        return self._parse_response(response.content)
    
    def _get_system_prompt(self) -> str:
        """获取系统提示词"""
        return """你是一个专业的需求分析师，擅长从碎片化的需求描述中提取结构化的业务信息。

你的任务是：
1. 识别并提取所有业务实体（BusinessEntity），包括实体名称、描述、属性和关联关系
2. 识别所有用户角色（Role），包括角色名称、描述和权限
3. 识别用户操作流程（UserFlow），包括流程名称、执行角色、步骤、分支、入口和出口
4. 识别业务规则树（RuleTree），包括规则描述、条件、动作和子规则
5. 识别操作分支（Branch），包括分支名称、类型（normal/exception/boundary）、触发条件和步骤
6. 识别边界场景（EdgeCase），包括场景描述、触发条件和预期行为
7. 生成需要澄清的问题（Question），当需求存在歧义或缺失时

请以JSON格式输出，确保所有字段都正确填充。如果某些信息无法从需求中推断，使用合理的默认值。"""
    
    def _build_parse_prompt(self, requirement_text: str) -> str:
        """构建解析提示词"""
        return f"""请分析以下需求描述，提取结构化的业务信息：

{requirement_text}

请以JSON格式输出，包含以下字段：
- entities: 业务实体列表
- roles: 用户角色列表
- rules: 业务规则树
- flows: 用户操作流程列表
- branches: 操作分支列表
- edge_cases: 边界场景列表
- clarifications: 需要澄清的问题列表"""
    
    def _parse_response(self, response_content: str) -> StructuredRequirement:
        """解析LLM响应
        
        Args:
            response_content: LLM响应内容
            
        Returns:
            结构化需求
        """
        import json
        
        # 尝试提取JSON
        content = response_content.strip()
        
        # 查找JSON块
        if "```json" in content:
            start = content.index("```json") + 7
            end = content.index("```", start)
            content = content[start:end].strip()
        elif "```" in content:
            start = content.index("```") + 3
            end = content.index("```", start)
            content = content[start:end].strip()
        
        data = json.loads(content)
        
        return StructuredRequirement(
            entities=[BusinessEntity(**e) for e in data.get("entities", [])],
            roles=[Role(**r) for r in data.get("roles", [])],
            rules=self._parse_rule_tree(data.get("rules", {})),
            flows=[UserFlow(**f) for f in data.get("flows", [])],
            branches=data.get("branches", []),
            edge_cases=[EdgeCase(**ec) for ec in data.get("edge_cases", [])],
            clarifications=[Question(**q) for q in data.get("clarifications", [])],
        )
    
    def _parse_rule_tree(self, rule_data: dict) -> RuleTree:
        """解析规则树"""
        from pm_workstation.models.core import RuleTreeNode
        
        if not rule_data:
            return RuleTreeNode(rule_text="待补充")
        
        children = [
            self._parse_rule_tree(child)
            for child in rule_data.get("children", [])
        ]
        
        return RuleTreeNode(
            rule_text=rule_data.get("rule_text", ""),
            conditions=rule_data.get("conditions", []),
            actions=rule_data.get("actions", []),
            children=children,
            depth=rule_data.get("depth", 0),
        )
