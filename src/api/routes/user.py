# -*- coding: utf-8 -*-
"""
User Route - 用户相关接口

提供用户档案预热等功能，支持前端登录后主动预热用户数据。

POST /v1/user/warmup - 用户登录后预热用户档案和会员数据

版本：v1.0.0
更新日期：2026-01-02
"""

import logging
import asyncio
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator

logger = logging.getLogger(__name__)

router = APIRouter()


class WarmupRequest(BaseModel):
    """预热请求模型"""
    user_id: str
    force_refresh: bool = False  # 是否强制刷新缓存（用户档案更新时设为True）

    @field_validator("user_id", mode="before")
    @classmethod
    def coerce_user_id(cls, v):
        """兼容前端发送的整数 user_id，自动转为字符串"""
        if isinstance(v, (int, float)):
            return str(int(v))
        return v


class WarmupResponse(BaseModel):
    """预热响应模型"""
    success: bool
    message: str
    user_id: str
    preload_status: Dict[str, Any]


@router.post("/v1/user/warmup", response_model=WarmupResponse)
async def warmup_user(request: WarmupRequest) -> WarmupResponse:
    """
    用户登录后预热接口
    
    在用户登录成功后调用，预热用户档案和会员数据到缓存中，
    加快后续对话中的数据加载速度。
    
    预热内容：
    1. 用户档案（UserProfileCache）
    2. 会员权限数据（SmartPreloader）
    
    Args:
        request: {
            "user_id": "用户ID"
        }
    
    Returns:
        WarmupResponse: 预热结果
    """
    user_id = request.user_id
    force_refresh = request.force_refresh
    
    if not user_id:
        raise HTTPException(status_code=400, detail="缺少必需参数：user_id")
    
    # 类型转换：确保user_id是字符串
    if isinstance(user_id, (int, float)):
        user_id = str(user_id)
    
    logger.info(f"🔥 开始预热用户数据: user_id={user_id}, force_refresh={force_refresh}")
    
    preload_status = {
        "user_profile": "pending",
        "membership": "pending"
    }
    
    try:
        # 1. 预热用户档案
        try:
            from ...applications.fitness.workflow_executor import get_user_cache
            from ...applications.fitness.clients.backend_client import BackendClient
            
            backend_client = BackendClient()
            user_cache = get_user_cache(backend_client=backend_client)
            if user_cache:
                # 如果force_refresh=True，强制刷新缓存（用户档案已更新）
                profile = await user_cache.get_user_profile(user_id, force_refresh=force_refresh)
                if profile:
                    preload_status["user_profile"] = "success" if not force_refresh else "refreshed"
                    logger.info(f"✅ 用户档案预热成功: user_id={user_id}, refreshed={force_refresh}")
                else:
                    preload_status["user_profile"] = "not_found"
                    logger.warning(f"⚠️ 用户档案不存在: user_id={user_id}")
            else:
                preload_status["user_profile"] = "cache_not_available"
                logger.warning(f"⚠️ 用户缓存未初始化")
        except Exception as e:
            preload_status["user_profile"] = f"error: {str(e)}"
            logger.error(f"❌ 用户档案预热失败: user_id={user_id}, error={e}")
        
        # 2. 预热会员数据
        try:
            from ...framework.storage.warmup import get_warmup_manager

            warmup_manager = get_warmup_manager()
            if warmup_manager:
                # 触发会员数据预热
                await warmup_manager.preload_memberships([user_id])
                preload_status["membership"] = "started"
                logger.info(f"✅ 会员数据预热已启动: user_id={user_id}")
            else:
                preload_status["membership"] = "preloader_not_available"
                logger.warning(f"⚠️ 预加载器未初始化")

        except Exception as e:
            preload_status["membership"] = f"error: {str(e)}"
            logger.error(f"❌ 会员数据预热失败: user_id={user_id}, error={e}")
        
        # 判断整体成功状态
        success = (
            preload_status["user_profile"] in ["success", "refreshed", "not_found"] and
            preload_status["membership"] in ["started", "skipped", "preloader_not_available"]
        )
        
        message = "预热完成" if success else "预热部分失败"
        
        logger.info(
            f"🔥 用户预热完成: user_id={user_id}, "
            f"profile={preload_status['user_profile']}, "
            f"membership={preload_status['membership']}"
        )
        
        return WarmupResponse(
            success=success,
            message=message,
            user_id=user_id,
            preload_status=preload_status
        )
        
    except Exception as e:
        logger.error(f"❌ 用户预热异常: user_id={user_id}, error={e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"预热失败: {str(e)}")


@router.get("/v1/user/warmup/status/{user_id}")
async def get_warmup_status(user_id: str) -> Dict[str, Any]:
    """
    获取用户预热状态
    
    Args:
        user_id: 用户ID
    
    Returns:
        Dict: 预热状态信息
    """
    if not user_id:
        raise HTTPException(status_code=400, detail="缺少必需参数：user_id")
    
    status = {
        "user_id": user_id,
        "user_profile_cached": False,
        "membership_preloaded": False
    }
    
    try:
        # 检查用户档案缓存状态
        from ...applications.fitness.workflow_executor import get_user_cache
        from ...applications.fitness.clients.backend_client import BackendClient
        
        backend_client = BackendClient()
        user_cache = get_user_cache(backend_client=backend_client)
        
        if user_cache:
            # UserProfileCache 使用 UnifiedCache，直接尝试获取用户档案
            # 不使用 force_refresh，这样可以检查缓存是否存在
            try:
                profile = await user_cache.get_user_profile(user_id, force_refresh=False)
                status["user_profile_cached"] = profile is not None
                if profile:
                    # 添加一些档案信息用于调试
                    status["profile_preview"] = {
                        "has_name": bool(profile.get("name")),
                        "has_fitness_level": bool(profile.get("fitness_level")),
                        "has_goals": bool(profile.get("goals")),
                    }
            except Exception as cache_err:
                logger.warning(f"获取用户档案失败: {cache_err}")
                status["user_profile_cached"] = False
                status["cache_error"] = str(cache_err)
        else:
            status["cache_error"] = "user_cache not initialized"
        
        # 检查会员预热状态
        from ...framework.storage.warmup import get_warmup_manager
        warmup_manager = get_warmup_manager()
        if warmup_manager:
            # 新预加载器暂时没有is_user_preloaded方法，标记为unknown
            status["membership_preloaded"] = "unknown"
        
        return status
        
    except Exception as e:
        logger.error(f"获取预热状态失败: user_id={user_id}, error={e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取状态失败: {str(e)}")


# 导出路由
__all__ = ['router']
