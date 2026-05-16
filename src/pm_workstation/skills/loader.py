"""技能加载器模块

按需加载技能到 Agent 上下文。
支持两种格式：
1. 项目原生格式（YAML）
2. Product-Manager-Skills 格式（Markdown with YAML front matter）
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
    # PM Skills 扩展字段
    intent: str = ""
    skill_type: str = ""  # component/interactive/workflow
    best_for: list[str] = Field(default_factory=list)
    scenarios: list[str] = Field(default_factory=list)
    estimated_time: str = ""

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
    支持两种格式：
    1. 项目原生格式（YAML）
    2. Product-Manager-Skills 格式（Markdown with YAML front matter）
    3. 用户导入的技能（存储在 user-skills/ 目录）
    """

    def __init__(self, skills_dir: str | None = None):
        self.skills_dir = Path(skills_dir) if skills_dir else Path(
            Path(__file__).parent.parent / "skills"
        )
        self._user_skills_dir = self.skills_dir / "user-skills"
        self._skills: dict[str, Skill] = {}
        self._imported_skills: set[str] = set()
        self._load_all()

    def import_skill(self, content: str, filename: str = "") -> Skill:
        """从 SKILL.md 格式内容导入技能

        Args:
            content: SKILL.md 格式内容（含 YAML front matter）
            filename: 可选的文件名（用于持久化）

        Returns:
            导入的 Skill 对象

        Raises:
            ValueError: 内容解析失败或技能名已存在
        """
        front_matter = self._parse_front_matter(content)
        if not front_matter:
            raise ValueError("无法解析 YAML front matter，请确保内容以 --- 开头和结尾")

        name = front_matter.get("name", "").strip()
        if not name:
            raise ValueError("技能名称 (name) 不能为空")

        if name in self._skills:
            raise ValueError(f"技能 '{name}' 已存在")

        markdown_content = self._extract_markdown_content(content)
        system_prompt = self._build_pm_skill_prompt(front_matter, markdown_content)
        steps = self._extract_pm_skill_steps(markdown_content)

        skill = Skill(
            name=name,
            description=front_matter.get("description", ""),
            system_prompt=system_prompt,
            tools=[],
            steps=steps,
            output_format="",
            intent=front_matter.get("intent", ""),
            skill_type=front_matter.get("type", "component"),
            best_for=front_matter.get("best_for", []),
            scenarios=front_matter.get("scenarios", []),
            estimated_time=front_matter.get("estimated_time", ""),
        )

        self._skills[name] = skill
        self._imported_skills.add(name)

        self._persist_imported_skill(content, name, filename)

        return skill

    def import_skill_from_dict(self, data: dict) -> Skill:
        """从字典格式导入技能（适用于 JSON API）

        Args:
            data: 包含技能字段的字典

        Returns:
            导入的 Skill 对象

        Raises:
            ValueError: 技能名已存在或必填字段缺失
        """
        name = data.get("name", "").strip()
        if not name:
            raise ValueError("技能名称 (name) 不能为空")

        if name in self._skills:
            raise ValueError(f"技能 '{name}' 已存在")

        skill = Skill(
            name=name,
            description=data.get("description", ""),
            system_prompt=data.get("system_prompt", ""),
            tools=data.get("tools", []),
            steps=data.get("steps", []),
            output_format=data.get("output_format", ""),
            intent=data.get("intent", ""),
            skill_type=data.get("type", "component"),
            best_for=data.get("best_for", []),
            scenarios=data.get("scenarios", []),
            estimated_time=data.get("estimated_time", ""),
        )

        self._skills[name] = skill
        self._imported_skills.add(name)

        content = self._skill_to_skilly(skill)
        self._persist_imported_skill(content, name)

        return skill

    def delete_skill(self, name: str) -> bool:
        """删除已导入的技能

        Args:
            name: 技能名称

        Returns:
            是否成功删除
        """
        if name not in self._imported_skills:
            return False

        self._skills.pop(name, None)
        self._imported_skills.discard(name)

        skill_file = self._user_skills_dir / f"{name}.md"
        if skill_file.exists():
            skill_file.unlink()

        return True

    def is_imported(self, name: str) -> bool:
        """检查技能是否为用户导入的"""
        return name in self._imported_skills

    def _persist_imported_skill(self, content: str, name: str, filename: str = "") -> None:
        """将导入的技能持久化到 user-skills 目录"""
        self._user_skills_dir.mkdir(parents=True, exist_ok=True)

        if filename and not filename.endswith(".md"):
            filename = f"{filename}.md"
        if not filename:
            filename = f"{name}.md"

        skill_file = self._user_skills_dir / filename
        skill_file.write_text(content, encoding="utf-8")

    def _skill_to_skilly(self, skill: Skill) -> str:
        """将 Skill 对象转换为 SKILL.md 格式内容"""
        lines = ["---"]
        lines.append(f"name: {skill.name}")
        lines.append(f"description: {skill.description}")
        if skill.intent:
            lines.append(f"intent: {skill.intent}")
        if skill.skill_type:
            lines.append(f"type: {skill.skill_type}")
        if skill.best_for:
            lines.append(f"best_for:")
            for item in skill.best_for:
                lines.append(f"  - {item}")
        if skill.scenarios:
            lines.append(f"scenarios:")
            for item in skill.scenarios:
                lines.append(f"  - {item}")
        if skill.estimated_time:
            lines.append(f"estimated_time: {skill.estimated_time}")
        lines.append("---")
        lines.append("")
        if skill.system_prompt:
            lines.append(skill.system_prompt)
        return "\n".join(lines)

    def _load_all(self) -> None:
        """加载技能目录下的所有技能定义"""
        if not self.skills_dir.exists():
            logger.warning(f"Skills directory not found: {self.skills_dir}")
            return

        # 加载项目原生格式（YAML）
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

        # 加载 PM Skills 格式（子目录中的 SKILL.md）
        pm_skills_dir = self.skills_dir / "pm-skills"
        if pm_skills_dir.exists():
            self._load_pm_skills(pm_skills_dir)

        # 加载用户导入的技能
        self._load_user_skills()

    def _load_pm_skills(self, pm_skills_dir: Path) -> None:
        """加载 Product-Manager-Skills 格式的技能"""
        for skill_dir in pm_skills_dir.iterdir():
            if not skill_dir.is_dir():
                continue

            skill_file = skill_dir / "SKILL.md"
            if not skill_file.exists():
                continue

            try:
                skill = self._load_pm_skill(skill_file)
                if skill:
                    self._skills[skill.name] = skill
            except Exception as e:
                logger.error(f"Failed to load PM skill from {skill_file}: {e}")

    def _load_user_skills(self) -> None:
        """加载用户导入的技能"""
        if not self._user_skills_dir.exists():
            return

        for file_path in sorted(self._user_skills_dir.glob("*.md")):
            try:
                content = file_path.read_text(encoding="utf-8")
                front_matter = self._parse_front_matter(content)
                if not front_matter:
                    continue

                name = front_matter.get("name", file_path.stem)
                if name in self._skills:
                    continue

                markdown_content = self._extract_markdown_content(content)
                system_prompt = self._build_pm_skill_prompt(front_matter, markdown_content)
                steps = self._extract_pm_skill_steps(markdown_content)

                skill = Skill(
                    name=name,
                    description=front_matter.get("description", ""),
                    system_prompt=system_prompt,
                    tools=[],
                    steps=steps,
                    output_format="",
                    intent=front_matter.get("intent", ""),
                    skill_type=front_matter.get("type", "component"),
                    best_for=front_matter.get("best_for", []),
                    scenarios=front_matter.get("scenarios", []),
                    estimated_time=front_matter.get("estimated_time", ""),
                )
                self._skills[name] = skill
                self._imported_skills.add(name)
            except Exception as e:
                logger.error(f"Failed to load user skill from {file_path}: {e}")

    def _load_pm_skill(self, file_path: Path) -> Skill | None:
        """加载单个 PM Skill"""
        content = file_path.read_text(encoding="utf-8")

        # 解析 YAML front matter
        front_matter = self._parse_front_matter(content)
        if not front_matter:
            return None

        # 提取 Markdown 内容（去掉 front matter）
        markdown_content = self._extract_markdown_content(content)

        # 构建系统提示词
        system_prompt = self._build_pm_skill_prompt(front_matter, markdown_content)

        # 提取步骤
        steps = self._extract_pm_skill_steps(markdown_content)

        return Skill(
            name=front_matter.get("name", file_path.parent.name),
            description=front_matter.get("description", ""),
            system_prompt=system_prompt,
            tools=[],
            steps=steps,
            output_format="",
            intent=front_matter.get("intent", ""),
            skill_type=front_matter.get("type", ""),
            best_for=front_matter.get("best_for", []),
            scenarios=front_matter.get("scenarios", []),
            estimated_time=front_matter.get("estimated_time", ""),
        )

    def _build_pm_skill_prompt(self, front_matter: dict, markdown_content: str) -> str:
        """构建 PM Skill 的系统提示词"""
        parts = []

        # 添加意图说明
        intent = front_matter.get("intent", "")
        if intent:
            parts.append(f"# {front_matter.get('name', '')}")
            parts.append(f"\n{intent}\n")

        # 添加最佳使用场景
        best_for = front_matter.get("best_for", [])
        if best_for:
            parts.append("## 最佳使用场景")
            for scenario in best_for:
                parts.append(f"- {scenario}")
            parts.append("")

        # 添加使用场景示例
        scenarios = front_matter.get("scenarios", [])
        if scenarios:
            parts.append("## 使用场景示例")
            for scenario in scenarios:
                parts.append(f"- {scenario}")
            parts.append("")

        # 添加完整的 Markdown 内容
        parts.append("## 详细说明")
        parts.append(markdown_content)

        return "\n".join(parts)

    def _extract_pm_skill_steps(self, markdown_content: str) -> list[str]:
        """从 PM Skill 的 Markdown 内容中提取步骤"""
        steps = []
        in_steps_section = False

        for line in markdown_content.split("\n"):
            # 检测步骤部分
            if re.match(r"^##\s+(Application|Steps|执行步骤)", line, re.IGNORECASE):
                in_steps_section = True
                continue

            if in_steps_section:
                # 遇到新的二级标题结束
                if line.strip().startswith("## "):
                    break

                # 匹配三级标题作为步骤
                step_match = re.match(r"^###\s+Step\s+\d+:\s+(.*)", line.strip())
                if step_match:
                    steps.append(step_match.group(1).strip())
                    continue

                # 匹配有序列表
                step_match = re.match(r"^\d+\.\s+(.*)", line.strip())
                if step_match:
                    steps.append(step_match.group(1))

        return steps

    @staticmethod
    def _extract_markdown_content(content: str) -> str:
        """提取 Markdown 内容（去掉 front matter）"""
        # 去掉 YAML front matter
        match = re.match(r"^---\s*\n.*?\n---\s*\n", content, re.DOTALL)
        if match:
            return content[match.end():]
        return content

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

    def list_pm_skills(self) -> list[dict[str, str]]:
        """列出所有 PM Skills

        Returns:
            PM Skills 信息列表
        """
        return [
            {
                "name": skill.name,
                "description": skill.description,
                "type": skill.skill_type,
                "best_for": ", ".join(skill.best_for[:3]) if skill.best_for else "",
            }
            for skill in self._skills.values()
            if skill.skill_type
        ]

    def get_skill_summary(self, skill_name: str) -> str | None:
        """获取技能摘要（名称和描述）"""
        skill = self._skills.get(skill_name)
        if not skill:
            return None
        return f"- **{skill.name}**: {skill.description}"
