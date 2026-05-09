# -*- coding: utf-8 -*-
"""
SkillRouter 单元测试

测试路由逻辑（mock LLM）。
"""

import pytest

from src.skills.definition import SkillDefinition
from src.skills.manager import SkillManager
from src.skills.router import SkillRouter, SkillRouteResult


class MockLLMClient:
    """Mock LLM 客户端"""

    def __init__(self, response: dict):
        self._response = response
        self.last_messages = None
        self.last_functions = None

    async def chat_with_functions(self, messages, functions, **kwargs):
        self.last_messages = messages
        self.last_functions = functions
        return self._response


class MockLLMClientError:
    """模拟 LLM 调用失败"""

    async def chat_with_functions(self, messages, functions, **kwargs):
        raise ConnectionError("LLM 服务不可用")


@pytest.fixture
def skill_manager():
    """创建包含测试 Skill 的 Manager"""
    manager = SkillManager()
    manager.register(SkillDefinition(
        id="safe_training_plan",
        name="安全训练计划",
        description="制定安全训练计划",
        triggers=["训练计划", "练什么"],
    ))
    manager.register(SkillDefinition(
        id="nutrition_planning",
        name="营养规划",
        description="制定营养方案",
        triggers=["吃什么", "饮食"],
    ))
    return manager


@pytest.fixture
def user_profile():
    """测试用户档案"""
    return {
        "name": "测试用户",
        "fitness_goal": "增肌",
        "experience_level": "intermediate",
        "health_conditions": "",
    }


@pytest.fixture
def messages():
    """测试消息"""
    return [{"role": "user", "content": "帮我制定一个胸肌训练计划"}]


class TestSkillRouterRoute:
    """测试路由逻辑"""

    @pytest.mark.asyncio
    async def test_route_selects_skill(self, skill_manager, user_profile, messages):
        """LLM 选择 Skill 时返回正确结果"""
        mock_response = {
            "function_call": {
                "name": "select_skill",
                "arguments": '{"skill_id": "safe_training_plan", "reason": "用户要训练计划"}',
            }
        }
        client = MockLLMClient(mock_response)
        router = SkillRouter(llm_client=client)

        result = await router.route(messages, user_profile, skill_manager)

        assert not result.is_direct_reply
        assert result.skill_id == "safe_training_plan"
        assert result.reason == "用户要训练计划"

    @pytest.mark.asyncio
    async def test_route_direct_reply(self, skill_manager, user_profile):
        """LLM 直接回复时返回 direct_reply"""
        mock_response = {
            "function_call": {
                "name": "select_skill",
                "arguments": '{"direct_reply": "你好！有什么可以帮你的？"}',
            }
        }
        client = MockLLMClient(mock_response)
        router = SkillRouter(llm_client=client)

        messages = [{"role": "user", "content": "你好"}]
        result = await router.route(messages, user_profile, skill_manager)

        assert result.is_direct_reply
        assert "你好" in result.direct_reply

    @pytest.mark.asyncio
    async def test_route_tool_calls_format(self, skill_manager, user_profile, messages):
        """兼容 tool_calls 格式的响应"""
        mock_response = {
            "tool_calls": [
                {
                    "function": {
                        "name": "select_skill",
                        "arguments": '{"skill_id": "nutrition_planning", "reason": "营养相关"}',
                    }
                }
            ]
        }
        client = MockLLMClient(mock_response)
        router = SkillRouter(llm_client=client)

        result = await router.route(messages, user_profile, skill_manager)

        assert not result.is_direct_reply
        assert result.skill_id == "nutrition_planning"

    @pytest.mark.asyncio
    async def test_route_no_function_call(self, skill_manager, user_profile, messages):
        """没有 function call 时视为直接回复"""
        mock_response = {"content": "这是一个直接回答"}
        client = MockLLMClient(mock_response)
        router = SkillRouter(llm_client=client)

        result = await router.route(messages, user_profile, skill_manager)

        assert result.is_direct_reply
        assert result.direct_reply == "这是一个直接回答"

    @pytest.mark.asyncio
    async def test_route_invalid_skill_id(self, skill_manager, user_profile, messages):
        """LLM 返回无效 skill_id 时降级为直接回复"""
        mock_response = {
            "function_call": {
                "name": "select_skill",
                "arguments": '{"skill_id": "nonexistent_skill", "reason": "test"}',
            }
        }
        client = MockLLMClient(mock_response)
        router = SkillRouter(llm_client=client)

        result = await router.route(messages, user_profile, skill_manager)

        assert result.is_direct_reply

    @pytest.mark.asyncio
    async def test_route_llm_error(self, skill_manager, user_profile, messages):
        """LLM 调用失败时返回错误提示"""
        client = MockLLMClientError()
        router = SkillRouter(llm_client=client)

        result = await router.route(messages, user_profile, skill_manager)

        assert result.is_direct_reply
        assert "暂时无法" in result.direct_reply

    @pytest.mark.asyncio
    async def test_route_no_client(self, skill_manager, user_profile, messages):
        """未配置 LLM 客户端时返回错误"""
        router = SkillRouter(llm_client=None)

        result = await router.route(messages, user_profile, skill_manager)

        assert result.is_direct_reply
        assert "暂时无法" in result.direct_reply

    @pytest.mark.asyncio
    async def test_route_passes_messages_to_llm(self, skill_manager, user_profile, messages):
        """验证消息正确传递给 LLM"""
        mock_response = {
            "function_call": {
                "name": "select_skill",
                "arguments": '{"skill_id": "safe_training_plan", "reason": "test"}',
            }
        }
        client = MockLLMClient(mock_response)
        router = SkillRouter(llm_client=client)

        await router.route(messages, user_profile, skill_manager)

        # 验证 system prompt 在第一条
        assert client.last_messages[0]["role"] == "system"
        assert "玉珍健身" in client.last_messages[0]["content"]
        # 验证用户消息被传递
        assert client.last_messages[-1]["content"] == "帮我制定一个胸肌训练计划"

    @pytest.mark.asyncio
    async def test_route_includes_user_profile_in_prompt(
        self, skill_manager, user_profile, messages
    ):
        """验证用户档案包含在 system prompt 中"""
        mock_response = {
            "function_call": {
                "name": "select_skill",
                "arguments": '{"skill_id": "safe_training_plan", "reason": "test"}',
            }
        }
        client = MockLLMClient(mock_response)
        router = SkillRouter(llm_client=client)

        await router.route(messages, user_profile, skill_manager)

        system_content = client.last_messages[0]["content"]
        assert "增肌" in system_content
        assert "测试用户" in system_content
