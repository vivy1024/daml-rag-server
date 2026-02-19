# -*- coding: utf-8 -*-
"""
Persona API 路由

提供 SystemPersona 列表查询接口，供前端风格选择使用。

版本: v1.0.0
日期: 2026-02-20
"""

import logging
from fastapi import APIRouter

from ..models.api_response import ApiResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1")


@router.get("/personas")
async def list_personas():
    """获取可用的 Persona 列表"""
    try:
        from ...applications.fitness.config.system_persona import get_persona_manager
        pm = get_persona_manager()
        personas = pm.list_personas()
        return ApiResponse.success(data={
            "personas": personas,
            "default": pm.default_persona_id,
        })
    except Exception as e:
        logger.error(f"获取 Persona 列表失败: {e}")
        return ApiResponse.error(500, f"获取 Persona 列表失败: {str(e)}")
