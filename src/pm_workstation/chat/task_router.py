"""Task Router - 任务路由器

根据任务类型分发给对应的子 Agent 执行。
"""

import logging
from datetime import datetime
from typing import Any, Optional

from ..agents.huashu_prototype_generator import HuashuPrototypeGenerator
from ..agents.market_research_agent import MarketResearchAgent
from ..agents.prd_generator import PRDGenerator
from ..agents.requirement_parser import RequirementParser
from ..model_router.base import LLMBackend
from ..skills.loader import SkillLoader
from .chat_models import Artifact, TaskMode, TaskResult, TaskStatus

logger = logging.getLogger(__name__)


class TaskRouter:
    """任务路由器

    根据任务模式将任务分发给对应的子 Agent 执行。
    """

    def __init__(self, llm_handler: Optional[LLMBackend] = None):
        """初始化任务路由器

        Args:
            llm_handler: LLM 处理器
        """
        self.llm_handler = llm_handler
        self.skill_loader = SkillLoader()
        self._task_counter = 0

    def _generate_task_id(self) -> str:
        """生成任务 ID"""
        self._task_counter += 1
        return f"task-{self._task_counter:06d}"

    async def execute_task(
        self,
        mode: TaskMode,
        params: dict[str, Any],
        selected_skills: Optional[list[str]] = None,
    ) -> TaskResult:
        """执行任务

        Args:
            mode: 任务模式
            params: 任务参数
            selected_skills: 选中的技能列表

        Returns:
            任务执行结果
        """
        task_id = self._generate_task_id()
        started_at = datetime.now()

        logger.info(f"Executing task {task_id} with mode {mode}")

        try:
            if mode == TaskMode.REQUIREMENT:
                result = await self._execute_requirement_task(params, selected_skills)
            elif mode == TaskMode.PROTOTYPE:
                result = await self._execute_prototype_task(params, selected_skills)
            elif mode == TaskMode.PRD:
                result = await self._execute_prd_task(params, selected_skills)
            elif mode == TaskMode.MARKET_RESEARCH:
                result = await self._execute_market_research_task(params, selected_skills)
            else:
                raise ValueError(f"Unknown task mode: {mode}")

            return TaskResult(
                task_id=task_id,
                task_mode=mode,
                status=TaskStatus.COMPLETED,
                output=result.get("output"),
                artifacts=result.get("artifacts", []),
                started_at=started_at,
                completed_at=datetime.now(),
            )

        except Exception as e:
            logger.error(f"Task {task_id} failed: {e}")
            return TaskResult(
                task_id=task_id,
                task_mode=mode,
                status=TaskStatus.FAILED,
                error_message=str(e),
                started_at=started_at,
                completed_at=datetime.now(),
            )

    async def _execute_requirement_task(
        self,
        params: dict[str, Any],
        selected_skills: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """执行需求分析任务

        Args:
            params: 任务参数，包含 requirement_text
            selected_skills: 选中的技能列表

        Returns:
            任务结果
        """
        requirement_text = params.get("requirement_text", "")
        if not requirement_text:
            raise ValueError("Missing requirement_text parameter")

        if not self.llm_handler:
            # 返回一个基本的需求分析结果，而不是抛出异常
            return {
                "output": f"""## 需求分析结果

### 原始需求
{requirement_text}

### 初步分析
由于 LLM 服务未配置，无法进行深度需求分析。以下是对您需求的初步理解：

**需求概述**：{requirement_text[:200]}{'...' if len(requirement_text) > 200 else ''}

### 建议
1. 请配置 LLM 服务以获得更详细的需求分析
2. 您可以手动补充以下信息：
   - 功能需求列表
   - 非功能需求（性能、安全等）
   - 约束条件
   - 验收标准
"""
            }

        # 使用需求解析器
        parser = RequirementParser(llm_handler=self.llm_handler)
        structured_req = await parser.parse(requirement_text)

        output = f"""## 需求分析结果

### 原始需求
{requirement_text}

### 结构化需求
- **功能需求**: {structured_req.functional_requirements if hasattr(structured_req, 'functional_requirements') else '已解析'}
- **非功能需求**: {structured_req.non_functional_requirements if hasattr(structured_req, 'non_functional_requirements') else '已解析'}
- **约束条件**: {structured_req.constraints if hasattr(structured_req, 'constraints') else '已解析'}
"""
        return {"output": output}

    async def _execute_prototype_task(
        self,
        params: dict[str, Any],
        selected_skills: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """执行原型设计任务

        Args:
            params: 任务参数，包含 requirement_text
            selected_skills: 选中的技能列表

        Returns:
            任务结果
        """
        requirement_text = params.get("requirement_text", "")
        if not requirement_text:
            raise ValueError("Missing requirement_text parameter")

        if not self.llm_handler:
            # 返回一个提示信息，而不是抛出异常
            return {
                "output": "原型设计功能需要 LLM 服务支持。\n\n请在 **设置 > LLM 配置** 中配置有效的 LLM API Key 后重试。",
                "artifacts": [],
            }

        # 加载技能内容
        skills_content = []
        if selected_skills:
            skills = self.skill_loader.load_multiple(selected_skills)
            skills_content = [s.get_full_prompt() for s in skills]

        # 生成原型
        generator = HuashuPrototypeGenerator(llm_handler=self.llm_handler)
        prototype_html = await generator.generate(
            requirement_text=requirement_text,
            skills=skills_content,
        )

        # 保存原型文件
        import os
        artifacts_dir = os.path.join(
            os.path.dirname(__file__), "..", "artifacts", "chat"
        )
        os.makedirs(artifacts_dir, exist_ok=True)

        filename = f"prototype_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        filepath = os.path.join(artifacts_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(prototype_html)

        return {
            "output": "原型已生成，请查看附件。",
            "artifacts": [
                Artifact(
                    type="prototype",
                    name=filename,
                    url=f"/artifacts/chat/{filename}",
                )
            ],
        }

    async def _execute_prd_task(
        self,
        params: dict[str, Any],
        selected_skills: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """执行文档撰写任务

        Args:
            params: 任务参数，包含 requirement_text
            selected_skills: 选中的技能列表

        Returns:
            任务结果
        """
        requirement_text = params.get("requirement_text", "")
        if not requirement_text:
            raise ValueError("Missing requirement_text parameter")

        if not self.llm_handler:
            # 返回一个提示信息，而不是抛出异常
            return {
                "output": "PRD 文档生成功能需要 LLM 服务支持。\n\n请在 **设置 > LLM 配置** 中配置有效的 LLM API Key 后重试。",
                "artifacts": [],
            }

        # 加载技能内容
        skills_content = []
        if selected_skills:
            skills = self.skill_loader.load_multiple(selected_skills)
            skills_content = [s.get_full_prompt() for s in skills]

        # 生成 PRD
        generator = PRDGenerator(llm_handler=self.llm_handler)
        prd_content = await generator.generate(
            requirement_text=requirement_text,
            skills=skills_content,
        )

        # 保存 PRD 文件
        import os
        artifacts_dir = os.path.join(
            os.path.dirname(__file__), "..", "artifacts", "chat"
        )
        os.makedirs(artifacts_dir, exist_ok=True)

        filename = f"prd_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        filepath = os.path.join(artifacts_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(prd_content)

        return {
            "output": prd_content,
            "artifacts": [
                Artifact(
                    type="document",
                    name=filename,
                    url=f"/artifacts/chat/{filename}",
                )
            ],
        }

    async def _execute_market_research_task(
        self,
        params: dict[str, Any],
        selected_skills: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """执行市场调研任务

        Args:
            params: 任务参数，包含 requirement_text
            selected_skills: 选中的技能列表

        Returns:
            任务结果
        """
        requirement_text = params.get("requirement_text", "")
        if not requirement_text:
            raise ValueError("Missing requirement_text parameter")

        if not self.llm_handler:
            # 返回一个提示信息，而不是抛出异常
            return {
                "output": "市场调研功能需要 LLM 服务支持。\n\n请在 **设置 > LLM 配置** 中配置有效的 LLM API Key 后重试。",
                "artifacts": [],
            }

        # 如果没有指定技能，使用默认的市场调研技能
        if not selected_skills:
            selected_skills = ["pestel-analysis", "tam-sam-som-calculator"]

        # 生成调研报告
        agent = MarketResearchAgent(llm_handler=self.llm_handler)
        report_content = await agent.generate_report(
            requirement_text=requirement_text,
            selected_skills=selected_skills,
        )

        # 保存报告文件
        import os
        artifacts_dir = os.path.join(
            os.path.dirname(__file__), "..", "artifacts", "chat"
        )
        os.makedirs(artifacts_dir, exist_ok=True)

        filename = f"market_research_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        filepath = os.path.join(artifacts_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(report_content)

        return {
            "output": report_content,
            "artifacts": [
                Artifact(
                    type="report",
                    name=filename,
                    url=f"/artifacts/chat/{filename}",
                )
            ],
        }
