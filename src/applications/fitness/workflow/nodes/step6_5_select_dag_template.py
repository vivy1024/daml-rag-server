# -*- coding: utf-8 -*-
"""
步骤6.5：LLM选择DAG模板（含会员权限检查）

⚠️ DEPRECATED (2026-05-09): 已被 Skills-first Agent v2 替代。
新系统使用 src/skills/router.py (SkillRouter) 替代 LLM 选 DAG 模板。
Skill 选择由 function calling 完成，不再暴露模板概念给用户。
待全量切换稳定后删除。
"""

import logging
import hashlib

from ..state import WorkflowState, StateUpdate

logger = logging.getLogger(__name__)


async def node_select_dag_template(
    state: WorkflowState,
    template_manager=None,
    decision_engine=None,
    cache_manager=None
) -> StateUpdate:
    """
    步骤6.5：LLM选择DAG模板（含会员权限检查）

    工作流程：
    1. 检查是否有用户强制指定的模板ID（template_id参数）
    2. 如果有强制指定，直接使用该模板（跳过LLM选择）
    3. 如果没有强制指定，先查缓存，未命中再调LLM选择
    4. 检查用户会员等级是否有权使用该模板
    5. 如果无权限，自动降级到用户可用的模板
    6. 返回最终选择的模板ID和权限检查结果

    会员等级与模板对应（MVP阶段）：
    - 免费版(2个): greeting, quick_consultation
    - 暖心会员(13个): 全部模板（¥6首充福利）
    - 能量会员: 暂不开放（等Agent模式开发完成）

    Args:
        state: 当前工作流状态
        template_manager: DAG模板管理器（可选）
        decision_engine: LLM决策引擎（可选）
        cache_manager: 缓存管理器（可选，用于缓存LLM模板选择结果）

    Returns:
        StateUpdate: 状态更新，包含 dag_template_id, _permission_check_result
    """
    request_id = state.get("request_id", "unknown")
    query_text = state.get("query_text", "")
    user_profile = state.get("user_profile")
    session_id = state.get("session_id")
    few_shot_examples = state.get("few_shot_examples", [])
    membership_info = state.get("membership_info")  # 从步骤3获取的会员信息
    force_template_id = state.get("template_id")  # 用户强制指定的模板ID

    selected_template_id = None
    cached_template_id = None
    permission_denied = False
    upgrade_message = None

    try:
        from ...llm_decision_engine import LLMDecisionEngine, DAGSelectionRequest
        from ...dag_template_system import DAGTemplateManager
        from ...services.dag_template_permission import (
            check_template_permission,
            get_user_membership_tier,
            get_template_count_by_tier
        )

        # 初始化模板管理器
        if template_manager is None:
            template_manager = DAGTemplateManager()

        # ✅ 检查是否有用户强制指定的模板ID
        if force_template_id:
            # 验证模板ID是否有效
            template = template_manager.get_template(force_template_id)
            if template:
                original_template_id = force_template_id
                logger.info(
                    f"🎯 [{request_id}] 步骤6.5: 用户强制指定模板={force_template_id}，跳过LLM选择"
                )
            else:
                # 无效的模板ID，回退到LLM选择
                logger.warning(
                    f"⚠️ [{request_id}] 步骤6.5: 无效的模板ID={force_template_id}，回退到LLM选择"
                )
                force_template_id = None

        # 如果没有强制指定，使用LLM选择（带缓存）
        if not force_template_id:
            # 初始化决策引擎
            if decision_engine is None:
                decision_engine = LLMDecisionEngine(template_manager)

            # 缓存key: 基于查询文本hash + 会员等级
            user_tier = get_user_membership_tier(membership_info)
            query_hash = hashlib.md5(query_text.encode()).hexdigest()[:12]
            cache_key = f"dag_template:{query_hash}:{user_tier}"

            # 尝试从缓存获取
            cached_template_id = None
            if cache_manager:
                cached_template_id = await cache_manager.get(cache_key)

            if cached_template_id:
                # 缓存命中，跳过LLM调用
                original_template_id = cached_template_id
                logger.info(
                    f"⚡ [{request_id}] 步骤6.5: 缓存命中 模板={original_template_id}, "
                    f"key={cache_key}"
                )
            else:
                # 缓存未命中，调用LLM选择
                selection_request = DAGSelectionRequest(
                    user_query=query_text,
                    user_profile=user_profile or {},
                    available_templates=template_manager.get_all_templates(),
                    session_context={"session_id": session_id},
                    few_shot_examples=few_shot_examples
                )

                selection_result = await decision_engine.select_dag_template(selection_request)
                original_template_id = selection_result.selected_template_id

                # 写入缓存（TTL=1小时）
                if cache_manager and original_template_id:
                    await cache_manager.set(cache_key, original_template_id, ttl=3600)

                logger.info(
                    f"🤖 [{request_id}] 步骤6.5: LLM选择模板={original_template_id}, "
                    f"置信度={selection_result.confidence:.2f}, 已缓存"
                )
        else:
            original_template_id = force_template_id

        # ✅ 会员权限检查
        permission_result = check_template_permission(original_template_id, membership_info)
        user_tier = get_user_membership_tier(membership_info)
        available_count, total_count = get_template_count_by_tier(user_tier)

        if permission_result.allowed:
            # 有权限，使用原始选择
            selected_template_id = original_template_id
            logger.info(
                f"✅ [{request_id}] 步骤6.5完成: 模板={selected_template_id}, "
                f"会员={user_tier}, 可用模板={available_count}/{total_count}"
                f"{', 用户强制指定' if force_template_id else ''}"
            )
        else:
            # 无权限，使用降级模板
            selected_template_id = permission_result.fallback_template_id or "quick_consultation"
            permission_denied = True
            upgrade_message = permission_result.message

            logger.warning(
                f"⚠️ [{request_id}] 步骤6.5: 权限不足，模板降级 "
                f"{original_template_id} → {selected_template_id}, "
                f"会员={user_tier}, 需要={permission_result.required_tier}"
            )

        return StateUpdate(updates={
            "dag_template_id": selected_template_id,
            "_dag_selection_confidence": 1.0 if (force_template_id or cached_template_id) else selection_result.confidence,
            "_dag_selection_reason": "用户强制指定" if force_template_id else ("缓存命中" if cached_template_id else selection_result.selection_reason),
            "_original_template_id": original_template_id,
            "_force_template_used": bool(force_template_id),
            "_permission_denied": permission_denied,
            "_upgrade_message": upgrade_message,
            "_user_tier": user_tier,
            "_available_templates_count": available_count,
            "_total_templates_count": total_count
        })

    except Exception as e:
        logger.warning(f"⚠️ [{request_id}] 步骤6.5: LLM选择失败: {e}")

        # 降级到规则匹配
        try:
            from ...dag_template_system import DAGTemplateManager
            from ...services.dag_template_permission import check_template_permission

            if template_manager is None:
                template_manager = DAGTemplateManager()
            selected_template_id = "quick_consultation"  # LLM分类失败时统一fallback

            # 即使降级也要检查权限
            permission_result = check_template_permission(selected_template_id, membership_info)
            if not permission_result.allowed:
                selected_template_id = permission_result.fallback_template_id or "quick_consultation"

            logger.info(f"✅ [{request_id}] 步骤6.5完成: 使用降级策略，选择模板={selected_template_id}")
        except Exception as fallback_error:
            logger.error(f"❌ [{request_id}] 步骤6.5: 降级策略也失败: {fallback_error}")
            selected_template_id = "quick_consultation"  # 最终降级到免费模板

        return StateUpdate(
            updates={"dag_template_id": selected_template_id},
            warning=f"LLM选择失败，使用降级策略: {str(e)}"
        )
