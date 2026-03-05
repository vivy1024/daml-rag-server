# -*- coding: utf-8 -*-
"""步骤2：会话记录存储 + 加载对话历史"""

import logging
import time

from ..state import WorkflowState, StateUpdate

logger = logging.getLogger(__name__)


async def node_store_session(
    state: WorkflowState,
    conversation_memory=None,
) -> StateUpdate:
    """
    步骤2：会话记录存储 + 加载对话历史

    新增功能：
    - 从 ConversationMemory 加载对话历史（Redis → 内存 → 后端）
    - 将历史格式化为 LLM 可用格式存入 state

    Args:
        state: 当前工作流状态
        conversation_memory: ConversationMemory 实例（可选）

    Returns:
        StateUpdate: 状态更新，包含 session_id, conversation_history, conversation_topic_id
    """
    request_id = state.get("request_id", "unknown")
    user_id = state.get("user_id", "anonymous")
    session_id = state.get("session_id")
    topic_id = state.get("conversation_topic_id")

    if not session_id:
        session_id = f"session_{user_id}_{int(time.time())}"

    # 加载对话历史
    conversation_history = []
    active_topic_id = topic_id

    if conversation_memory and user_id != "anonymous":
        try:
            # 如果指定了 topic_id，切换到该话题
            if topic_id:
                await conversation_memory.switch_topic(
                    user_id, topic_id, create_if_not_exists=True
                )
            else:
                active_topic_id = conversation_memory.get_active_topic_id(user_id)

            messages = await conversation_memory.get_history(
                user_id=user_id,
                topic_id=active_topic_id,
            )
            if messages:
                conversation_history = conversation_memory.format_history_for_llm(messages)
                logger.info(
                    f"✅ [{request_id}] 步骤2: 加载对话历史 {len(conversation_history)} 条, "
                    f"topic={active_topic_id}"
                )
        except Exception as e:
            logger.warning(f"⚠️ [{request_id}] 步骤2: 加载对话历史失败（不影响主流程）: {e}")

    logger.info(f"✅ [{request_id}] 步骤2完成: 会话ID={session_id[:16]}...")

    return StateUpdate(updates={
        "session_id": session_id,
        "conversation_history": conversation_history,
        "conversation_topic_id": active_topic_id,
    })
