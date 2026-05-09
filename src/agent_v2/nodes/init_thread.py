# -*- coding: utf-8 -*-
"""
init_thread 节点 — 初始化会话线程

职责：
- 从 state 获取 user_id
- 加载 user_profile（当前简单实现：从 state 传入或返回空 dict）
- 返回 state 更新

版本: v2.0.0
日期: 2026-05-09
"""

import logging
from typing import Dict, Any

from ..state import AgentState

logger = logging.getLogger(__name__)


async def init_thread(state: AgentState) -> Dict[str, Any]:
    """初始化会话线程

    从 state 中获取 user_id，加载用户档案。
    当前为简单实现：如果 state 中已有 user_profile 则直接使用，
    否则返回空 dict。后续可接入 MCP user_profile 工具。

    Args:
        state: 当前 Agent 状态

    Returns:
        状态更新字典
    """
    user_id = state.get("user_id", "")
    thread_id = state.get("thread_id", "")

    logger.info(
        f"🚀 init_thread: user_id={user_id}, thread_id={thread_id}"
    )

    # 如果 state 中已有 user_profile，直接使用
    existing_profile = state.get("user_profile")
    if existing_profile:
        logger.debug("init_thread: 使用已有 user_profile")
        return {"user_profile": existing_profile}

    # 简单实现：返回空档案
    # TODO: 接入 MCP get_user_profile 工具加载完整档案
    logger.debug("init_thread: 无已有档案，返回空 dict")
    return {"user_profile": {}}
