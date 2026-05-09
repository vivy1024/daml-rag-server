# -*- coding: utf-8 -*-
"""
Skill Loader 单元测试

测试 YAML 加载、字段验证、目录批量加载。
"""

import os
import tempfile
from pathlib import Path

import pytest
import yaml

from src.skills.definition import SkillDefinition
from src.skills.loader import SkillLoader, SkillLoadError


@pytest.fixture
def valid_skill_yaml(tmp_path):
    """创建有效的 Skill YAML 文件"""
    data = {
        "id": "test_skill",
        "name": "测试技能",
        "description": "用于测试的技能",
        "triggers": ["测试触发1", "测试触发2"],
        "required_tools": ["get_user_profile", "tdee_calculator"],
        "optional_tools": ["contraindications_checker"],
        "safety_preconditions": {"user_has_profile": True},
        "output_standard": "必须包含测试内容",
        "example_output": "## 测试输出",
        "degradation": "如果失败则降级",
        "harness_checkpoints": {"pre_execution": "check something"},
    }
    file_path = tmp_path / "test_skill.yaml"
    with open(file_path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True)
    return str(file_path)


@pytest.fixture
def minimal_skill_yaml(tmp_path):
    """创建仅含必填字段的 Skill YAML"""
    data = {
        "id": "minimal_skill",
        "name": "最小技能",
        "description": "仅含必填字段",
    }
    file_path = tmp_path / "minimal_skill.yaml"
    with open(file_path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True)
    return str(file_path)


@pytest.fixture
def invalid_skill_yaml_missing_field(tmp_path):
    """创建缺少必填字段的 YAML"""
    data = {
        "id": "broken_skill",
        "name": "缺少 description",
    }
    file_path = tmp_path / "broken.yaml"
    with open(file_path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True)
    return str(file_path)


@pytest.fixture
def skill_directory(tmp_path):
    """创建包含多个 Skill YAML 的目录"""
    skills = [
        {"id": "skill_a", "name": "技能A", "description": "描述A"},
        {"id": "skill_b", "name": "技能B", "description": "描述B"},
        {"id": "skill_c", "name": "技能C", "description": "描述C"},
    ]
    for skill in skills:
        file_path = tmp_path / f"{skill['id']}.yaml"
        with open(file_path, "w", encoding="utf-8") as f:
            yaml.dump(skill, f, allow_unicode=True)
    return str(tmp_path)


class TestSkillLoaderLoadFile:
    """测试单文件加载"""

    def test_load_valid_skill(self, valid_skill_yaml):
        """加载完整的 Skill YAML"""
        skill = SkillLoader.load_file(valid_skill_yaml)

        assert isinstance(skill, SkillDefinition)
        assert skill.id == "test_skill"
        assert skill.name == "测试技能"
        assert skill.description == "用于测试的技能"
        assert len(skill.triggers) == 2
        assert "get_user_profile" in skill.required_tools
        assert "contraindications_checker" in skill.optional_tools
        assert skill.safety_preconditions["user_has_profile"] is True
        assert skill.output_standard == "必须包含测试内容"
        assert skill.harness_checkpoints["pre_execution"] == "check something"

    def test_load_minimal_skill(self, minimal_skill_yaml):
        """加载仅含必填字段的 Skill"""
        skill = SkillLoader.load_file(minimal_skill_yaml)

        assert skill.id == "minimal_skill"
        assert skill.name == "最小技能"
        assert skill.triggers == []
        assert skill.required_tools == []
        assert skill.optional_tools == []

    def test_load_nonexistent_file(self):
        """加载不存在的文件应抛出异常"""
        with pytest.raises(SkillLoadError, match="文件不存在"):
            SkillLoader.load_file("/nonexistent/path.yaml")

    def test_load_invalid_extension(self, tmp_path):
        """加载非 YAML 扩展名文件应抛出异常"""
        file_path = tmp_path / "test.txt"
        file_path.write_text("content")
        with pytest.raises(SkillLoadError, match="不支持的文件格式"):
            SkillLoader.load_file(str(file_path))

    def test_load_missing_required_field(self, invalid_skill_yaml_missing_field):
        """缺少必填字段应抛出异常"""
        with pytest.raises(SkillLoadError, match="缺少必填字段"):
            SkillLoader.load_file(invalid_skill_yaml_missing_field)

    def test_load_invalid_yaml_content(self, tmp_path):
        """无效 YAML 内容应抛出异常"""
        file_path = tmp_path / "bad.yaml"
        file_path.write_text("[ invalid: yaml: content", encoding="utf-8")
        with pytest.raises(SkillLoadError, match="YAML 解析失败"):
            SkillLoader.load_file(str(file_path))

    def test_load_non_dict_yaml(self, tmp_path):
        """YAML 内容不是字典应抛出异常"""
        file_path = tmp_path / "list.yaml"
        file_path.write_text("- item1\n- item2\n", encoding="utf-8")
        with pytest.raises(SkillLoadError, match="必须是字典格式"):
            SkillLoader.load_file(str(file_path))


class TestSkillLoaderLoadDirectory:
    """测试目录批量加载"""

    def test_load_directory(self, skill_directory):
        """从目录加载多个 Skill"""
        skills = SkillLoader.load_directory(skill_directory)

        assert len(skills) == 3
        ids = {s.id for s in skills}
        assert ids == {"skill_a", "skill_b", "skill_c"}

    def test_load_nonexistent_directory(self):
        """加载不存在的目录应抛出异常"""
        with pytest.raises(SkillLoadError, match="目录不存在"):
            SkillLoader.load_directory("/nonexistent/dir")

    def test_load_empty_directory(self, tmp_path):
        """空目录返回空列表"""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        skills = SkillLoader.load_directory(str(empty_dir))
        assert skills == []

    def test_load_directory_skips_invalid(self, tmp_path):
        """目录中有无效文件时跳过并继续"""
        # 有效文件
        valid = {"id": "valid", "name": "有效", "description": "有效技能"}
        with open(tmp_path / "valid.yaml", "w", encoding="utf-8") as f:
            yaml.dump(valid, f, allow_unicode=True)
        # 无效文件（缺少字段）
        invalid = {"id": "invalid", "name": "无效"}
        with open(tmp_path / "invalid.yaml", "w", encoding="utf-8") as f:
            yaml.dump(invalid, f, allow_unicode=True)

        skills = SkillLoader.load_directory(str(tmp_path))
        assert len(skills) == 1
        assert skills[0].id == "valid"


class TestSkillLoaderRealDefinitions:
    """测试加载真实的 Skill 定义文件"""

    def test_load_real_definitions_directory(self):
        """加载 src/skills/definitions/ 目录下的真实 YAML"""
        definitions_dir = os.path.join(
            os.path.dirname(__file__),
            "..", "..", "..", "src", "skills", "definitions"
        )
        definitions_dir = os.path.abspath(definitions_dir)

        if not os.path.exists(definitions_dir):
            pytest.skip("definitions 目录不存在")

        skills = SkillLoader.load_directory(definitions_dir)
        assert len(skills) == 10

        # 验证所有 Skill 都有有效的 ID
        ids = {s.id for s in skills}
        expected_ids = {
            "safe_training_plan",
            "exercise_optimization",
            "nutrition_planning",
            "posture_correction",
            "progress_analysis",
            "rehabilitation_training",
            "fat_loss_program",
            "strength_program",
            "safety_assessment",
            "quick_consultation",
        }
        assert ids == expected_ids
