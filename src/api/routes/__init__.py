# -*- coding: utf-8 -*-
"""
API Routes Package

v3.1.0: Agent/Chat/Thread 路由已迁移到 YuzhenFork。
保留：GraphRAG、Health、Food、User、Feedback、ModelEvaluation
"""

from fastapi import APIRouter
from .graphrag import router as graphrag_router
from .feedback import router as feedback_router
from .health import router as health_router
from .food import router as food_router
from .user import router as user_router
from .model_evaluation import router as model_evaluation_router

# 创建主路由器
api_router = APIRouter()

# 注册各模块路由
api_router.include_router(graphrag_router, tags=["GraphRAG"])
api_router.include_router(feedback_router, tags=["Feedback"])
api_router.include_router(health_router, tags=["Health"])
api_router.include_router(food_router, tags=["Food"])
api_router.include_router(user_router, tags=["User"])
api_router.include_router(model_evaluation_router, tags=["ModelEvaluation"])

__all__ = ['api_router']
