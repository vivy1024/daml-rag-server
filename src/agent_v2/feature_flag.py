# -*- coding: utf-8 -*-
"""
Feature Flag — Agent v2 启用控制

通过环境变量 AGENT_V2_ENABLED 控制是否启用 Agent v2 运行时。
默认 False（使用旧的 DAG 模式）。

版本: v2.0.0
日期: 2026-05-09
"""

import os
import logging

logger = logging.getLogger(__name__)


def is_agent_v2_enabled() -> bool:
    """检查 Agent v2 是否启用

    读取环境变量 AGENT_V2_ENABLED，支持以下值：
    - "true" / "1" / "yes" → 启用
    - 其他值或未设置 → 禁用

    Returns:
        是否启用 Agent v2
    """
    value = os.getenv("AGENT_V2_ENABLED", "false").lower().strip()
    enabled = value in ("true", "1", "yes")

    if enabled:
        logger.info("🚀 Agent v2 已启用 (AGENT_V2_ENABLED=%s)", value)
    else:
        logger.debug("Agent v2 未启用 (AGENT_V2_ENABLED=%s)", value)

    return enabled
