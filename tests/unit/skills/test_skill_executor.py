# -*- coding: utf-8 -*-
"""
SkillExecutor 单元测试

测试工具链执行（mock 工具）。
"""

import pytest

from src.skills.definition import SkillDefinition
from src.skills.executor import SkillExecutor, ExecutionResult, ToolResult


class MockToolRegistry:
    """Mock 工具注册表"""

    def __init__(self, results: dict = None, errors: dict = None):
        """
        Args:
            results: {tool_name: return_value}
            errors: {tool_name: exception}
        """
        self._results = results or {}
        self._errors = errors or {}
        self.call_log = []

    async def call_tool(self, tool_name: str, params: dict):
        self.call_log.append((tool_name, params))
        if tool_name in self._errors:
            raise self._errors[tool_name]
        return self._results.get(tool_name, {"status": "ok"})


@pytest.fixture
def simple_skill():
    """简单的测试 Skill"""
    return SkillDefinition(
        id="test_skill",
        name="测试技能",
        description="测试用",
        required_tools=["get_user_profile", "tdee_calculator"],
        optional_tools=[],
    )


@pytest.fixture
def skill_with_optional():
    """带可选工具的 Skill"""
    return SkillDefinition(
        id="optional_skill",
        name="可选工具技能",
        description="测试可选工具",
        required_tools=["get_user_profile", "intelligent_exercise_selector"],
        optional_tools=["movement_pattern_balancer"],
    )


@pytest.fixture
def state():
    """测试状态"""
    return {
        "user_profile": {
            "name": "测试用户",
            "fitness_goal": "增肌",
            "experience_level": "intermediate",
        },
        "messages": [{"role": "user", "content": "帮我制定计划"}],
    }


class TestSkillExecutorBasic:
    """测试基本执行逻辑"""

    @pytest.mark.asyncio
    async def test_execute_all_tools_success(self, simple_skill, state):
        """所有工具执行成功"""
        registry = MockToolRegistry(
            results={
                "get_user_profile": {"name": "测试用户"},
                "tdee_calculator": {"tdee": 2500},
            }
        )
        executor = SkillExecutor()

        result = await executor.execute(simple_skill, state, registry)

        assert result.success
        assert result.skill_id == "test_skill"
        assert len(result.tool_results) == 2
        assert result.tool_results["get_user_profile"].success
        assert result.tool_results["tdee_calculator"].success
        assert result.tool_results["tdee_calculator"].data == {"tdee": 2500}
        assert result.total_duration_ms > 0

    @pytest.mark.asyncio
    async def test_execute_tool_order(self, simple_skill, state):
        """工具按顺序执行"""
        registry = MockToolRegistry()
        executor = SkillExecutor()

        await executor.execute(simple_skill, state, registry)

        # 验证调用顺序
        tool_names = [name for name, _ in registry.call_log]
        assert tool_names == ["get_user_profile", "tdee_calculator"]

    @pytest.mark.asyncio
    async def test_execute_single_tool_failure(self, simple_skill, state):
        """单个工具失败不阻断整体"""
        registry = MockToolRegistry(
            results={"tdee_calculator": {"tdee": 2500}},
            errors={"get_user_profile": RuntimeError("连接超时")},
        )
        executor = SkillExecutor()

        result = await executor.execute(simple_skill, state, registry)

        # 整体仍然成功（因为不是所有 required 都失败）
        assert result.success
        assert not result.tool_results["get_user_profile"].success
        assert "连接超时" in result.tool_results["get_user_profile"].error
        assert result.tool_results["tdee_calculator"].success
        assert len(result.errors) == 1

    @pytest.mark.asyncio
    async def test_execute_all_tools_failure(self, simple_skill, state):
        """所有 required 工具失败标记整体失败"""
        registry = MockToolRegistry(
            errors={
                "get_user_profile": RuntimeError("失败1"),
                "tdee_calculator": RuntimeError("失败2"),
            }
        )
        executor = SkillExecutor()

        result = await executor.execute(simple_skill, state, registry)

        assert not result.success
        assert len(result.errors) == 2


class TestSkillExecutorParallel:
    """测试并行执行"""

    @pytest.mark.asyncio
    async def test_parallel_group_execution(self, state):
        """并行组内工具并行执行"""
        skill = SkillDefinition(
            id="parallel_skill",
            name="并行技能",
            description="测试并行",
            required_tools=["tool_a", "tool_b", "tool_c"],
        )
        registry = MockToolRegistry(
            results={
                "tool_a": {"a": 1},
                "tool_b": {"b": 2},
                "tool_c": {"c": 3},
            }
        )
        # 配置并行组：tool_a 和 tool_b 并行，tool_c 单独
        executor = SkillExecutor(
            parallel_groups={
                "parallel_skill": [["tool_a", "tool_b"], ["tool_c"]]
            }
        )

        result = await executor.execute(skill, state, registry)

        assert result.success
        assert len(result.tool_results) == 3
        assert all(r.success for r in result.tool_results.values())


class TestSkillExecutorOptionalTools:
    """测试可选工具执行"""

    @pytest.mark.asyncio
    async def test_optional_tool_runs_when_condition_met(
        self, skill_with_optional, state
    ):
        """满足条件时执行可选工具"""
        registry = MockToolRegistry(
            results={
                "get_user_profile": {"name": "用户"},
                "intelligent_exercise_selector": {
                    "exercises": [
                        {"name": "动作1"},
                        {"name": "动作2"},
                        {"name": "动作3"},
                        {"name": "动作4"},
                    ]
                },
                "movement_pattern_balancer": {"balanced": True},
            }
        )
        executor = SkillExecutor()

        result = await executor.execute(skill_with_optional, state, registry)

        # movement_pattern_balancer 应该被执行（exercises > 3）
        assert "movement_pattern_balancer" in result.tool_results

    @pytest.mark.asyncio
    async def test_optional_tool_skipped_when_condition_not_met(self, state):
        """不满足条件时跳过可选工具"""
        skill = SkillDefinition(
            id="skip_optional",
            name="跳过可选",
            description="测试",
            required_tools=["get_user_profile", "intelligent_exercise_selector"],
            optional_tools=["movement_pattern_balancer"],
        )
        registry = MockToolRegistry(
            results={
                "get_user_profile": {"name": "用户"},
                "intelligent_exercise_selector": {
                    "exercises": [{"name": "动作1"}, {"name": "动作2"}]
                },
            }
        )
        executor = SkillExecutor()

        result = await executor.execute(skill, state, registry)

        # exercises <= 3，不执行 movement_pattern_balancer
        assert "movement_pattern_balancer" not in result.tool_results


class TestSkillExecutorParams:
    """测试参数传递"""

    @pytest.mark.asyncio
    async def test_passes_user_profile(self, simple_skill, state):
        """传递用户档案给工具"""
        registry = MockToolRegistry()
        executor = SkillExecutor()

        await executor.execute(simple_skill, state, registry)

        # 第一个工具应收到 user_profile
        _, params = registry.call_log[0]
        assert "user_profile" in params
        assert params["user_profile"]["name"] == "测试用户"

    @pytest.mark.asyncio
    async def test_passes_previous_results(self, simple_skill, state):
        """后续工具收到前序工具结果"""
        registry = MockToolRegistry(
            results={
                "get_user_profile": {"name": "用户", "weight": 75},
                "tdee_calculator": {"tdee": 2500},
            }
        )
        executor = SkillExecutor()

        await executor.execute(simple_skill, state, registry)

        # 第二个工具应收到第一个工具的结果
        _, params = registry.call_log[1]
        assert "previous_results" in params
        assert "get_user_profile" in params["previous_results"]
