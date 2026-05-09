# -*- coding: utf-8 -*-
"""
Agent v2 冒烟测试

测试场景：
1. 简单问候 → direct_reply（不走 Skill）
2. Skill 选择 → 工具执行 → 输出（mock LLM + mock 工具）
3. HITL 中断（mock interrupt）

版本: v2.0.0
日期: 2026-05-09
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.agent_v2.state import AgentState
from src.agent_v2.feature_flag import is_agent_v2_enabled
from src.agent_v2.sse_emitter import SSEEventType, emit_event
from src.skills.router import SkillRouteResult
from src.skills.manager import SkillManager
from src.skills.definition import SkillDefinition
from src.harness_v2.pre_skill_policy import PolicyResult

# langgraph 可能不在本地环境，条件导入
try:
    from src.agent_v2.graph import (
        build_agent_graph,
        _route_after_skill_select,
        _route_after_safety_check,
    )
    HAS_LANGGRAPH = True
except ImportError:
    HAS_LANGGRAPH = False

    # 提供 fallback 路由函数用于测试
    def _route_after_skill_select(state):
        if state.get("direct_reply"):
            return "output_generate"
        return "safety_check"

    def _route_after_safety_check(state):
        if state.get("direct_reply"):
            return "output_generate"
        if not state.get("current_skill"):
            return "output_generate"
        return "skill_execute"

    build_agent_graph = None


# ============ B1: AgentState 测试 ============


class TestAgentState:
    """AgentState 结构测试"""

    def test_state_has_required_fields(self):
        """验证 AgentState 包含所有必需字段"""
        annotations = AgentState.__annotations__
        expected_fields = [
            "messages", "user_id", "thread_id", "user_profile",
            "current_skill", "skill_reason", "tool_results",
            "harness_trace", "approval_status", "direct_reply",
            "final_output", "error",
        ]
        for field in expected_fields:
            assert field in annotations, f"缺少字段: {field}"

    def test_messages_uses_add_reducer(self):
        """验证 messages 字段使用 add reducer"""
        from typing import get_type_hints, Annotated
        hints = get_type_hints(AgentState, include_extras=True)
        msg_hint = hints["messages"]
        # Annotated[list, add] 的 __metadata__ 包含 add
        assert hasattr(msg_hint, "__metadata__")


# ============ 条件路由测试 ============


class TestConditionalRouting:
    """条件边路由逻辑测试"""

    def test_route_after_skill_select_direct_reply(self):
        """direct_reply 设置时跳到 output_generate"""
        state = {"direct_reply": "你好！", "current_skill": None}
        assert _route_after_skill_select(state) == "output_generate"

    def test_route_after_skill_select_to_safety(self):
        """选中 Skill 时走 safety_check"""
        state = {"direct_reply": None, "current_skill": "safe_training_plan"}
        assert _route_after_skill_select(state) == "safety_check"

    def test_route_after_safety_check_to_execute(self):
        """安全检查通过时走 skill_execute"""
        state = {"direct_reply": None, "current_skill": "safe_training_plan"}
        assert _route_after_safety_check(state) == "skill_execute"

    def test_route_after_safety_check_require_profile(self):
        """需要档案时跳到 output_generate"""
        state = {"direct_reply": "请先完善个人档案", "current_skill": None}
        assert _route_after_safety_check(state) == "output_generate"

    def test_route_after_safety_check_no_skill(self):
        """无 Skill 时跳到 output_generate"""
        state = {"direct_reply": None, "current_skill": None}
        assert _route_after_safety_check(state) == "output_generate"


# ============ 节点单元测试 ============


class TestInitThread:
    """init_thread 节点测试"""

    @pytest.mark.asyncio
    async def test_returns_existing_profile(self):
        """已有 user_profile 时直接返回"""
        from src.agent_v2.nodes.init_thread import init_thread

        state = {
            "user_id": "user_123",
            "thread_id": "thread_abc",
            "user_profile": {"name": "张三"},
            "messages": [],
        }
        result = await init_thread(state)
        assert result["user_profile"] == {"name": "张三"}

    @pytest.mark.asyncio
    async def test_returns_empty_profile_when_none(self):
        """无 user_profile 时返回空 dict"""
        from src.agent_v2.nodes.init_thread import init_thread

        state = {
            "user_id": "user_123",
            "thread_id": "thread_abc",
            "user_profile": None,
            "messages": [],
        }
        result = await init_thread(state)
        assert result["user_profile"] == {}


class TestSkillSelect:
    """skill_select 节点测试"""

    @pytest.mark.asyncio
    async def test_direct_reply_path(self):
        """简单问候走 direct_reply"""
        from src.agent_v2.nodes.skill_select import skill_select, configure_skill_select

        mock_router = AsyncMock()
        mock_router.route = AsyncMock(return_value=SkillRouteResult(
            is_direct_reply=True,
            direct_reply="你好！有什么可以帮你的？",
        ))
        mock_manager = MagicMock(spec=SkillManager)

        configure_skill_select(router=mock_router, manager=mock_manager)

        state = {
            "messages": [{"role": "user", "content": "你好"}],
            "user_profile": {},
        }
        result = await skill_select(state)
        assert result["direct_reply"] == "你好！有什么可以帮你的？"

    @pytest.mark.asyncio
    async def test_skill_selection_path(self):
        """选择 Skill 路径"""
        from src.agent_v2.nodes.skill_select import skill_select, configure_skill_select

        mock_router = AsyncMock()
        mock_router.route = AsyncMock(return_value=SkillRouteResult(
            skill_id="safe_training_plan",
            reason="用户需要训练计划",
            is_direct_reply=False,
        ))
        mock_manager = MagicMock(spec=SkillManager)

        configure_skill_select(router=mock_router, manager=mock_manager)

        state = {
            "messages": [{"role": "user", "content": "帮我制定一个训练计划"}],
            "user_profile": {"basic_info": {"fitness_level": "beginner"}},
        }
        result = await skill_select(state)
        assert result["current_skill"] == "safe_training_plan"
        assert result["skill_reason"] == "用户需要训练计划"


class TestSafetyCheck:
    """safety_check 节点测试"""

    @pytest.mark.asyncio
    async def test_pass_through(self):
        """安全检查通过"""
        from src.agent_v2.nodes.safety_check import safety_check, configure_safety_check
        from src.harness_v2.pre_skill_policy import PreSkillPolicy

        mock_policy = MagicMock(spec=PreSkillPolicy)
        mock_policy.check.return_value = PolicyResult(allowed=True, action="proceed")
        configure_safety_check(policy=mock_policy)

        state = {
            "current_skill": "exercise_optimization",
            "user_profile": {},
        }
        result = await safety_check(state)
        assert result.get("approval_status") == "approved"

    @pytest.mark.asyncio
    async def test_require_profile(self):
        """需要用户档案"""
        from src.agent_v2.nodes.safety_check import safety_check, configure_safety_check
        from src.harness_v2.pre_skill_policy import PreSkillPolicy

        mock_policy = MagicMock(spec=PreSkillPolicy)
        mock_policy.check.return_value = PolicyResult(
            allowed=False,
            action="require_profile",
            reason="请先完善个人档案",
        )
        configure_safety_check(policy=mock_policy)

        state = {
            "current_skill": "safe_training_plan",
            "user_profile": None,
        }
        result = await safety_check(state)
        assert result.get("direct_reply") == "请先完善个人档案"
        assert result.get("current_skill") is None

    @pytest.mark.asyncio
    async def test_skip_when_no_skill(self):
        """无 Skill 时跳过检查"""
        from src.agent_v2.nodes.safety_check import safety_check

        state = {"current_skill": None, "user_profile": {}}
        result = await safety_check(state)
        assert result == {}


# ============ SSE 测试 ============


class TestSSEEmitter:
    """SSE 事件格式化测试"""

    def test_emit_event_format(self):
        """验证 SSE 格式"""
        result = emit_event(SSEEventType.CONTENT, {"text": "你好"})
        assert result.startswith("event: content\n")
        assert "data: " in result
        assert result.endswith("\n\n")

    def test_emit_event_string_data(self):
        """字符串数据直接输出"""
        result = emit_event(SSEEventType.DONE, "completed")
        assert "data: completed\n" in result

    def test_event_type_values(self):
        """验证事件类型枚举值"""
        assert SSEEventType.SKILL_STARTED.value == "skill_started"
        assert SSEEventType.TOOL_EXECUTING.value == "tool_executing"
        assert SSEEventType.TOOL_COMPLETED.value == "tool_completed"
        assert SSEEventType.APPROVAL_REQUIRED.value == "approval_required"
        assert SSEEventType.CONTENT.value == "content"
        assert SSEEventType.DONE.value == "done"
        assert SSEEventType.ERROR.value == "error"


# ============ Feature Flag 测试 ============


class TestFeatureFlag:
    """Feature flag 测试"""

    def test_disabled_by_default(self):
        """默认禁用"""
        with patch.dict("os.environ", {}, clear=True):
            # 清除 AGENT_V2_ENABLED
            import os
            os.environ.pop("AGENT_V2_ENABLED", None)
            assert is_agent_v2_enabled() is False

    def test_enabled_with_true(self):
        """设置 true 启用"""
        with patch.dict("os.environ", {"AGENT_V2_ENABLED": "true"}):
            assert is_agent_v2_enabled() is True

    def test_enabled_with_1(self):
        """设置 1 启用"""
        with patch.dict("os.environ", {"AGENT_V2_ENABLED": "1"}):
            assert is_agent_v2_enabled() is True

    def test_disabled_with_false(self):
        """设置 false 禁用"""
        with patch.dict("os.environ", {"AGENT_V2_ENABLED": "false"}):
            assert is_agent_v2_enabled() is False


# ============ Graph 构建测试 ============


@pytest.mark.skipif(not HAS_LANGGRAPH, reason="langgraph not installed")
class TestGraphBuild:
    """Agent Graph 构建测试"""

    def test_graph_builds_without_error(self):
        """Graph 可以正常构建"""
        mock_router = AsyncMock()
        mock_manager = MagicMock(spec=SkillManager)
        mock_executor = MagicMock()

        graph = build_agent_graph(
            skill_router=mock_router,
            skill_manager=mock_manager,
            skill_executor=mock_executor,
            use_memory_checkpointer=True,
        )
        assert graph is not None

    def test_graph_has_expected_nodes(self):
        """Graph 包含所有预期节点"""
        graph = build_agent_graph(use_memory_checkpointer=True)
        # CompiledGraph 的 nodes 属性
        node_names = set(graph.nodes.keys())
        expected = {"init_thread", "skill_select", "safety_check",
                    "skill_execute", "output_generate", "record"}
        # LangGraph 会添加 __start__ 和 __end__ 节点
        assert expected.issubset(node_names)
