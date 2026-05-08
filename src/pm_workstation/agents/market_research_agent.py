"""市场调研报告生成 Agent

根据用户调研需求和选中的 PM Skills 生成市场调研报告。
"""

import logging
from typing import Callable

from pm_workstation.model_router.base import LLMBackend, LLMMessage
from pm_workstation.model_router.fallback_handler import FallbackHandler
from pm_workstation.skills.loader import SkillLoader, Skill

logger = logging.getLogger(__name__)


class SkillRecommendation:
    """技能推荐结果"""

    def __init__(self, name: str, description: str, relevance_score: float, category: str):
        self.name = name
        self.description = description
        self.relevance_score = relevance_score
        self.category = category

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "relevance_score": self.relevance_score,
            "category": self.category,
        }


# 技能分类映射
SKILL_CATEGORIES = {
    "pestel-analysis": "macro",
    "tam-sam-som-calculator": "market",
    "company-research": "competitor",
    "proto-persona": "customer",
    "customer-journey-map": "customer",
    "customer-journey-mapping-workshop": "customer",
    "jobs-to-be-done": "customer",
    "discovery-interview-prep": "customer",
    "discovery-process": "customer",
    "positioning-statement": "strategy",
    "positioning-workshop": "strategy",
    "product-strategy-session": "strategy",
    "roadmap-planning": "strategy",
    "opportunity-solution-tree": "strategy",
    "problem-statement": "strategy",
    "problem-framing-canvas": "strategy",
    "epic-hypothesis": "strategy",
    "feature-investment-advisor": "strategy",
    "finance-based-pricing-advisor": "market",
    "finance-metrics-quickref": "market",
    "saas-revenue-growth-metrics": "market",
    "saas-economics-efficiency-metrics": "market",
    "acquisition-channel-advisor": "market",
    "business-health-diagnostic": "market",
}

# 关键词到技能的映射
KEYWORD_SKILL_MAP = {
    # 宏观环境
    "宏观": ["pestel-analysis"],
    "政策": ["pestel-analysis"],
    "政治": ["pestel-analysis"],
    "经济": ["pestel-analysis", "saas-revenue-growth-metrics"],
    "社会": ["pestel-analysis"],
    "技术": ["pestel-analysis"],
    "环境": ["pestel-analysis"],
    "法律": ["pestel-analysis"],
    "PESTEL": ["pestel-analysis"],

    # 市场规模
    "市场规模": ["tam-sam-som-calculator"],
    "TAM": ["tam-sam-som-calculator"],
    "SAM": ["tam-sam-som-calculator"],
    "SOM": ["tam-sam-som-calculator"],
    "市场容量": ["tam-sam-som-calculator"],
    "市场潜力": ["tam-sam-som-calculator"],

    # 竞争对手
    "竞争对手": ["company-research"],
    "竞品": ["company-research"],
    "公司研究": ["company-research"],
    "行业分析": ["company-research", "pestel-analysis"],

    # 用户研究
    "用户画像": ["proto-persona"],
    "用户研究": ["proto-persona", "jobs-to-be-done", "discovery-interview-prep"],
    "客户": ["proto-persona", "customer-journey-map", "jobs-to-be-done"],
    "客户旅程": ["customer-journey-map"],
    "旅程图": ["customer-journey-map"],
    "用户旅程": ["customer-journey-map"],

    # 需求分析
    "需求": ["jobs-to-be-done", "discovery-process"],
    "痛点": ["jobs-to-be-done", "problem-statement"],
    "JTBD": ["jobs-to-be-done"],
    "访谈": ["discovery-interview-prep", "discovery-process"],

    # 产品策略
    "定位": ["positioning-statement", "positioning-workshop"],
    "产品定位": ["positioning-statement"],
    "战略": ["product-strategy-session", "roadmap-planning"],
    "路线图": ["roadmap-planning"],
    "规划": ["roadmap-planning", "product-strategy-session"],

    # 财务分析
    "定价": ["finance-based-pricing-advisor"],
    "财务": ["finance-metrics-quickref", "saas-revenue-growth-metrics"],
    "收入": ["saas-revenue-growth-metrics"],
    "增长": ["saas-revenue-growth-metrics", "acquisition-channel-advisor"],
    "获客": ["acquisition-channel-advisor"],

    # 综合
    "市场调研": ["pestel-analysis", "tam-sam-som-calculator", "proto-persona"],
    "调研": ["pestel-analysis", "tam-sam-som-calculator", "company-research"],
    "分析": ["pestel-analysis", "company-research"],
}


class MarketResearchAgent:
    """市场调研报告生成器

    根据用户调研需求和选中的 PM Skills 生成结构化的市场调研报告。
    """

    def __init__(self, llm_handler: LLMBackend | FallbackHandler):
        """初始化市场调研生成器

        Args:
            llm_handler: LLM 处理器
        """
        self.llm_handler = llm_handler
        self.skill_loader = SkillLoader()

    async def generate_report(
        self,
        requirement_text: str,
        selected_skills: list[str],
        callback: Callable | None = None,
    ) -> str:
        """生成市场调研报告

        Args:
            requirement_text: 调研需求描述
            selected_skills: 选中的 PM Skills 名称列表
            callback: 进度回调函数 (step: int, total: int, message: str)

        Returns:
            Markdown 格式的调研报告
        """
        # 加载选中的技能
        skills = self.skill_loader.load_multiple(selected_skills)
        if not skills:
            return self._generate_fallback_report(requirement_text)

        total_steps = len(skills) + 1  # +1 for final assembly
        sections: dict[str, str] = {}

        # 为每个技能生成对应的报告章节
        for i, skill in enumerate(skills, 1):
            if callback:
                callback(i, total_steps, f"正在生成 {skill.name} 分析...")

            try:
                section = await self._generate_skill_section(skill, requirement_text)
                sections[skill.name] = section
            except Exception as e:
                logger.error(f"Failed to generate section for {skill.name}: {e}")
                sections[skill.name] = f"**{skill.name} 分析生成失败**: {str(e)}"

        # 组装完整报告
        if callback:
            callback(total_steps, total_steps, "正在组装完整报告...")

        report = self._build_report_structure(requirement_text, skills, sections)
        return report

    async def _generate_skill_section(
        self,
        skill: Skill,
        requirement_text: str,
    ) -> str:
        """生成单个技能对应的报告章节

        Args:
            skill: PM Skill 对象
            requirement_text: 调研需求描述

        Returns:
            该技能对应的 Markdown 章节内容
        """
        system_prompt = skill.system_prompt or skill.get_full_prompt()

        user_prompt = f"""请基于以下调研需求，使用 {skill.name} 方法论进行分析：

## 调研需求

{requirement_text}

## 分析要求

请使用 {skill.name} 的框架和方法论，生成详细的分析内容。

要求：
1. 分析内容必须基于 {skill.name} 的核心概念和步骤
2. 使用 Markdown 格式输出
3. 包含具体的分析结论和建议
4. 如果有数据表格，请使用 Markdown 表格格式
5. 分析内容应直接可用于市场调研报告

请直接输出分析内容，不要添加额外的解释。"""

        response = await self.llm_handler.chat([
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=user_prompt),
        ])

        return self._extract_section_content(response.content, skill.name)

    def _extract_section_content(self, content: str, skill_name: str) -> str:
        """提取章节内容"""
        content = content.strip()

        # 尝试提取 ```markdown 代码块
        if "```markdown" in content:
            start = content.index("```markdown") + 11
            end = content.find("```", start)
            if end != -1:
                return content[start:end].strip()
            return content[start:].strip()

        # 尝试提取 ``` 代码块
        if "```" in content:
            start = content.index("```") + 3
            end = content.find("```", start)
            if end != -1:
                return content[start:end].strip()
            return content[start:].strip()

        return content

    def _build_report_structure(
        self,
        requirement_text: str,
        skills: list[Skill],
        sections: dict[str, str],
    ) -> str:
        """组装完整的报告结构

        Args:
            requirement_text: 调研需求描述
            skills: 使用的技能列表
            sections: 各技能对应的章节内容

        Returns:
            完整的 Markdown 报告
        """
        parts = []

        # 报告标题
        parts.append("# 市场调研报告\n")

        # 报告概述
        parts.append("## 调研概述\n")
        parts.append(f"**调研需求**: {requirement_text}\n")
        parts.append(f"**使用工具**: {', '.join(s.name for s in skills)}\n")
        parts.append("")

        # 各章节内容
        chapter_num = 1
        for skill in skills:
            section_content = sections.get(skill.name, "（内容生成失败）")
            parts.append(f"## {chapter_num}. {skill.name}\n")
            parts.append(section_content)
            parts.append("")
            chapter_num += 1

        # 总结与建议
        parts.append("## 总结与建议\n")
        parts.append("基于以上分析，我们建议：\n")
        parts.append("（此部分可由用户手动补充或后续 AI 生成）\n")

        return "\n".join(parts)

    def _generate_fallback_report(self, requirement_text: str) -> str:
        """当无可用技能时生成兜底报告"""
        return f"""# 市场调研报告

## 调研概述

**调研需求**: {requirement_text}

## 说明

未能加载相关的 PM Skills，请确保技能库已正确配置。

## 基础分析框架

建议从以下维度进行市场调研：

1. **宏观环境分析 (PESTEL)**
   - 政治因素
   - 经济因素
   - 社会因素
   - 技术因素
   - 环境因素
   - 法律因素

2. **市场规模评估 (TAM/SAM/SOM)**
   - 总可寻址市场 (TAM)
   - 可服务市场 (SAM)
   - 可获得市场 (SOM)

3. **目标用户分析**
   - 用户画像
   - 用户痛点
   - 用户旅程

4. **竞争格局分析**
   - 主要竞争对手
   - 竞争优势
   - 市场份额

请根据以上框架手动补充调研内容。
"""

    def recommend_skills(self, requirement_text: str) -> list[SkillRecommendation]:
        """根据需求文本推荐相关技能

        Args:
            requirement_text: 调研需求描述

        Returns:
            推荐的技能列表，按相关性排序
        """
        text_lower = requirement_text.lower()
        skill_scores: dict[str, float] = {}

        # 基于关键词匹配计算相关性分数
        for keyword, skill_names in KEYWORD_SKILL_MAP.items():
            if keyword.lower() in text_lower:
                for skill_name in skill_names:
                    current_score = skill_scores.get(skill_name, 0)
                    skill_scores[skill_name] = max(current_score, 0.8)

        # 如果没有匹配到关键词，返回默认推荐
        if not skill_scores:
            default_skills = [
                "pestel-analysis",
                "tam-sam-som-calculator",
                "proto-persona",
                "company-research",
            ]
            for skill_name in default_skills:
                skill_scores[skill_name] = 0.5

        # 构建推荐结果
        recommendations = []
        for skill_name, score in sorted(skill_scores.items(), key=lambda x: x[1], reverse=True):
            skill = self.skill_loader.load(skill_name)
            if skill:
                category = SKILL_CATEGORIES.get(skill_name, "other")
                recommendations.append(SkillRecommendation(
                    name=skill_name,
                    description=skill.description,
                    relevance_score=score,
                    category=category,
                ))

        return recommendations
