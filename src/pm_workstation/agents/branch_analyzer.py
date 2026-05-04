"""操作分支分析器"""

from pm_workstation.model_router.base import LLMBackend, LLMMessage, LLMResponse
from pm_workstation.models.core import Branch, FlowStep


class BranchAnalyzer:
    """操作分支分析器 - 梳理正常/异常/边界场景"""
    
    def __init__(self, llm_handler: LLMBackend):
        """初始化分支分析器
        
        Args:
            llm_handler: LLM处理器
        """
        self.llm_handler = llm_handler
    
    async def analyze(self, requirement_text: str, flow_name: str) -> list[Branch]:
        """分析操作流程的分支
        
        Args:
            requirement_text: 原始需求文本
            flow_name: 流程名称
            
        Returns:
            分支列表
        """
        prompt = self._build_analyze_prompt(requirement_text, flow_name)
        
        response = await self.llm_handler.chat([
            LLMMessage(role="system", content=self._get_system_prompt()),
            LLMMessage(role="user", content=prompt),
        ])
        
        return self._parse_branches(response.content)
    
    def _get_system_prompt(self) -> str:
        """获取系统提示词"""
        return """你是一个操作流程分析师，擅长识别和分析用户操作流程中的各种分支场景。

分支类型：
- normal: 正常流程分支
- exception: 异常流程分支（错误、失败场景）
- boundary: 边界场景分支（极限条件、特殊输入）

每个分支包含：
- name: 分支名称
- branch_type: 分支类型（normal/exception/boundary）
- condition: 触发条件
- steps: 分支步骤列表，每个步骤包含step_number, description, action, expected_result

请以JSON数组格式输出所有识别到的分支。"""
    
    def _build_analyze_prompt(self, requirement_text: str, flow_name: str) -> str:
        """构建分析提示词"""
        return f"""请分析以下需求中"{flow_name}"流程的所有操作分支：

需求描述：
{requirement_text}

请识别该流程的所有分支场景，包括：
1. 正常流程分支
2. 异常处理分支（如验证失败、系统错误、网络异常等）
3. 边界场景分支（如空输入、超大输入、并发操作等）

请以JSON数组格式输出。"""
    
    def _parse_branches(self, content: str) -> list[Branch]:
        """解析分支响应"""
        import json
        
        json_str = self._extract_json(content)
        data = json.loads(json_str)
        
        branches = []
        for item in data:
            steps_data = item.get("steps", [])
            steps = [FlowStep(**s) for s in steps_data]
            
            branches.append(Branch(
                name=item.get("name", ""),
                branch_type=item.get("branch_type", "normal"),
                condition=item.get("condition", ""),
                steps=steps,
            ))
        
        return branches
    
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
