"""澄清问题生成器"""


from pydantic import BaseModel

from pm_workstation.model_router.base import LLMBackend, LLMMessage
from pm_workstation.models.core import Question


class ClarificationRequest(BaseModel):
    """澄清请求"""
    requirement_text: str  # 原始需求
    ambiguous_parts: list[str] = []  # 歧义部分
    missing_info: list[str] = []  # 缺失信息


class ClarificationResponse(BaseModel):
    """澄清响应"""
    questions: list[Question]  # 澄清问题列表
    priority: str  # 优先级 (high/medium/low)


class ClarificationGenerator:
    """澄清问题生成器 - 生成需要用户确认的问题"""

    def __init__(self, llm_handler: LLMBackend):
        """初始化澄清问题生成器

        Args:
            llm_handler: LLM处理器
        """
        self.llm_handler = llm_handler

    async def generate(
        self,
        requirement_text: str,
        ambiguous_parts: list[str] | None = None,
        missing_info: list[str] | None = None,
    ) -> list[Question]:
        """生成澄清问题

        Args:
            requirement_text: 原始需求文本
            ambiguous_parts: 歧义部分列表
            missing_info: 缺失信息列表

        Returns:
            澄清问题列表
        """
        request = ClarificationRequest(
            requirement_text=requirement_text,
            ambiguous_parts=ambiguous_parts or [],
            missing_info=missing_info or [],
        )

        prompt = self._build_prompt(request)

        response = await self.llm_handler.chat([
            LLMMessage(role="system", content=self._get_system_prompt()),
            LLMMessage(role="user", content=prompt),
        ])

        return self._parse_questions(response.content)

    async def generate_from_analysis(
        self,
        requirement_text: str,
        analysis_result: str,
    ) -> list[Question]:
        """基于分析结果生成澄清问题

        Args:
            requirement_text: 原始需求文本
            analysis_result: 分析结果

        Returns:
            澄清问题列表
        """
        prompt = f"""基于以下分析结果，生成需要用户澄清的问题：

原始需求：
{requirement_text}

分析结果：
{analysis_result}

请识别分析中不确定的部分，生成具体的澄清问题。"""

        response = await self.llm_handler.chat([
            LLMMessage(role="system", content=self._get_system_prompt()),
            LLMMessage(role="user", content=prompt),
        ])

        return self._parse_questions(response.content)

    def _get_system_prompt(self) -> str:
        """获取系统提示词"""
        return """你是一个需求澄清专家，擅长从模糊或不完整的需求中识别歧义和缺失信息，并生成清晰的澄清问题。

生成问题的原则：
1. 问题应该具体明确，避免模糊
2. 提供可选项帮助用户快速回答
3. 按优先级排序（高优先级问题影响核心功能）
4. 问题数量控制在3-7个之间

每个问题包含：
- question: 问题内容
- context: 问题上下文（为什么问这个问题）
- options: 可选答案列表（如果适用）

请以JSON数组格式输出问题列表。"""

    def _build_prompt(self, request: ClarificationRequest) -> str:
        """构建提示词"""
        parts = []

        if request.ambiguous_parts:
            parts.append("歧义部分：")
            for part in request.ambiguous_parts:
                parts.append(f"- {part}")

        if request.missing_info:
            parts.append("缺失信息：")
            for info in request.missing_info:
                parts.append(f"- {info}")

        return f"""请针对以下需求生成澄清问题：

需求描述：
{request.requirement_text}

{chr(10).join(parts)}

请生成具体的澄清问题，帮助完善需求。"""

    def _parse_questions(self, content: str) -> list[Question]:
        """解析问题响应"""
        import json

        json_str = self._extract_json(content)
        data = json.loads(json_str)

        return [Question(**q) for q in data]

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
