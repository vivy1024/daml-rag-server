# -*- coding: utf-8 -*-
"""
API Routes Package

统一导出所有API路由模块，提供：
- GraphRAG查询接口
- 聊天交互接口
- 用户反馈接口
- 系统健康检查
- 食物数据查询接口
- 用户预热接口

版本：v2.2.0
更新日期：2026-01-02
重构说明：新增用户预热API
"""

from fastapi import APIRouter
from .graphrag import router as graphrag_router
from .chat import router as chat_router
from .feedback import router as feedback_router
from .health import router as health_router
from .food import router as food_router
from .user import router as user_router

# 创建主路由器
api_router = APIRouter()

# 注册各模块路由
api_router.include_router(
    graphrag_router,
    tags=["GraphRAG"]
)

api_router.include_router(
    chat_router,
    tags=["Chat"]
)

api_router.include_router(
    feedback_router,
    tags=["Feedback"]
)

api_router.include_router(
    health_router,
    tags=["Health"]
)

api_router.include_router(
    food_router,
    tags=["Food"]
)

api_router.include_router(
    user_router,
    tags=["User"]
)

# 导出路由
__all__ = [
    'api_router'
]