"""技能加载器模块

按需加载技能到 Agent 上下文。
"""

import logging
import re
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class Skill(BaseModel):
    """技能模型"""

    name: str
    description: str
    system_prompt: str = ""
    tools: list[str] = Field(default_factory=list)
    steps: list[str] = Field(default_factory=list)
    output_format: str = ""

    def get_full_prompt(self) -> str:
        """获取完整的技能提示（包含步骤和输出格式）"""
        parts = [self.system_prompt]

        if self.steps:
            parts.append("\n## 执行步骤\n")
            for i, step in enumerate(self.steps, 1):
                parts.append(f"{i}. {step}")

        if self.output_format:
            parts.append(f"\n## 输出格式\n\n{self.output_format}")

        return "\n".join(parts)


class SkillLoader:
    """技能加载器

    从文件系统加载技能定义，支持按需加载。
    """

    def __init__(self, skills_dir: str | None = None):
        self.skills_dir = Path(skills_dir) if skills_dir else Path(
            Path(__file__).parent.parent / "skills"
        )
        self._skills: dict[str, Skill] = {}
        self._load_all()

    def _load_all(self) -> None:
        """加载技能目录下的所有技能定义"""
        if not self.skills_dir.exists():
            logger.warning(f"Skills directory not found: {self.skills_dir}")
            return

        # 支持 .yaml 和 .md 格式
        for file_path in self.skills_dir.glob("*.yaml"):
            try:
                skill = self._load_from_yaml(file_path)
                self._skills[skill.name] = skill
            except Exception as e:
                logger.error(f"Failed to load skill from {file_path}: {e}")

        for file_path in self.skills_dir.glob("*.md"):
            try:
                skill = self._load_from_markdown(file_path)
                self._skills[skill.name] = skill
            except Exception as e:
                logger.error(f"Failed to load skill from {file_path}: {e}")

    def _load_from_yaml(self, file_path: Path) -> Skill:
        """从 YAML 文件加载技能"""
        with open(file_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        return Skill(
            name=data.get("name", file_path.stem),
            description=data.get("description", ""),
            system_prompt=data.get("system_prompt", ""),
            tools=data.get("tools", []),
            steps=data.get("steps", []),
            output_format=data.get("output_format", ""),
        )

    def _load_from_markdown(self, file_path: Path) -> Skill:
        """从 Markdown 文件加载技能"""
        content = file_path.read_text(encoding="utf-8")

        # 解析 YAML front matter
        front_matter = self._parse_front_matter(content)

        # 提取步骤（从 Markdown 内容中）
        steps = self._extract_steps(content)

        return Skill(
            name=front_matter.get("name", file_path.stem),
            description=front_matter.get("description", ""),
            system_prompt=front_matter.get("system_prompt", ""),
            tools=front_matter.get("tools", []),
            steps=steps,
            output_format=front_matter.get("output_format", ""),
        )

    @staticmethod
    def _parse_front_matter(content: str) -> dict[str, Any]:
        """解析 YAML front matter"""
        match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
        if not match:
            return {}

        try:
            return yaml.safe_load(match.group(1)) or {}
        except yaml.YAMLError:
            return {}

    @staticmethod
    def _extract_steps(content: str) -> list[str]:
        """从 Markdown 中提取步骤列表"""
        steps = []
        in_steps_section = False

        for line in content.split("\n"):
            if line.strip().startswith("## 执行步骤") or line.strip().startswith("## Steps"):
                in_steps_section = True
                continue

            if in_steps_section:
                # 遇到新的标题结束
                if line.strip().startswith("## "):
                    break

                # 匹配有序列表
                step_match = re.match(r"^\d+\.\s+(.*)", line.strip())
                if step_match:
                    steps.append(step_match.group(1))

        return steps

    def load(self, skill_name: str) -> Skill | None:
        """加载指定技能

        Args:
            skill_name: 技能名称

        Returns:
            技能对象，如果不存在返回 None
        """
        return self._skills.get(skill_name)

    def load_multiple(self, skill_names: list[str]) -> list[Skill]:
        """批量加载技能

        Args:
            skill_names: 技能名称列表

        Returns:
            技能对象列表
        """
        return [
            skill for name in skill_names
            if (skill := self.load(name)) is not None
        ]

    def list_available(self) -> list[str]:
        """列出所有可用的技能

        Returns:
            技能名称列表
        """
        return list(self._skills.keys())

    def get_skill_summary(self, skill_name: str) -> str | None:
        """获取技能摘要（名称和描述）"""
        skill = self._skills.get(skill_name)
        if not skill:
            return None
        return f"- **{skill.name}**: {skill.description}"
