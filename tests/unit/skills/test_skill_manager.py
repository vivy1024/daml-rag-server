# -*- coding: utf-8 -*-
"""
SkillManager 单元测试

测试注册、列表、选择 prompt 生成、function schema 生成。
"""

import os

import pytest

from src.skills.definition import SkillDefinition
from src.skills.manager import SkillManager, SkillNotFoundError


@pytest.fixture
def skill_manager():
    """创建空的 SkillManager"""
    return SkillManager()


@pytest.fixture
def sample_skill():
    """创建示例 Skill"""
    return SkillDefinition(
        id="test_skill",
        name="测试技能",
        description="用于测试的技能描述",
        triggers=["触发条件1", "触发条件2"],
        required_tools=["get_user_profile", "tdee_calculator"],
        optional_tools=["contraindications_checker"],
        safety_preconditions={"user_has_profile": True},
        output_standard="输出标准",
        example_output="示例输出",
        degradation="降级策略",
        harness_checkpoints={"pre_execution": "check"},
    )


@pytest.fixture
def populated_manager(skill_manager, sample_skill):
    """创建已注册 Skill 的 Manager"""
    skill_manager.register(sample_skill)
    skill_manager.register(
        SkillDefinition(
            id="another_skill",
            name="另一个技能",
            description="另一个描述",
            triggers=["另一个触发"],
            required_tools=["intelligent_exercise_selector"],
        )
    )
    return skill_manager


class TestSkillManagerRegister:
    """测试 Skill 注册"""

    def test_register_skill(self, skill_manager, sample_skill):
        """注册 Skill 成功"""
        skill_manager.register(sample_skill)
        assert skill_manager.skill_count == 1

    def test_register_duplicate_overwrites(self, skill_manager, sample_skill):
        """重复注册覆盖旧 Skill"""
        skill_manager.register(sample_skill)
        updated = SkillDefinition(
            id="test_skill",
            name="更新后的技能",
            description="更新后的描述",
        )
        skill_manager.register(updated)
        assert skill_manager.skill_count == 1
        assert skill_manager.get("test_skill").name == "更新后的技能"


class TestSkillManagerGet:
    """测试 Skill 获取"""

    def test_get_existing_skill(self, populated_manager):
        """获取已注册的 Skill"""
        skill = populated_manager.get("test_skill")
        assert skill.id == "test_skill"
        assert skill.name == "测试技能"

    def test_get_nonexistent_skill(self, populated_manager):
        """获取不存在的 Skill 抛出异常"""
        with pytest.raises(SkillNotFoundError, match="Skill 不存在"):
            populated_manager.get("nonexistent")


class TestSkillManagerList:
    """测试 Skill 列表"""

    def test_list_empty(self, skill_manager):
        """空 Manager 返回空列表"""
        assert skill_manager.list_skills() == []

    def test_list_skills(self, populated_manager):
        """列出所有已注册 Skill"""
        skills = populated_manager.list_skills()
        assert len(skills) == 2
        ids = {s.id for s in skills}
        assert ids == {"test_skill", "another_skill"}


class TestSkillManagerLoadAll:
    """测试从目录加载"""

    def test_load_all_from_definitions(self):
        """从真实 definitions 目录加载"""
        definitions_dir = os.path.join(
            os.path.dirname(__file__),
            "..", "..", "..", "src", "skills", "definitions"
        )
        definitions_dir = os.path.abspath(definitions_dir)

        if not os.path.exists(definitions_dir):
            pytest.skip("definitions 目录不存在")

        manager = SkillManager()
        count = manager.load_all(definitions_dir)
        assert count == 10
        assert manager.skill_count == 10


class TestSkillManagerPrompt:
    """测试 prompt 和 schema 生成"""

    def test_get_selection_prompt(self, populated_manager):
        """生成选择 prompt"""
        prompt = populated_manager.get_selection_prompt()

        assert "玉珍健身 AI 教练" in prompt
        assert "test_skill" in prompt
        assert "测试技能" in prompt
        assert "another_skill" in prompt
        assert "触发条件1" in prompt

    def test_get_selection_prompt_empty(self, skill_manager):
        """空 Manager 也能生成 prompt"""
        prompt = skill_manager.get_selection_prompt()
        assert "可用 Skill 列表" in prompt

    def test_get_function_schema(self, populated_manager):
        """生成 function calling schema"""
        schema = populated_manager.get_function_schema()

        assert schema["type"] == "function"
        assert schema["function"]["name"] == "select_skill"

        params = schema["function"]["parameters"]
        assert "skill_id" in params["properties"]
        assert "reason" in params["properties"]
        assert "direct_reply" in params["properties"]

        # skill_id 的 enum 应包含所有已注册 Skill
        enum_values = params["properties"]["skill_id"]["enum"]
        assert "test_skill" in enum_values
        assert "another_skill" in enum_values

    def test_get_function_schema_empty(self, skill_manager):
        """空 Manager 生成的 schema 中 enum 为空列表"""
        schema = skill_manager.get_function_schema()
        enum_values = schema["function"]["parameters"]["properties"]["skill_id"]["enum"]
        assert enum_values == []
