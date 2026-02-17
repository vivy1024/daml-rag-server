# -*- coding: utf-8 -*-
"""
双模式路由器

根据会员等级和请求参数决定使用 DAG 模式还是 Agent 模式。

DAG 模式（默认）：固定模板编排，成本低，适合免费/暖心会员
Agent 模式：LLM 动态决策，灵活但成本高，仅限能量会员+

版本: v1.0.0
日期: 2026-02-17
"""

import logging
from typing import Dict, Any, Optional, Literal

logger = logging.getLogger(__name__)

# 允许使用 Agent 模式的会员等级
AGENT_MODE_ALLOWED_LEVELS = {"energy", "professional", "admin"}

ExecutionMode = Literal["dag", "agent"]


def resolve_execution_mode(
    requested_mode: Optional[str],
    membership_level: str,
) -> ExecutionMode:
    """
    解析最终执行模式

    规则：
    1. mode="dag" → 始终使用 DAG
    2. mode="agent" + 会员等级足够 → Agent
    3. mode="agent" + 会员等级不够 → 降级到 DAG
    4. mode="auto"（默认）→ DAG（Agent 模式需要显式请求）

    Args:
        requested_mode: 请求的模式 (auto/dag/agent)
        membership_level: 会员等级

    Returns:
        "dag" 或 "agent"
    """
    if not requested_mode or requested_mode == "auto":
        return "dag"

    if requested_mode == "dag":
        return "dag"

    if requested_mode == "agent":
        if membership_level in AGENT_MODE_ALLOWED_LEVELS:
            logger.info(f"Agent mode activated for {membership_level} member")
            return "agent"
        else:
            logger.info(
                f"Agent mode denied for {membership_level} member, "
                f"falling back to DAG"
            )
            return "dag"

    return "dag"
