"""技能加载器测试"""

import os
import tempfile
from pathlib import Path

import pytest
import yaml

from pm_workstation.skills.loader import Skill, SkillLoader


class TestSkill:
    """Skill 模型测试"""

    def test_create_skill(self):
        """测试创建技能"""
        skill = Skill(
            name="test-skill",
            description="测试技能",
            system_prompt="你是测试专家",
            tools=["read_file", "write_file"],
            steps=["步骤 1", "步骤 2"],
        )

        assert skill.name == "test-skill"
        assert len(skill.tools) == 2
        assert len(skill.steps) == 2

    def test_get_full_prompt_with_steps(self):
        """测试获取完整提示（包含步骤）"""
        skill = Skill(
            name="test",
            description="测试",
            system_prompt="系统提示",
            steps=["第一步", "第二步"],
        )

        prompt = skill.get_full_prompt()
        assert "系统提示" in prompt
        assert "执行步骤" in prompt
        assert "第一步" in prompt
        assert "第二步" in prompt

    def test_get_full_prompt_with_output_format(self):
        """测试获取完整提示（包含输出格式）"""
        skill = Skill(
            name="test",
            description="测试",
            system_prompt="系统提示",
            output_format="```json\n{}\n```",
        )

        prompt = skill.get_full_prompt()
        assert "输出格式" in prompt
        assert "```json" in prompt

    def test_get_full_prompt_empty(self):
        """测试空技能提示"""
        skill = Skill(
            name="test",
            description="测试",
            system_prompt="系统提示",
        )

        prompt = skill.get_full_prompt()
        assert prompt == "系统提示"


class TestSkillLoader:
    """SkillLoader 测试"""

    def _create_temp_skill_dir(self, skills: dict) -> str:
        """创建临时技能目录"""
        tmpdir = tempfile.mkdtemp()
        for name, data in skills.items():
            file_path = Path(tmpdir) / f"{name}.yaml"
            with open(file_path, "w", encoding="utf-8") as f:
                yaml.dump(data, f)
        return tmpdir

    def test_load_from_yaml(self):
        """测试从 YAML 加载"""
        skills_data = {
            "test-skill": {
                "name": "test-skill",
                "description": "测试技能",
                "system_prompt": "系统提示",
                "tools": ["read_file"],
                "steps": ["步骤 1"],
            }
        }

        tmpdir = self._create_temp_skill_dir(skills_data)
        try:
            loader = SkillLoader(skills_dir=tmpdir)
            skill = loader.load("test-skill")

            assert skill is not None
            assert skill.name == "test-skill"
            assert skill.description == "测试技能"
            assert "read_file" in skill.tools
        finally:
            for f in Path(tmpdir).glob("*.yaml"):
                f.unlink()
            Path(tmpdir).rmdir()

    def test_load_nonexistent_returns_none(self):
        """测试加载不存在的技能返回 None"""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = SkillLoader(skills_dir=tmpdir)
            skill = loader.load("nonexistent")
            assert skill is None

    def test_load_multiple(self):
        """测试批量加载"""
        skills_data = {
            "skill-a": {
                "name": "skill-a",
                "description": "技能 A",
                "system_prompt": "A",
            },
            "skill-b": {
                "name": "skill-b",
                "description": "技能 B",
                "system_prompt": "B",
            },
            "skill-c": {
                "name": "skill-c",
                "description": "技能 C",
                "system_prompt": "C",
            },
        }

        tmpdir = self._create_temp_skill_dir(skills_data)
        try:
            loader = SkillLoader(skills_dir=tmpdir)
            skills = loader.load_multiple(["skill-a", "skill-c", "nonexistent"])

            assert len(skills) == 2
            assert skills[0].name == "skill-a"
            assert skills[1].name == "skill-c"
        finally:
            for f in Path(tmpdir).glob("*.yaml"):
                f.unlink()
            Path(tmpdir).rmdir()

    def test_list_available(self):
        """测试列出可用技能"""
        skills_data = {
            "skill-a": {"name": "skill-a", "description": "A", "system_prompt": "A"},
            "skill-b": {"name": "skill-b", "description": "B", "system_prompt": "B"},
        }

        tmpdir = self._create_temp_skill_dir(skills_data)
        try:
            loader = SkillLoader(skills_dir=tmpdir)
            available = loader.list_available()

            assert "skill-a" in available
            assert "skill-b" in available
        finally:
            for f in Path(tmpdir).glob("*.yaml"):
                f.unlink()
            Path(tmpdir).rmdir()

    def test_load_from_nonexistent_directory(self):
        """测试从不存在的目录加载"""
        loader = SkillLoader(skills_dir="/nonexistent/path")
        assert loader.list_available() == []

    def test_get_skill_summary(self):
        """测试获取技能摘要"""
        skills_data = {
            "test-skill": {
                "name": "test-skill",
                "description": "测试描述",
                "system_prompt": "提示",
            }
        }

        tmpdir = self._create_temp_skill_dir(skills_data)
        try:
            loader = SkillLoader(skills_dir=tmpdir)
            summary = loader.get_skill_summary("test-skill")

            assert summary is not None
            assert "test-skill" in summary
            assert "测试描述" in summary
        finally:
            for f in Path(tmpdir).glob("*.yaml"):
                f.unlink()
            Path(tmpdir).rmdir()

    def test_get_skill_summary_nonexistent(self):
        """测试获取不存在技能摘要"""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = SkillLoader(skills_dir=tmpdir)
            summary = loader.get_skill_summary("nonexistent")
            assert summary is None

    def test_load_from_project_skills(self):
        """测试从项目技能目录加载"""
        skills_dir = Path(__file__).parent.parent.parent / "src" / "pm_workstation" / "skills"
        if skills_dir.exists():
            loader = SkillLoader(skills_dir=str(skills_dir))
            available = loader.list_available()

            # 验证加载了预期的技能
            expected_skills = [
                "requirement-analysis",
                "prd-generation",
                "prototype-generation",
                "document-review",
                "consistency-check",
            ]
            for expected in expected_skills:
                assert expected in available, f"Expected skill '{expected}' not found"

    def test_load_yaml_with_steps(self):
        """测试加载包含步骤的 YAML"""
        skills_data = {
            "test-skill": {
                "name": "test-skill",
                "description": "测试",
                "system_prompt": "提示",
                "steps": ["第一步", "第二步", "第三步"],
                "output_format": "JSON",
            }
        }

        tmpdir = self._create_temp_skill_dir(skills_data)
        try:
            loader = SkillLoader(skills_dir=tmpdir)
            skill = loader.load("test-skill")

            assert skill is not None
            assert len(skill.steps) == 3
            assert skill.output_format == "JSON"
        finally:
            for f in Path(tmpdir).glob("*.yaml"):
                f.unlink()
            Path(tmpdir).rmdir()
