"""PM Workflows - 预定义的产品经理工作流

包含产品设计、市场调研、用户研究等常用工作流模板。
"""

import logging

from .workflow_models import WorkflowDefinition, WorkflowStep

logger = logging.getLogger(__name__)


PM_WORKFLOWS: list[WorkflowDefinition] = [
    WorkflowDefinition(
        id="full-product-design",
        name="完整产品设计流程",
        description="从需求分析到原型设计和文档撰写的完整产品设计流程",
        version="1.0.0",
        category="product-design",
        steps=[
            WorkflowStep(
                id="step-1-requirement",
                name="需求分析",
                description="梳理需求，生成用户故事和功能点",
                mode="requirement",
                skills=["user-story", "jobs-to-be-done"],
                agent_id="requirement-analyst",
                timeout=60,
                priority=8,
            ),
            WorkflowStep(
                id="step-2-prototype",
                name="原型设计",
                description="生成高保真界面原型",
                mode="prototype",
                skills=["huashu-design"],
                agent_id="prototype-designer",
                depends_on="step-1-requirement",
                input_from_dependency="requirement_output",
                timeout=90,
                priority=9,
            ),
            WorkflowStep(
                id="step-3-prd",
                name="PRD撰写",
                description="生成产品需求文档",
                mode="prd",
                skills=["prd-template"],
                agent_id="prd-writer",
                depends_on="step-1-requirement",
                parallel_with="step-2-prototype",  # 与原型设计并行
                input_from_dependency="requirement_output",
                timeout=60,
                priority=7,
            ),
            WorkflowStep(
                id="step-4-quality-check",
                name="质量检验",
                description="检验原型和文档的一致性和完整性",
                mode="verification",
                skills=["document-verification", "prototype-verification"],
                agent_id="quality-checker",
                depends_on="step-2-prototype",
                timeout=45,
                priority=5,
                optional=True,  # 可选步骤
            ),
        ],
        estimated_time="10-15 minutes",
        best_for=["新产品设计", "功能迭代", "从0到1", "产品规划"],
        tags=["产品设计", "需求分析", "原型", "PRD", "完整流程"],
        author="system",
    ),

    WorkflowDefinition(
        id="quick-prototype",
        name="快速原型设计",
        description="快速生成界面原型，适合简单功能或验证想法",
        version="1.0.0",
        category="product-design",
        steps=[
            WorkflowStep(
                id="step-1-quick-analysis",
                name="快速需求梳理",
                description="快速梳理核心功能和页面结构",
                mode="requirement",
                skills=["user-story"],
                agent_id="requirement-analyst",
                timeout=30,
                priority=7,
            ),
            WorkflowStep(
                id="step-2-quick-prototype",
                name="快速原型",
                description="生成简洁的界面原型",
                mode="prototype",
                skills=["huashu-design"],
                agent_id="prototype-designer",
                depends_on="step-1-quick-analysis",
                input_from_dependency="requirement_output",
                timeout=60,
                priority=9,
            ),
        ],
        estimated_time="5-8 minutes",
        best_for=["快速验证", "简单功能", "头脑风暴", "原型预览"],
        tags=["快速", "原型", "验证"],
        author="system",
    ),

    WorkflowDefinition(
        id="market-research-full",
        name="完整市场调研流程",
        description="市场分析 + 竞品研究 + 用户洞察的完整调研流程",
        version="1.0.0",
        category="market-research",
        steps=[
            WorkflowStep(
                id="step-1-market-analysis",
                name="市场分析",
                description="市场规模、趋势、机会分析",
                mode="market_research",
                skills=["pestel-analysis", "tam-sam-som-calculator"],
                agent_id="market-researcher",
                timeout=90,
                priority=7,
            ),
            WorkflowStep(
                id="step-2-competitive",
                name="竞品分析",
                description="竞争对手分析和对比",
                mode="market_research",
                skills=["competitive-analysis"],
                agent_id="market-researcher",
                parallel_with="step-1-market-analysis",  # 与市场分析并行
                timeout=75,
                priority=6,
            ),
            WorkflowStep(
                id="step-3-user-insight",
                name="用户洞察",
                description="用户画像和用户旅程分析",
                mode="market_research",
                skills=["customer-journey-map", "user-persona"],
                agent_id="user-researcher",
                depends_on="step-1-market-analysis",
                timeout=75,
                priority=7,
            ),
            WorkflowStep(
                id="step-4-strategy",
                name="战略建议",
                description="基于调研结果生成战略建议",
                mode="strategy",
                skills=["business-health-diagnostic", "positioning-statement"],
                agent_id="strategy-advisor",
                depends_on="step-3-user-insight",
                input_from_dependency="user_insight",
                timeout=60,
                priority=8,
            ),
        ],
        estimated_time="15-20 minutes",
        best_for=["市场进入决策", "竞品分析", "战略规划", "投资决策"],
        tags=["市场调研", "竞品", "战略", "用户研究"],
        author="system",
    ),

    WorkflowDefinition(
        id="user-research-flow",
        name="用户研究流程",
        description="用户访谈 + 用户旅程 + 用户画像",
        version="1.0.0",
        category="user-research",
        steps=[
            WorkflowStep(
                id="step-1-interview-prep",
                name="访谈准备",
                description="设计用户访谈提纲",
                mode="user-research",
                skills=["discovery-interview-prep"],
                agent_id="user-researcher",
                timeout=60,
                priority=7,
            ),
            WorkflowStep(
                id="step-2-journey",
                name="用户旅程地图",
                description="绘制用户旅程，识别关键节点",
                mode="user-research",
                skills=["customer-journey-map"],
                agent_id="user-researcher",
                parallel_with="step-1-interview-prep",  # 可以并行准备
                timeout=75,
                priority=7,
            ),
            WorkflowStep(
                id="step-3-persona",
                name="用户画像",
                description="创建详细的用户画像",
                mode="user-research",
                skills=["user-persona"],
                agent_id="user-researcher",
                depends_on="step-2-journey",
                input_from_dependency="journey_output",
                timeout=60,
                priority=6,
            ),
        ],
        estimated_time="10-15 minutes",
        best_for=["用户研究", "产品优化", "用户洞察", "访谈准备"],
        tags=["用户研究", "访谈", "用户旅程", "用户画像"],
        author="system",
    ),

    WorkflowDefinition(
        id="feature-spec",
        name="功能规格设计",
        description="单个功能的完整规格文档（用户故事 + 原型 + 规格说明）",
        version="1.0.0",
        category="product-design",
        steps=[
            WorkflowStep(
                id="step-1-feature-story",
                name="功能用户故事",
                description="生成功能的用户故事和验收标准",
                mode="requirement",
                skills=["user-story", "acceptance-criteria"],
                agent_id="requirement-analyst",
                timeout=45,
                priority=8,
            ),
            WorkflowStep(
                id="step-2-feature-prototype",
                name="功能原型",
                description="生成功能的界面原型",
                mode="prototype",
                skills=["huashu-design"],
                agent_id="prototype-designer",
                depends_on="step-1-feature-story",
                input_from_dependency="story_output",
                timeout=60,
                priority=9,
            ),
            WorkflowStep(
                id="step-3-feature-spec",
                name="功能规格说明",
                description="生成详细的功能规格说明文档",
                mode="prd",
                skills=["feature-spec-template"],
                agent_id="prd-writer",
                depends_on="step-2-feature-prototype",
                input_from_dependency="prototype_url",
                timeout=60,
                priority=7,
            ),
        ],
        estimated_time="8-12 minutes",
        best_for=["功能设计", "开发对接", "需求细化", "规格文档"],
        tags=["功能", "用户故事", "原型", "规格"],
        author="system",
    ),

    WorkflowDefinition(
        id="business-model-design",
        name="商业模式设计",
        description="商业模式画布 + 定位策略 + 商业计划",
        version="1.0.0",
        category="strategy",
        steps=[
            WorkflowStep(
                id="step-1-business-canvas",
                name="商业模式画布",
                description="绘制商业模式画布",
                mode="strategy",
                skills=["business-model-canvas"],
                agent_id="strategy-advisor",
                timeout=75,
                priority=8,
            ),
            WorkflowStep(
                id="step-2-positioning",
                name="产品定位",
                description="确定产品定位和差异化策略",
                mode="strategy",
                skills=["positioning-statement", "differentiation"],
                agent_id="strategy-advisor",
                depends_on="step-1-business-canvas",
                input_from_dependency="canvas_output",
                timeout=60,
                priority=8,
            ),
            WorkflowStep(
                id="step-3-gtm",
                name="市场进入策略",
                description="制定市场进入和推广策略",
                mode="strategy",
                skills=["go-to-market", "pricing-strategy"],
                agent_id="strategy-advisor",
                depends_on="step-2-positioning",
                input_from_dependency="positioning_output",
                timeout=75,
                priority=7,
            ),
        ],
        estimated_time="12-15 minutes",
        best_for=["商业模式", "战略规划", "产品定位", "市场进入"],
        tags=["商业模式", "定位", "战略", "GTM"],
        author="system",
    ),

    WorkflowDefinition(
        id="data-analysis-flow",
        name="数据分析流程",
        description="指标设计 + 数据分析 + A/B 测试计划",
        version="1.0.0",
        category="analytics",
        steps=[
            WorkflowStep(
                id="step-1-metrics",
                name="指标设计",
                description="设计产品指标体系",
                mode="data-analysis",
                skills=["north-star-metric", "metrics-framework"],
                agent_id="data-analyst",
                timeout=45,
                priority=7,
            ),
            WorkflowStep(
                id="step-2-analysis",
                name="数据分析",
                description="分析当前数据状态和趋势",
                mode="data-analysis",
                skills=["data-trend-analysis"],
                agent_id="data-analyst",
                depends_on="step-1-metrics",
                input_from_dependency="metrics",
                timeout=60,
                priority=6,
            ),
            WorkflowStep(
                id="step-3-ab-plan",
                name="A/B测试计划",
                description="设计 A/B 测试方案",
                mode="data-analysis",
                skills=["ab-test-design"],
                agent_id="data-analyst",
                depends_on="step-2-analysis",
                input_from_dependency="analysis_output",
                timeout=45,
                priority=5,
                optional=True,
            ),
        ],
        estimated_time="8-12 minutes",
        best_for=["数据分析", "指标设计", "A/B测试", "增长优化"],
        tags=["数据", "指标", "A/B测试", "分析"],
        author="system",
    ),
]


def get_workflow_by_id(workflow_id: str) -> WorkflowDefinition | None:
    """根据 ID 获取工作流

    Args:
        workflow_id: 工作流 ID

    Returns:
        工作流定义，如果不存在返回 None
    """
    for workflow in PM_WORKFLOWS:
        if workflow.id == workflow_id:
            return workflow
    return None


def get_workflows_by_category(category: str) -> list[WorkflowDefinition]:
    """根据分类获取工作流

    Args:
        category: 分类名称

    Returns:
        工作流列表
    """
    return [w for w in PM_WORKFLOWS if w.category == category]


def get_all_workflows() -> list[WorkflowDefinition]:
    """获取所有预定义工作流

    Returns:
        所有工作流列表
    """
    return PM_WORKFLOWS


def search_workflows(query: str) -> list[WorkflowDefinition]:
    """搜索工作流

    Args:
        query: 搜索关键词

    Returns:
        匹配的工作流列表
    """
    query_lower = query.lower()
    matched = []

    for workflow in PM_WORKFLOWS:
        # 匹配名称、描述、标签
        if (
            query_lower in workflow.name.lower()
            or query_lower in workflow.description.lower()
            or any(query_lower in tag.lower() for tag in workflow.tags)
            or any(query_lower in bf.lower() for bf in workflow.best_for)
        ):
            matched.append(workflow)

    return matched
