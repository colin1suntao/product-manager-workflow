"""经验收集器 - 从任务执行中收集经验"""

import json
import logging
import threading
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from pm_workstation.agents.evolution.evolution_models import (
    ExperienceQuality,
    ExperienceRecord,
    ExperienceType,
)
from pm_workstation.orchestrator.workflow_state import WorkflowState

logger = logging.getLogger(__name__)


class ExperienceCollector:
    """经验收集器

    从任务执行中收集经验数据，包括：
    - 任务执行结果
    - 用户反馈
    - 性能指标
    - Agent 执行情况
    """

    def __init__(self, storage_dir: str = "./data/evolution/experiences"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.index_file = self.storage_dir / "experience_index.json"
        self._index: dict[str, str] = {}  # experience_id -> file_path
        self._cache: dict[str, ExperienceRecord] = {}  # 内存缓存，避免重复读文件
        self._lock = threading.Lock()
        self._load_index()

    def _load_index(self):
        """加载索引"""
        if self.index_file.exists():
            try:
                with open(self.index_file, encoding="utf-8") as f:
                    self._index = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load experience index: {e}")
                self._index = {}

    def _save_index(self):
        """保存索引"""
        try:
            with open(self.index_file, "w", encoding="utf-8") as f:
                json.dump(self._index, f, ensure_ascii=False, indent=2)
        except OSError as e:
            logger.error(f"Failed to save index: {e}")

    def count_experiences(self) -> int:
        """返回经验总数（使用索引，避免读取文件）"""
        return len(self._index)

    def collect_from_workflow(self, state: WorkflowState, user_feedback: str | None = None) -> ExperienceRecord:
        """从工作流执行中收集经验

        Args:
            state: 工作流状态
            user_feedback: 用户反馈

        Returns:
            经验记录
        """
        run = state.workflow_run

        # 确定经验类型和质量
        if run.status.value == "completed":
            experience_type = ExperienceType.TASK_SUCCESS
            quality = self._evaluate_quality(state, user_feedback)
        elif run.status.value == "failed":
            experience_type = ExperienceType.TASK_FAILURE
            quality = ExperienceQuality.POOR
        else:
            experience_type = ExperienceType.PERFORMANCE_METRIC
            quality = ExperienceQuality.AVERAGE

        # 提取关键洞察
        insights = self._extract_insights(state)
        best_practices = self._extract_best_practices(state)
        pitfalls = self._extract_pitfalls(state)

        # 计算性能指标
        execution_time = self._calculate_execution_time(state)
        token_usage = self._extract_token_usage(state)

        experience = ExperienceRecord(
            id=str(uuid4()),
            workflow_id=run.id,
            task_type=self._identify_task_type(state),
            experience_type=experience_type,
            quality=quality,
            requirement_text=run.requirement_text or "",
            selected_skills=getattr(state, 'selected_skills', []),
            agent_chain=self._extract_agent_chain(state),
            success=run.status.value == "completed",
            error_message=run.error_message,
            user_feedback=user_feedback,
            user_satisfaction=self._parse_satisfaction(user_feedback),
            execution_time_seconds=execution_time,
            token_usage=token_usage,
            retry_count=getattr(run, 'retry_count', 0),
            key_insights=insights,
            best_practices=best_practices,
            pitfalls=pitfalls,
            optimization_suggestions=self._generate_suggestions(state),
            version="1.0",
            created_at=datetime.utcnow(),
        )

        # 保存经验
        self._save_experience(experience)

        logger.info(f"Collected experience: {experience.id} (quality={quality.value}, success={experience.success})")
        return experience

    def _evaluate_quality(self, state: WorkflowState, user_feedback: str | None) -> ExperienceQuality:
        """评估经验质量"""
        # 有正面用户反馈 = 优秀
        if user_feedback:
            if any(word in user_feedback.lower() for word in ['很好', '优秀', '满意', 'good', 'excellent', 'great']):
                return ExperienceQuality.EXCELLENT
            if any(word in user_feedback.lower() for word in ['不错', '可以', 'ok', 'fine']):
                return ExperienceQuality.GOOD
            if any(word in user_feedback.lower() for word in ['差', '不好', '失望', 'bad', 'poor']):
                return ExperienceQuality.POOR

        # 根据执行结果评估
        run = state.workflow_run
        if run.status.value == "completed":
            # 检查是否有产出物
            has_prototype = bool(getattr(state, 'prototype_html', None))
            has_document = bool(getattr(state, 'prd_document', None))
            has_verification = bool(getattr(state, 'verification_report', None))

            if has_prototype and has_document and has_verification:
                return ExperienceQuality.EXCELLENT
            elif has_prototype or has_document:
                return ExperienceQuality.GOOD
            return ExperienceQuality.AVERAGE

        return ExperienceQuality.AVERAGE

    def _extract_insights(self, state: WorkflowState) -> list[str]:
        """提取关键洞察"""
        insights = []

        # 从 Coordinator 总结中提取
        if hasattr(state, 'coordinator_summary') and state.coordinator_summary:
            insights.append(f"任务拆解策略：{state.coordinator_summary[:100]}")

        # 从 Agent 执行链中提取
        agent_chain = self._extract_agent_chain(state)
        if len(agent_chain) > 3:
            insights.append(f"复杂任务需要 {len(agent_chain)} 个 Agent 协作")

        # 从验证报告中提取
        if hasattr(state, 'verification_report') and state.verification_report:
            report = state.verification_report
            if hasattr(report, 'manual_review_required'):
                issues = report.manual_review_required or []
            elif isinstance(report, dict):
                issues = report.get('manual_review_required', [])
            else:
                issues = []
            if issues:
                insights.append(f"发现 {len(issues)} 个需要人工审查的问题")

        return insights[:5]  # 最多 5 条

    def _extract_best_practices(self, state: WorkflowState) -> list[str]:
        """提取最佳实践"""
        practices = []

        # 成功的任务拆解模式
        if hasattr(state, 'task_decomposition') and state.task_decomposition:
            subtasks = state.task_decomposition.get('subtasks', [])
            if subtasks and len(subtasks) <= 5:
                practices.append(f"建议将任务拆解为 {len(subtasks)} 个子任务")

        # 有效的技能组合
        skills = getattr(state, 'selected_skills', [])
        if len(skills) > 0:
            practices.append(f"有效技能组合：{', '.join(skills[:3])}")

        return practices[:3]

    def _extract_pitfalls(self, state: WorkflowState) -> list[str]:
        """提取陷阱/注意事项"""
        pitfalls = []

        # 错误信息
        run = state.workflow_run
        if run.error_message:
            pitfalls.append(f"错误：{run.error_message[:200]}")

        # 重试情况
        if getattr(run, 'retry_count', 0) > 2:
            pitfalls.append(f"任务重试 {run.retry_count} 次，可能存在稳定性问题")

        # 超时情况
        execution_time = self._calculate_execution_time(state)
        if execution_time > 300:  # 5 分钟
            pitfalls.append(f"执行时间过长 ({execution_time:.1f}s)，建议优化")

        return pitfalls[:5]

    def _generate_suggestions(self, state: WorkflowState) -> list[str]:
        """生成优化建议"""
        suggestions = []

        # Token 用量优化
        token_usage = self._extract_token_usage(state)
        total_tokens = sum(token_usage.values())
        if total_tokens > 50000:
            suggestions.append(f"Token 用量较大 ({total_tokens})，考虑优化 prompt 或使用更高效的模型")

        # 执行时间优化
        execution_time = self._calculate_execution_time(state)
        if execution_time > 180:
            suggestions.append(f"执行时间 {execution_time:.1f}s，考虑并行执行或简化流程")

        # 技能使用优化
        skills = getattr(state, 'selected_skills', [])
        if len(skills) > 5:
            suggestions.append(f"使用了 {len(skills)} 个技能，建议精简到 3-5 个核心技能")

        return suggestions[:3]

    def _identify_task_type(self, state: WorkflowState) -> str:
        """识别任务类型"""
        # 从需求文本中识别
        requirement = state.workflow_run.requirement_text or ""

        if any(kw in requirement for kw in ['原型', '界面', 'UI', '页面']):
            return "prototype_generation"
        if any(kw in requirement for kw in ['文档', 'PRD', '需求']):
            return "document_generation"
        if any(kw in requirement for kw in ['市场调研', '竞品']):
            return "market_research"
        if any(kw in requirement for kw in ['分析', '拆解']):
            return "requirement_analysis"

        return "general_task"

    def _extract_agent_chain(self, state: WorkflowState) -> list[str]:
        """提取 Agent 执行链"""
        agents = []

        if hasattr(state, 'subtask_results') and state.subtask_results:
            results = state.subtask_results
            # subtask_results 可能是 dict[str, any] 或 list[dict]
            if isinstance(results, dict):
                items = results.values()
            elif isinstance(results, list):
                items = results
            else:
                items = []

            for task_result in items:
                if isinstance(task_result, dict):
                    agent_id = task_result.get('agent_id', 'unknown')
                    if agent_id and agent_id not in agents:
                        agents.append(agent_id)

        return agents

    def _calculate_execution_time(self, state: WorkflowState) -> float:
        """计算执行时间"""
        run = state.workflow_run
        if hasattr(run, 'created_at') and hasattr(run, 'updated_at'):
            delta = run.updated_at - run.created_at
            return delta.total_seconds()
        return 0.0

    def _extract_token_usage(self, state: WorkflowState) -> dict[str, int]:
        """提取 Token 用量"""
        token_usage: dict[str, int] = {}

        if hasattr(state, 'reasoning_trace') and state.reasoning_trace:
            trace_data = state.reasoning_trace
            # reasoning_trace 可能是 list[dict] 或 str(json) 或 str
            if isinstance(trace_data, list):
                items = trace_data
            elif isinstance(trace_data, str):
                try:
                    items = json.loads(trace_data)
                    if not isinstance(items, list):
                        items = []
                except (json.JSONDecodeError, TypeError):
                    items = []
            else:
                items = []

            for trace in items:
                if isinstance(trace, dict):
                    model = trace.get('model', 'unknown')
                    tokens = trace.get('token_usage', {})
                    if model and isinstance(tokens, dict):
                        token_usage[model] = tokens.get('total_tokens', 0)

        return token_usage

    def _parse_satisfaction(self, user_feedback: str | None) -> int | None:
        """解析用户满意度"""
        if not user_feedback:
            return None

        # 简单的关键词匹配（注意顺序：长词优先避免子串误匹配）
        positive = ['很好', '优秀', '满意', 'great', 'excellent', 'good', 'perfect']
        negative = ['不好', '糟糕', '差', '失望', '差劲', 'bad', 'poor', 'terrible', 'disappointed']

        feedback_lower = user_feedback.lower()
        positive_count = sum(1 for word in positive if word in feedback_lower)
        negative_count = sum(1 for word in negative if word in feedback_lower)

        if positive_count > negative_count:
            return 5 if positive_count >= 2 else 4
        elif negative_count > positive_count:
            return 2 if negative_count >= 2 else 3
        return 3

    def _save_experience(self, experience: ExperienceRecord):
        """保存经验"""
        file_path = self.storage_dir / f"{experience.id}.json"

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(experience.model_dump(), f, ensure_ascii=False, indent=2, default=str)
            self._index[experience.id] = str(file_path)
            self._cache[experience.id] = experience
            self._save_index()
        except OSError as e:
            logger.error(f"Failed to save experience {experience.id}: {e}")

    def get_experience(self, experience_id: str) -> ExperienceRecord | None:
        """获取经验"""
        cached = self._cache.get(experience_id)
        if cached is not None:
            return cached

        if experience_id not in self._index:
            return None

        file_path = self._index[experience_id]
        if not Path(file_path).exists():
            return None

        try:
            with open(file_path, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError, FileNotFoundError):
            logger.error(f"Failed to read experience file {experience_id}")
            return None

        try:
            experience = ExperienceRecord(**data)
            self._cache[experience_id] = experience
            return experience
        except Exception as e:
            logger.error(f"Failed to deserialize experience {experience_id}: {e}")
            return None

    def list_experiences(
        self,
        task_type: str | None = None,
        quality: ExperienceQuality | None = None,
        success: bool | None = None,
        limit: int = 100,
    ) -> list[ExperienceRecord]:
        """列出经验

        Args:
            task_type: 任务类型过滤
            quality: 质量等级过滤
            success: 成功/失败过滤
            limit: 数量限制

        Returns:
            经验记录列表
        """
        experiences = []

        with self._lock:
            index_ids = list(self._index.keys())
            for exp_id in index_ids:
                exp = self._cache.get(exp_id)
                if exp is None:
                    exp = self.get_experience(exp_id)
                    if exp is None:
                        continue

                # 过滤
                if task_type and exp.task_type != task_type:
                    continue
                if quality and exp.quality != quality:
                    continue
                if success is not None and exp.success != success:
                    continue

                experiences.append(exp)
                if len(experiences) >= limit:
                    break

        return experiences
