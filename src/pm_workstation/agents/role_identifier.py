"""角色识别器"""

from pm_workstation.model_router.base import LLMBackend, LLMMessage
from pm_workstation.models.core import Role


class RoleIdentifier:
    """角色识别器"""

    def __init__(self, llm_handler: LLMBackend):
        self.llm_handler = llm_handler

    async def identify(self, requirement_text: str) -> list[Role]:
        """从需求文本中识别用户角色

        Args:
            requirement_text: 需求文本

        Returns:
            角色列表
        """
        prompt = f"""请从以下需求描述中识别所有用户角色：

{requirement_text}

用户角色是指与系统交互的不同类型的用户，例如：普通用户、管理员、客服、审核员等。

请以JSON数组格式输出，每个角色包含：
- name: 角色名称
- description: 角色描述
- permissions: 权限列表（字符串数组）"""

        response = await self.llm_handler.chat([
            LLMMessage(role="system", content="你是一个业务分析师，擅长识别系统用户角色。"),
            LLMMessage(role="user", content=prompt),
        ])

        return self._parse_roles(response.content)

    def _parse_roles(self, content: str) -> list[Role]:
        """解析角色响应"""
        import json

        json_str = self._extract_json(content)
        data = json.loads(json_str)

        return [Role(**item) for item in data]

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
