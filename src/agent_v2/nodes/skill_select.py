# -*- coding: utf-8 -*-
"""
skill_select 节点 — Skill 路由选择

职责：
- 使用 SkillRouter 选择最合适的 Skill
- 如果 is_direct_reply → 设置 state.direct_reply
- 否则 → 设置 state.current_skill + state.skill_reason

版本: v2.0.0
日期: 2026-05-09
"""

import logging
from typing import Dict, Any

from src.skills.router import SkillRouter, SkillRouteResult
from src.skills.manager import SkillManager
from ..state import AgentState

logger = logging.getLogger(__name__)

# 模块级单例（由 graph 构建时注入）
_skill_router: SkillRouter | None = None
_skill_manager: SkillManager | None = None


def configure_skill_select(
    router: SkillRouter,
    manager: SkillManager,
) -> None:
    """配置 skill_select 节点依赖

    Args:
        router: SkillRouter 实例
        manager: SkillManager 实例
    """
    global _skill_router, _skill_manager
    _skill_router = router
    _skill_manager = manager


async def skill_select(state: AgentState) -> Dict[str, Any]:
    """Skill 路由选择节点

    调用 SkillRouter 根据用户消息和档案选择 Skill。
    如果是简单问候/闲聊，直接返回 direct_reply。

    Args:
        state: 当前 Agent 状态

    Returns:
        状态更新字典
    """
    if not _skill_router or not _skill_manager:
        logger.error("skill_select: SkillRouter 或 SkillManager 未配置")
        return {
            "direct_reply": "系统初始化中，请稍后再试。",
            "error": "skill_select 依赖未配置",
        }

    messages = state.get("messages", [])
    user_profile = state.get("user_profile") or {}

    try:
        result: SkillRouteResult = await _skill_router.route(
            messages=messages,
            user_profile=user_profile,
            skill_manager=_skill_manager,
        )
    except Exception as e:
        logger.error(f"skill_select: 路由调用异常: {e}")
        return {
            "direct_reply": "抱歉，我暂时无法处理你的请求，请稍后再试。",
            "error": str(e),
        }

    if result.is_direct_reply:
        logger.info(f"skill_select: 直接回复（不走 Skill）")
        return {"direct_reply": result.direct_reply}

    logger.info(
        f"skill_select: 选择 Skill [{result.skill_id}], "
        f"原因: {result.reason}"
    )
    return {
        "current_skill": result.skill_id,
        "skill_reason": result.reason,
    }
