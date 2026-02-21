# -*- coding: utf-8 -*-
"""
执行模式路由器（简化版）

v3.0.0: Agent模式已移至experimental/，统一使用DAG模式。

版本: v3.0.0
日期: 2026-02-22
"""

import logging
from typing import Optional, Literal

logger = logging.getLogger(__name__)

ExecutionMode = Literal["dag"]


def resolve_execution_mode(
    requested_mode: Optional[str] = None,
    membership_level: str = "free",
) -> ExecutionMode:
    """
    解析最终执行模式（统一返回DAG）

    Args:
        requested_mode: 请求的模式（忽略，统一DAG）
        membership_level: 会员等级（保留参数兼容性）

    Returns:
        "dag"
    """
    return "dag"
