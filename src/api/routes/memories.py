# -*- coding: utf-8 -*-
"""
用户记忆管理 API

提供用户跨对话记忆的查询和清空接口。

版本: v1.0.0
日期: 2026-02-20
"""

import logging
from fastapi import APIRouter, Query

from ..models.api_response import ApiResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/user")


@router.get("/memories")
async def list_memories(user_id: int = Query(..., description="用户ID")):
    """获取用户记忆列表"""
    try:
        from ...applications.fitness.services.user_memory import get_user_memory_service
        service = get_user_memory_service()
        memories = await service.list_memories(user_id)
        return ApiResponse.success(data={"memories": memories, "count": len(memories)})
    except Exception as e:
        logger.error(f"获取记忆列表失败: {e}")
        return ApiResponse.error(500, f"获取记忆列表失败: {str(e)}")


@router.delete("/memories")
async def clear_memories(user_id: int = Query(..., description="用户ID")):
    """清空用户所有记忆"""
    try:
        from ...applications.fitness.services.user_memory import get_user_memory_service
        service = get_user_memory_service()
        count = await service.clear_all(user_id)
        return ApiResponse.success(data={"deleted_count": count}, msg=f"已清空 {count} 条记忆")
    except Exception as e:
        logger.error(f"清空记忆失败: {e}")
        return ApiResponse.error(500, f"清空记忆失败: {str(e)}")
