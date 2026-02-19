# -*- coding: utf-8 -*-
"""
双模式路由器

根据请求参数决定使用 DAG 模式还是 Agent 模式。
所有会员等级均可使用 Agent 模式，区别仅在积分消耗倍率。

DAG 模式（默认）：固定模板编排，积分消耗 1.0x
Agent 模式：LLM 动态编排 Skills，积分消耗 1.5x

版本: v2.0.0
日期: 2026-02-19
"""

import logging
from typing import Dict, Any, Optional, Literal

logger = logging.getLogger(__name__)

ExecutionMode = Literal["dag", "agent"]


def resolve_execution_mode(
    requested_mode: Optional[str],
    membership_level: str,
) -> ExecutionMode:
    """
    解析最终执行模式

    规则（v2.0 — 去除等级锁）：
    1. mode="dag" → 使用 DAG
    2. mode="agent" → 使用 Agent（所有等级均可）
    3. mode="auto"（默认）→ DAG

    Args:
        requested_mode: 请求的模式 (auto/dag/agent)
        membership_level: 会员等级（保留参数兼容性，不再用于限制）

    Returns:
        "dag" 或 "agent"
    """
    if not requested_mode or requested_mode == "auto":
        return "dag"

    if requested_mode == "dag":
        return "dag"

    if requested_mode == "agent":
        logger.info(f"Agent mode activated for {membership_level} member")
        return "agent"

    return "dag"
