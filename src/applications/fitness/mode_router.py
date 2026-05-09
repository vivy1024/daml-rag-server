# -*- coding: utf-8 -*-
"""
执行模式路由器

⚠️ DEPRECATED (2026-05-09): 已被 Skills-first Agent v2 替代。
新系统不再区分 dag/agent 模式，统一走 Agent v2 流程。
前端不再暴露策略切换，由 Agent 自主决策。
当 AGENT_V2_ENABLED=true 时此模块不再被调用。
待全量切换稳定后删除。

v4.1.0: 积分体系对齐 — 所有用户均可使用Agent模式，
权限控制由积分消耗机制统一处理（与DAG模板一致）。
- DAG: 固定编排（默认）
- Agent: LangGraph动态决策（前端请求即可）

版本: v4.1.0
日期: 2026-02-22
"""

import logging
from typing import Optional, Literal

logger = logging.getLogger(__name__)

ExecutionMode = Literal["dag", "agent"]


def resolve_execution_mode(
    requested_mode: Optional[str] = None,
) -> ExecutionMode:
    """
    解析最终执行模式

    积分体系下不再按会员等级限制，前端请求agent即返回agent。
    积分消耗在执行层统一扣减。

    Args:
        requested_mode: 前端请求的模式（"dag" 或 "agent"）

    Returns:
        "dag" 或 "agent"
    """
    if requested_mode == "agent":
        return "agent"

    return "dag"
