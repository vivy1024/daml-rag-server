# -*- coding: utf-8 -*-
"""
Conversation Route - 对话历史管理接口

提供对话话题和消息的 CRUD 操作：
- GET  /v1/conversations/{user_id}                    - 获取用户话题列表
- GET  /v1/conversations/{user_id}/{topic_id}/messages - 获取话题消息
- POST /v1/conversations/{user_id}/topics              - 创建新话题
- DELETE /v1/conversations/{user_id}/{topic_id}        - 删除话题

版本：v1.0.0
更新日期：2026-02-17
"""

import logging
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from ..models import ApiResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/conversations")


# ============ 请求模型 ============

class CreateTopicRequest(BaseModel):
    """创建话题请求"""
    topic_id: Optional[str] = Field(None, description="话题ID（可选，自动生成）")
    title: Optional[str] = Field(None, description="话题标题")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


# ============ 获取 ConversationMemory 实例 ============

_conversation_memory_instance = None


def _get_conversation_memory():
    """获取全局 ConversationMemory 实例（懒初始化单例）"""
    global _conversation_memory_instance
    if _conversation_memory_instance is not None:
        return _conversation_memory_instance

    from ...applications.fitness.context.conversation_memory import ConversationMemory

    # 尝试连接 Redis
    redis_client = None
    try:
        import redis.asyncio as aioredis
        import os
        redis_host = os.getenv("REDIS_HOST", "redis")
        redis_port = int(os.getenv("REDIS_PORT", "6379"))
        redis_client = aioredis.Redis(host=redis_host, port=redis_port, decode_responses=True)
        logger.info(f"ConversationMemory Redis: {redis_host}:{redis_port}")
    except Exception as e:
        logger.warning(f"Redis 连接创建失败，降级到纯内存: {e}")

    _conversation_memory_instance = ConversationMemory(
        enable_persistence=False,
        redis_client=redis_client,
    )
    return _conversation_memory_instance


# ============ 路由 ============

@router.get("/{user_id}")
async def list_topics(user_id: str):
    """
    获取用户的话题列表

    Args:
        user_id: 用户ID

    Returns:
        话题列表
    """
    try:
        memory = _get_conversation_memory()
        topics = await memory.get_user_topics(user_id)
        active_topic_id = memory.get_active_topic_id(user_id)

        return ApiResponse.success(data={
            "user_id": user_id,
            "active_topic_id": active_topic_id,
            "topics": topics,
            "count": len(topics),
        })
    except Exception as e:
        logger.error(f"获取话题列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取话题列表失败: {str(e)}")


@router.get("/{user_id}/{topic_id}/messages")
async def get_messages(
    user_id: str,
    topic_id: str,
    limit: int = 10,
):
    """
    获取话题的消息列表

    Args:
        user_id: 用户ID
        topic_id: 话题ID
        limit: 返回消息数量（默认10）

    Returns:
        消息列表
    """
    try:
        memory = _get_conversation_memory()
        messages = await memory.get_history(
            user_id=user_id,
            topic_id=topic_id,
            n_messages=limit,
        )

        return ApiResponse.success(data={
            "user_id": user_id,
            "topic_id": topic_id,
            "messages": [m.to_dict() for m in messages],
            "count": len(messages),
        })
    except Exception as e:
        logger.error(f"获取消息列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取消息列表失败: {str(e)}")


@router.post("/{user_id}/topics")
async def create_topic(user_id: str, body: CreateTopicRequest):
    """
    创建新话题

    Args:
        user_id: 用户ID
        body: 创建话题请求

    Returns:
        创建的话题信息
    """
    try:
        memory = _get_conversation_memory()

        # 生成 topic_id（如果未提供）
        topic_id = body.topic_id
        if not topic_id:
            topic_id = memory._generate_topic_id(user_id)

        topic = await memory.create_topic(
            user_id=user_id,
            topic_id=topic_id,
            title=body.title,
            metadata=body.metadata,
        )

        return ApiResponse.success(data=topic.to_dict())
    except Exception as e:
        logger.error(f"创建话题失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"创建话题失败: {str(e)}")


@router.delete("/{user_id}/{topic_id}")
async def delete_topic(user_id: str, topic_id: str):
    """
    删除话题（清空消息并移除话题）

    Args:
        user_id: 用户ID
        topic_id: 话题ID

    Returns:
        删除结果
    """
    try:
        memory = _get_conversation_memory()
        await memory.clear_topic(user_id=user_id, topic_id=topic_id)

        return ApiResponse.success(data={
            "user_id": user_id,
            "topic_id": topic_id,
            "deleted": True,
        })
    except Exception as e:
        logger.error(f"删除话题失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"删除话题失败: {str(e)}")


# 导出路由
__all__ = ['router']
