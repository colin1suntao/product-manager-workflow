"""业务实体提取器"""


from pm_workstation.model_router.base import LLMBackend, LLMMessage
from pm_workstation.models.core import BusinessEntity


class EntityExtractor:
    """业务实体提取器"""

    def __init__(self, llm_handler: LLMBackend):
        self.llm_handler = llm_handler

    async def extract(self, requirement_text: str) -> list[BusinessEntity]:
        """从需求文本中提取业务实体

        Args:
            requirement_text: 需求文本

        Returns:
            业务实体列表
        """
        prompt = f"""请从以下需求描述中提取所有业务实体：

{requirement_text}

业务实体是指业务流程中涉及的关键对象或概念，例如：用户、订单、产品、账户等。

请以JSON数组格式输出，每个实体包含：
- name: 实体名称
- description: 实体描述
- attributes: 属性列表，每个属性包含name, type, description, required
- relationships: 关联关系列表，每个关系包含target_entity, relationship_type, description"""

        response = await self.llm_handler.chat([
            LLMMessage(role="system", content="你是一个业务分析师，擅长识别和提取业务实体。"),
            LLMMessage(role="user", content=prompt),
        ])

        return self._parse_entities(response.content)

    def _parse_entities(self, content: str) -> list[BusinessEntity]:
        """解析实体响应"""
        import json

        # 提取JSON
        json_str = self._extract_json(content)
        data = json.loads(json_str)

        return [BusinessEntity(**item) for item in data]

    def _extract_json(self, content: str) -> str:
        """从响应中提取JSON字符串"""
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
