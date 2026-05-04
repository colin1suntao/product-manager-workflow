"""任务分类器"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel


class TaskComplexity(str, Enum):
    """任务复杂度"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TaskType(str, Enum):
    """任务类型"""
    ANALYSIS = "analysis"  # 需求分析
    GENERATION = "generation"  # 内容生成
    REASONING = "reasoning"  # 逻辑推理
    SUMMARIZATION = "summarization"  # 总结
    CLASSIFICATION = "classification"  # 分类


class TaskClassification(BaseModel):
    """任务分类结果"""
    task_type: TaskType
    complexity: TaskComplexity
    estimated_tokens: int = 1000  # 预估token数
    requires_streaming: bool = False  # 是否需要流式输出
    reasoning_steps: int = 1  # 推理步骤数


class TaskClassifier:
    """任务分类器"""
    
    # 任务类型关键词映射
    TYPE_KEYWORDS = {
        TaskType.ANALYSIS: ["分析", "解析", "拆解", "梳理", "analyze", "parse"],
        TaskType.GENERATION: ["生成", "创建", "编写", "produce", "generate", "create"],
        TaskType.REASONING: ["推理", "逻辑", "判断", "reason", "logic"],
        TaskType.SUMMARIZATION: ["总结", "概括", "归纳", "summarize"],
        TaskType.CLASSIFICATION: ["分类", "归类", "classify"],
    }
    
    # 复杂度关键词映射
    COMPLEXITY_KEYWORDS = {
        TaskComplexity.HIGH: ["复杂", "多步骤", "详细", "深入", "complex", "detailed"],
        TaskComplexity.LOW: ["简单", "基础", "快速", "short", "simple"],
    }
    
    def classify(self, task_description: str) -> TaskClassification:
        """分类任务
        
        Args:
            task_description: 任务描述
            
        Returns:
            任务分类结果
        """
        task_type = self._classify_type(task_description)
        complexity = self._classify_complexity(task_description)
        estimated_tokens = self._estimate_tokens(task_description, task_type, complexity)
        
        return TaskClassification(
            task_type=task_type,
            complexity=complexity,
            estimated_tokens=estimated_tokens,
            requires_streaming=complexity in (TaskComplexity.HIGH,),
            reasoning_steps=self._estimate_reasoning_steps(complexity),
        )
    
    def _classify_type(self, description: str) -> TaskType:
        """分类任务类型"""
        desc_lower = description.lower()
        
        for task_type, keywords in self.TYPE_KEYWORDS.items():
            if any(kw in desc_lower for kw in keywords):
                return task_type
        
        # 默认类型
        return TaskType.GENERATION
    
    def _classify_complexity(self, description: str) -> TaskComplexity:
        """分类任务复杂度"""
        desc_lower = description.lower()
        length = len(description)
        
        # 基于关键词判断
        for complexity, keywords in self.COMPLEXITY_KEYWORDS.items():
            if any(kw in desc_lower for kw in keywords):
                return complexity
        
        # 基于长度判断
        if length > 500:
            return TaskComplexity.HIGH
        elif length > 100:
            return TaskComplexity.MEDIUM
        else:
            return TaskComplexity.LOW
    
    def _estimate_tokens(
        self,
        description: str,
        task_type: TaskType,
        complexity: TaskComplexity,
    ) -> int:
        """预估token数"""
        # 基础token数（按字符数估算，约4字符/token）
        base_tokens = max(len(description) // 4, 100)
        
        # 任务类型系数
        type_multiplier = {
            TaskType.ANALYSIS: 2.0,
            TaskType.GENERATION: 1.5,
            TaskType.REASONING: 3.0,
            TaskType.SUMMARIZATION: 1.0,
            TaskType.CLASSIFICATION: 1.0,
        }
        
        # 复杂度系数
        complexity_multiplier = {
            TaskComplexity.LOW: 1.0,
            TaskComplexity.MEDIUM: 2.0,
            TaskComplexity.HIGH: 4.0,
        }
        
        estimated = int(
            base_tokens
            * type_multiplier.get(task_type, 1.0)
            * complexity_multiplier.get(complexity, 1.0)
        )
        
        # 限制范围
        return max(100, min(estimated, 100000))
    
    def _estimate_reasoning_steps(self, complexity: TaskComplexity) -> int:
        """预估推理步骤数"""
        steps_map = {
            TaskComplexity.LOW: 1,
            TaskComplexity.MEDIUM: 3,
            TaskComplexity.HIGH: 5,
        }
        return steps_map.get(complexity, 1)
