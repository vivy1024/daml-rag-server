# -*- coding: utf-8 -*-
"""
SkillRouter

基于 LLM function calling 的 Skill 路由器。
根据用户消息和档案，选择最合适的 Skill 或直接回复。
"""

import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol

from .manager import SkillManager

logger = logging.getLogger(__name__)


@dataclass
class SkillRouteResult:
    """Skill 路由结果

    Attributes:
        skill_id: 选中的 Skill ID（is_direct_reply=True 时为空）
        reason: 选择原因
        is_direct_reply: 是否为直接回复（不需要 Skill）
        direct_reply: 直接回复内容
    """

    skill_id: str = ""
    reason: str = ""
    is_direct_reply: bool = False
    direct_reply: str = ""


class LLMClientProtocol(Protocol):
    """LLM 客户端协议（用于类型提示）"""

    async def chat_with_functions(
        self,
        messages: List[Dict[str, str]],
        functions: List[dict],
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """带 function calling 的聊天接口"""
        ...


class SkillRouter:
    """Skill 路由器

    使用 LLM function calling 将用户意图路由到合适的 Skill。
    """

    def __init__(self, llm_client: Optional[LLMClientProtocol] = None) -> None:
        """初始化路由器

        Args:
            llm_client: LLM 客户端实例（需支持 chat_with_functions）
        """
        self._llm_client = llm_client

    async def route(
        self,
        messages: List[Dict[str, str]],
        user_profile: Dict[str, Any],
        skill_manager: SkillManager,
    ) -> SkillRouteResult:
        """路由用户消息到合适的 Skill

        Args:
            messages: 对话消息列表
            user_profile: 用户档案
            skill_manager: Skill 管理器实例

        Returns:
            SkillRouteResult 路由结果
        """
        if not self._llm_client:
            logger.error("LLM 客户端未配置，无法进行路由")
            return SkillRouteResult(
                is_direct_reply=True,
                direct_reply="系统暂时无法处理请求，请稍后再试。",
            )

        # 构建 function calling 请求
        system_prompt = self._build_system_prompt(skill_manager, user_profile)
        function_schema = skill_manager.get_function_schema()

        call_messages = [{"role": "system", "content": system_prompt}]
        call_messages.extend(messages)

        try:
            response = await self._llm_client.chat_with_functions(
                messages=call_messages,
                functions=[function_schema],
            )
            return self._parse_response(response, skill_manager)
        except Exception as e:
            logger.error(f"Skill 路由 LLM 调用失败: {e}")
            return SkillRouteResult(
                is_direct_reply=True,
                direct_reply="抱歉，我暂时无法理解你的需求，请换个方式描述。",
            )

    def _build_system_prompt(
        self,
        skill_manager: SkillManager,
        user_profile: Dict[str, Any],
    ) -> str:
        """构建路由系统 prompt

        Args:
            skill_manager: Skill 管理器
            user_profile: 用户档案

        Returns:
            系统 prompt 文本
        """
        selection_prompt = skill_manager.get_selection_prompt()

        profile_summary = self._summarize_profile(user_profile)

        return (
            f"{selection_prompt}\n"
            f"---\n"
            f"用户档案摘要：\n{profile_summary}\n"
            f"---\n"
            f"请调用 select_skill 函数选择 Skill，或使用 direct_reply 直接回答。"
        )

    def _summarize_profile(self, user_profile: Dict[str, Any]) -> str:
        """生成用户档案摘要

        Args:
            user_profile: 用户档案字典

        Returns:
            档案摘要文本
        """
        if not user_profile:
            return "用户暂无档案信息"

        parts = []
        if "name" in user_profile:
            parts.append(f"姓名: {user_profile['name']}")
        if "fitness_goal" in user_profile:
            parts.append(f"健身目标: {user_profile['fitness_goal']}")
        if "health_conditions" in user_profile:
            conditions = user_profile["health_conditions"]
            if conditions:
                parts.append(f"健康状况: {conditions}")
        if "experience_level" in user_profile:
            parts.append(f"训练经验: {user_profile['experience_level']}")
        if "available_equipment" in user_profile:
            parts.append(f"可用器械: {user_profile['available_equipment']}")

        return "\n".join(parts) if parts else "用户暂无详细档案"

    def _parse_response(
        self,
        response: Dict[str, Any],
        skill_manager: SkillManager,
    ) -> SkillRouteResult:
        """解析 LLM function calling 响应

        Args:
            response: LLM 响应字典
            skill_manager: Skill 管理器

        Returns:
            SkillRouteResult 路由结果
        """
        # 处理 function_call 响应
        function_call = response.get("function_call") or response.get(
            "tool_calls", [{}]
        )

        # 兼容 OpenAI 格式
        if isinstance(function_call, list) and function_call:
            function_call = function_call[0].get("function", {})

        if not function_call:
            # 没有 function call，视为直接回复
            content = response.get("content", "")
            return SkillRouteResult(
                is_direct_reply=True,
                direct_reply=content or "你好！有什么可以帮你的吗？",
            )

        # 解析 function call 参数
        arguments = function_call.get("arguments", "{}")
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except json.JSONDecodeError:
                logger.warning(f"function call 参数解析失败: {arguments}")
                return SkillRouteResult(
                    is_direct_reply=True,
                    direct_reply="你好！请告诉我你的健身需求。",
                )

        # 判断是直接回复还是 Skill 选择
        direct_reply = arguments.get("direct_reply", "")
        if direct_reply:
            return SkillRouteResult(
                is_direct_reply=True,
                direct_reply=direct_reply,
            )

        skill_id = arguments.get("skill_id", "")
        reason = arguments.get("reason", "")

        # 验证 skill_id 是否有效
        if skill_id:
            try:
                skill_manager.get(skill_id)
                return SkillRouteResult(
                    skill_id=skill_id,
                    reason=reason,
                    is_direct_reply=False,
                )
            except Exception:
                logger.warning(f"LLM 选择了无效的 Skill: {skill_id}")

        return SkillRouteResult(
            is_direct_reply=True,
            direct_reply="你好！请告诉我你的健身需求，我来帮你制定方案。",
        )
