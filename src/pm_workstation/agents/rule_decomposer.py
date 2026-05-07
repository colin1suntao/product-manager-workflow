"""业务规则拆解器"""

from pm_workstation.model_router.base import LLMBackend, LLMMessage
from pm_workstation.models.core import (
    Action,
    Condition,
    RuleTreeNode,
)


class RuleDecomposer:
    """业务规则拆解器 - 生成规则树"""

    def __init__(self, llm_handler: LLMBackend, max_depth: int = 5):
        """初始化规则拆解器

        Args:
            llm_handler: LLM处理器
            max_depth: 最大规则深度
        """
        self.llm_handler = llm_handler
        self.max_depth = max_depth

    async def decompose(self, requirement_text: str, rule_description: str) -> RuleTreeNode:
        """拆解业务规则

        Args:
            requirement_text: 原始需求文本
            rule_description: 规则描述

        Returns:
            规则树根节点
        """
        prompt = self._build_decompose_prompt(requirement_text, rule_description)

        response = await self.llm_handler.chat([
            LLMMessage(role="system", content=self._get_system_prompt()),
            LLMMessage(role="user", content=prompt),
        ])

        return self._parse_rule_tree(response.content)

    async def decompose_complex_rules(
        self,
        requirement_text: str,
        rules: list[str],
    ) -> list[RuleTreeNode]:
        """拆解复杂业务规则列表

        Args:
            requirement_text: 原始需求文本
            rules: 规则描述列表

        Returns:
            规则树列表
        """
        rule_trees = []

        for rule_desc in rules:
            tree = await self.decompose(requirement_text, rule_desc)
            rule_trees.append(tree)

        return rule_trees

    def _get_system_prompt(self) -> str:
        """获取系统提示词"""
        return """你是一个业务规则分析师，擅长将复杂的业务规则拆解为结构化的规则树。

规则树结构：
- 每个规则节点包含：规则描述(rule_text)、条件列表(conditions)、动作列表(actions)、子规则列表(children)、深度(depth)
- 条件包含：字段(field)、操作符(operator)、值(value)
- 动作包含：动作类型(action_type)、描述(description)、参数(parameters)
- 操作符支持：==, !=, >, <, >=, <=, in, contains
- 深度从0开始，每层子规则深度+1
- 最大深度不超过5层

请以JSON格式输出规则树，确保结构完整且逻辑清晰。"""

    def _build_decompose_prompt(self, requirement_text: str, rule_description: str) -> str:
        """构建拆解提示词"""
        return f"""请分析以下需求中的业务规则，并将其拆解为规则树：

需求描述：
{requirement_text}

目标规则：
{rule_description}

请将该规则拆解为多层规则树，覆盖所有条件和分支场景。
最大深度限制为{self.max_depth}层。

请以JSON格式输出规则树根节点。"""

    def _parse_rule_tree(self, content: str) -> RuleTreeNode:
        """解析规则树响应"""
        import json

        json_str = self._extract_json(content)
        data = json.loads(json_str)

        return self._build_node(data)

    def _build_node(self, data: dict) -> RuleTreeNode:
        """构建规则树节点"""
        children_data = data.get("children", [])
        children = [self._build_node(child) for child in children_data]

        conditions_data = data.get("conditions", [])
        conditions = [Condition(**c) for c in conditions_data]

        actions_data = data.get("actions", [])
        actions = [Action(**a) for a in actions_data]

        return RuleTreeNode(
            rule_text=data.get("rule_text", ""),
            conditions=conditions,
            actions=actions,
            children=children,
            depth=data.get("depth", 0),
        )

    def _extract_json(self, content: str) -> str:
        """从响应中提取JSON"""
        content = content.strip()

        if "```json" in content:
            start = content.index("```json") + 7
            end = content.index("```", start)
            return content[start:end].strip()
        elif "```" in content:
            start = content.index("```") + 3
            end = content.index("```", start)
            return content[start:end].strip()

        return content
