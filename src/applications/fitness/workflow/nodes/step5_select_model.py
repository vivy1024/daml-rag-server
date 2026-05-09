# -*- coding: utf-8 -*-
"""
步骤5：智能模型选择（教师/学生切换）

⚠️ DEPRECATED (2026-05-09): 已被 Skills-first Agent v2 替代。
新系统使用 src/framework/models/llm_pool.py (LLMPoolManager) 统一管理模型。
教师/学生切换逻辑已废弃，改为后台可配置的国产模型池。
待全量切换稳定后删除。
"""

import logging

from src.framework.config.app_config import get_config
from ..state import WorkflowState, StateUpdate

logger = logging.getLogger(__name__)


async def node_select_model(
    state: WorkflowState
) -> StateUpdate:
    """
    步骤5：智能模型选择（三段式决策）

    注意：当DUAL_MODEL_ENABLED=false时，直接选择DeepSeek（teacher）

    Args:
        state: 当前工作流状态

    Returns:
        StateUpdate: 状态更新，包含 selected_model
    """
    request_id = state.get("request_id", "unknown")

    # ✅ 检查是否启用双模型选择
    dual_model_enabled = get_config().service.dual_model_enabled
    if not dual_model_enabled:
        logger.info(f"✅ [{request_id}] 步骤5完成: 双模型选择已禁用，直接使用DeepSeek")
        return StateUpdate(updates={"selected_model": "teacher"})

    complexity_level = state.get("complexity_level", "simple")
    similarity = state.get("_complexity_similarity", 0.0)
    is_premium = state.get("is_premium", False)

    # 模型选择逻辑
    if complexity_level == "complex" or similarity >= 0.7:
        model_choice = "teacher"
    else:
        model_choice = "student"

    logger.info(f"✅ [{request_id}] 步骤5完成: 选择模型={model_choice}")

    return StateUpdate(updates={"selected_model": model_choice})
