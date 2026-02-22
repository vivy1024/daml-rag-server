# -*- coding: utf-8 -*-
"""
执行模式路由器

v4.0.0: Agent模式恢复，作为管线步骤7的执行方式。
- DAG: 固定编排（默认，所有用户）
- Agent: LangGraph动态决策（energy+会员）

版本: v4.0.0
日期: 2026-02-22
"""

import logging
from typing import Optional, Literal

logger = logging.getLogger(__name__)

ExecutionMode = Literal["dag", "agent"]

# Agent 模式所需的最低会员等级
AGENT_ALLOWED_TIERS = {"energy", "energy_plus", "pro", "admin"}


def resolve_execution_mode(
    requested_mode: Optional[str] = None,
    membership_level: str = "free",
) -> ExecutionMode:
    """
    解析最终执行模式

    Args:
        requested_mode: 前端请求的模式（"dag" 或 "agent"）
        membership_level: 会员等级

    Returns:
        "dag" 或 "agent"
    """
    if requested_mode == "agent":
        if membership_level.lower() in AGENT_ALLOWED_TIERS:
            return "agent"
        logger.info(f"Agent模式需要energy+会员，当前={membership_level}，降级为DAG")
        return "dag"

    return "dag"
