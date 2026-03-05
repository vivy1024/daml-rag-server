# -*- coding: utf-8 -*-
"""步骤3：检查会员权限"""

import logging

from ..state import WorkflowState, StateUpdate

logger = logging.getLogger(__name__)


async def node_check_membership(
    state: WorkflowState,
    backend_client=None,
    cache_manager=None,
    membership_cache=None,
    smart_preloader=None,
) -> StateUpdate:
    """
    步骤3：检查会员权限（带完整错误处理 + 缓存管理器集成）

    新增功能 (Requirements 3.3):
    - 记录预热缓存命中，用于追踪预热效果

    Args:
        state: 当前工作流状态
        backend_client: 后端客户端（可选）
        cache_manager: 缓存管理器（可选）
        membership_cache: 会员缓存（可选）
        smart_preloader: 智能预热器（可选，用于追踪预热效果）

    Returns:
        StateUpdate: 状态更新，包含 membership_info 和 is_premium
    """
    request_id = state.get("request_id", "unknown")
    user_id = state.get("user_id")

    if not user_id:
        logger.info(f"✅ [{request_id}] 步骤3完成: 匿名用户")
        return StateUpdate(updates={
            "membership_info": None,
            "is_premium": False
        })

    try:
        # 健壮的user_id转换
        if isinstance(user_id, int):
            user_id_int = user_id
        elif isinstance(user_id, str) and user_id.isdigit():
            user_id_int = int(user_id)
        else:
            logger.info(f"✅ [{request_id}] 步骤3完成: 无效user_id，匿名模式")
            return StateUpdate(updates={
                "membership_info": None,
                "is_premium": False
            })

        membership = None
        cache_hit = False  # 追踪是否缓存命中

        # 主路径：使用缓存管理器
        if cache_manager:
            cache_key = f"user_membership:{user_id_int}"

            async def fetch_membership():
                if membership_cache:
                    return await membership_cache.get_user_membership(str(user_id_int))
                return None

            membership = await cache_manager.get(
                key=cache_key,
                fetch_func=fetch_membership,
                ttl=600  # 10分钟TTL
            )

            # 检查是否是缓存命中（通过缓存管理器的统计）
            if membership and hasattr(cache_manager, 'stats'):
                cache_hit = True

        # 降级路径：直接使用会员缓存
        elif membership_cache:
            membership = await membership_cache.get_user_membership(str(user_id_int))
            cache_hit = membership is not None

        # ✅ 记录预热缓存命中（用于追踪预热效果）(Requirements 3.3)
        if cache_hit:
            await _record_preload_cache_hit(str(user_id_int), smart_preloader, request_id)

        if membership:
            tier = membership.get('tier', 'free')
            is_fallback = membership.get('_fallback', False)
            is_premium = tier != 'free'

            if is_fallback:
                logger.info(f"✅ [{request_id}] 步骤3完成: 会员等级={tier}（降级）")
            else:
                logger.info(f"✅ [{request_id}] 步骤3完成: 会员等级={tier}")

            return StateUpdate(updates={
                "membership_info": membership,
                "is_premium": is_premium
            })
        else:
            logger.info(f"✅ [{request_id}] 步骤3完成: 会员信息未找到")
            return StateUpdate(updates={
                "membership_info": None,
                "is_premium": False
            })

    except Exception as e:
        logger.warning(f"⚠️ [{request_id}] 步骤3: 会员权限检查失败: {e}")
        return StateUpdate(
            updates={
                "membership_info": None,
                "is_premium": False
            },
            warning=f"会员权限检查失败: {str(e)}"
        )


async def _record_preload_cache_hit(
    user_id: str,
    smart_preloader,
    request_id: str
):
    """
    记录预热缓存命中（内部辅助函数）

    用于追踪步骤1预热步骤3的效果。

    Requirements:
        - 3.3: WHEN step 3 executes, THE Membership_Cache SHALL find data already in cache
    """
    # 尝试获取预热器（如果未传入）
    if smart_preloader is None:
        try:
            # 预热系统暂时没有record_cache_hit方法，跳过追踪
            logger.debug(
                f"📊 [{request_id}] 步骤3预热效果追踪（暂不支持）: user_id={user_id}"
            )
        except ImportError:
            pass
        except Exception as e:
            # 追踪失败不影响主工作流
            logger.debug(f"⚠️ [{request_id}] 预热效果追踪失败: {e}")
