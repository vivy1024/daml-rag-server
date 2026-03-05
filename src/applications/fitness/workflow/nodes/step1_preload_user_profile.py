# -*- coding: utf-8 -*-
"""步骤1：预加载用户档案"""

import logging
from typing import Any

from ..state import WorkflowState, StateUpdate

logger = logging.getLogger(__name__)


async def node_preload_user_profile(
    state: WorkflowState,
    backend_client=None,
    cache_manager=None,
    user_cache=None,
    performance_monitor=None,
    perf_context=None,
    smart_preloader=None,
) -> StateUpdate:
    """
    步骤1：预加载用户档案（混合方案：缓存优先 + MCP工具降级）

    新增功能 (Requirements 3.1, 3.2, 3.3):
    - 用户档案加载完成后，异步预热步骤3需要的会员数据
    - 预热不阻塞主工作流执行

    Args:
        state: 当前工作流状态
        backend_client: 后端客户端（可选）
        cache_manager: 缓存管理器（可选）
        user_cache: 用户缓存（可选）
        performance_monitor: 性能监控器（可选）
        perf_context: 性能上下文（可选）
        smart_preloader: 智能预热器（可选）(Requirements 3.1)

    Returns:
        StateUpdate: 状态更新，包含 user_profile
    """
    request_id = state.get("request_id", "unknown")
    user_id = state.get("user_id")

    user_profile = state.get("user_profile")  # 可能已预先提供

    if user_profile:
        logger.info(f"✅ [{request_id}] 步骤1完成: 使用已提供的用户档案")
        # 即使使用已提供的档案，也触发步骤3预热 (Requirements 3.1)
        await _trigger_step3_preload(user_id, smart_preloader, request_id)
        return StateUpdate(updates={"user_profile": user_profile})

    if not user_id:
        logger.info(f"✅ [{request_id}] 步骤1完成: 无用户ID，跳过档案加载")
        return StateUpdate(updates={"user_profile": None})

    try:
        # 健壮的user_id转换逻辑
        if isinstance(user_id, int):
            user_id_int = user_id
        elif isinstance(user_id, str) and user_id.isdigit():
            user_id_int = int(user_id)
        else:
            logger.warning(f"⚠️ [{request_id}] 无效的user_id: {user_id}")
            return StateUpdate(
                updates={"user_profile": None},
                warning=f"无效的user_id: {user_id}"
            )

        # 主路径：使用缓存管理器获取用户档案
        if cache_manager:
            cache_key = f"user_profile:{user_id_int}"

            async def fetch_user_profile():
                """从数据库获取用户档案"""
                if user_cache:
                    return await user_cache.get_user_profile(str(user_id_int))
                elif backend_client:
                    return await backend_client.get_user_profile(user_id_int)
                return None

            # 使用缓存管理器获取
            user_profile = await cache_manager.get(
                key=cache_key,
                fetch_func=fetch_user_profile,
                ttl=300  # 5分钟TTL
            )

            if user_profile:
                logger.info(f"✅ [{request_id}] 步骤1完成: 用户档案已加载（缓存管理器）")
            else:
                logger.warning(f"⚠️ [{request_id}] 步骤1: 缓存管理器返回空档案")

        # 降级路径：直接使用用户缓存
        elif user_cache:
            user_profile = await user_cache.get_user_profile(str(user_id_int))
            if user_profile:
                logger.info(f"✅ [{request_id}] 步骤1完成: 用户档案已加载（用户缓存）")

        # 最后降级：直接调用后端
        elif backend_client:
            user_profile = await backend_client.get_user_profile(user_id_int)
            if user_profile:
                logger.info(f"✅ [{request_id}] 步骤1完成: 用户档案已加载（后端API）")

        if not user_profile:
            logger.info(f"✅ [{request_id}] 步骤1完成: 用户档案未找到，继续匿名模式")

        # ✅ 步骤1完成后，异步预热步骤3需要的会员数据 (Requirements 3.1, 3.2)
        await _trigger_step3_preload(user_id, smart_preloader, request_id)

        return StateUpdate(updates={"user_profile": user_profile})

    except Exception as e:
        logger.warning(f"⚠️ [{request_id}] 步骤1: 用户档案加载失败: {e}")
        return StateUpdate(
            updates={"user_profile": None},
            warning=f"用户档案加载失败: {str(e)}"
        )


async def _trigger_step3_preload(
    user_id: Any,
    smart_preloader,
    request_id: str
):
    """
    触发步骤3预热（内部辅助函数）

    在步骤1完成后调用，异步预热步骤3需要的会员数据。
    此函数不阻塞主工作流执行。

    Requirements:
        - 3.1: WHEN step 1 completes, THE DAML_RAG_System SHALL async preload membership data
        - 3.2: THE async preload SHALL NOT block the main workflow execution
    """
    if not user_id:
        return

    # 尝试获取预热器（如果未传入）
    if smart_preloader is None:
        try:
            # 使用预热系统
            from .....framework.storage.warmup import get_warmup_manager
            warmup_manager = get_warmup_manager()
            if warmup_manager:
                # 转换user_id为字符串
                user_id_str = str(user_id)

                # 异步预热会员数据（非阻塞）
                try:
                    await warmup_manager.preload_memberships([user_id_str])
                    logger.debug(
                        f"🚀 [{request_id}] 步骤1→步骤3预热已启动: user_id={user_id_str}"
                    )
                except Exception as e:
                    logger.warning(
                        f"⚠️ [{request_id}] 步骤3预热启动失败（不影响主流程）: {e}"
                    )
        except ImportError:
            pass
        except Exception as e:
            # 预热失败不影响主工作流
            logger.warning(
                f"⚠️ [{request_id}] 步骤3预热启动失败（不影响主流程）: {e}"
            )
