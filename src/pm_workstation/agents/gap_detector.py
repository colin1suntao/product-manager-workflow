"""逻辑疏漏检测器"""


from pydantic import BaseModel

from pm_workstation.model_router.base import LLMBackend, LLMMessage
from pm_workstation.models.core import Question


class GapItem(BaseModel):
    """疏漏项"""
    description: str  # 疏漏描述
    severity: str  # 严重程度 (high/medium/low)
    suggestion: str  # 建议


class GapDetectionResult(BaseModel):
    """疏漏检测结果"""
    gaps: list[GapItem]  # 疏漏列表
    clarifications: list[Question]  # 需要澄清的问题
    is_complete: bool  # 是否完整


class GapDetector:
    """逻辑疏漏检测器 - 标记考虑不全的场景"""

    def __init__(self, llm_handler: LLMBackend):
        """初始化疏漏检测器

        Args:
            llm_handler: LLM处理器
        """
        self.llm_handler = llm_handler

    async def detect(self, requirement_text: str, structured_data: str) -> GapDetectionResult:
        """检测逻辑疏漏

        Args:
            requirement_text: 原始需求文本
            structured_data: 已解析的结构化数据

        Returns:
            疏漏检测结果
        """
        prompt = self._build_detect_prompt(requirement_text, structured_data)

        response = await self.llm_handler.chat([
            LLMMessage(role="system", content=self._get_system_prompt()),
            LLMMessage(role="user", content=prompt),
        ])

        return self._parse_result(response.content)

    def _get_system_prompt(self) -> str:
        """获取系统提示词"""
        return """你是一个需求质量审计专家，擅长发现需求中的逻辑疏漏、考虑不全的场景和潜在风险。

你需要检查以下方面：
1. 异常处理是否完整（错误、失败、超时、重试等）
2. 边界条件是否覆盖（空值、极限值、并发、竞态等）
3. 权限和安全是否考虑（未授权访问、数据泄露、注入等）
4. 用户体验是否完善（加载状态、错误提示、回滚机制等）
5. 数据一致性是否保障（事务、补偿、幂等等）

对于每个发现的疏漏，提供：
- description: 疏漏描述
- severity: 严重程度（high/medium/low）
- suggestion: 修复建议

对于需要澄清的问题，提供：
- question: 问题内容
- context: 问题上下文

最后给出整体完整性评估（is_complete: true/false）。

请以JSON格式输出。"""

    def _build_detect_prompt(self, requirement_text: str, structured_data: str) -> str:
        """构建检测提示词"""
        return f"""请检查以下需求是否存在逻辑疏漏：

原始需求：
{requirement_text}

已解析的结构化数据：
{structured_data}

请全面检查异常处理、边界条件、权限安全、用户体验、数据一致性等方面，
列出所有发现的疏漏和需要澄清的问题。"""

    def _parse_result(self, content: str) -> GapDetectionResult:
        """解析检测结果"""
        import json

        json_str = self._extract_json(content)
        data = json.loads(json_str)

        gaps = [GapItem(**g) for g in data.get("gaps", [])]

        clarifications_data = data.get("clarifications", [])
        clarifications = [Question(**q) for q in clarifications_data]

        return GapDetectionResult(
            gaps=gaps,
            clarifications=clarifications,
            is_complete=data.get("is_complete", False),
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
