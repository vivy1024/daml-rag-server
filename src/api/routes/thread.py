# -*- coding: utf-8 -*-
"""
Thread Route - 线程管理接口

提供 LangGraph 对话线程的 CRUD 操作：
- POST   /api/v1/thread/create          - 创建新线程
- GET    /api/v1/thread/list?user_id=X   - 列出用户线程
- DELETE /api/v1/thread/{thread_id}      - 删除线程

版本：v1.0.0
更新日期：2026-03-15
"""

import uuid
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from ..models.thread import (
    ThreadCreateRequest,
    ThreadCreateResponse,
    ThreadDeleteResponse,
    ThreadInfo,
    ThreadListResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/thread")

# 内存存储（后续由 Redis/DB 替换）
_thread_store: dict[str, ThreadInfo] = {}


@router.post("/create", response_model=ThreadCreateResponse)
async def create_thread(request: ThreadCreateRequest) -> ThreadCreateResponse:
    """
    创建新的对话线程

    为用户创建一个新的 LangGraph 线程，用于多轮对话状态管理。
    """
    thread_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    thread_info = ThreadInfo(
        thread_id=thread_id,
        user_id=request.user_id,
        title=request.title or f"对话 {now.strftime('%m-%d %H:%M')}",
        created_at=now,
        updated_at=now,
        message_count=0,
        metadata=request.metadata or {},
    )

    _thread_store[thread_id] = thread_info
    logger.info("创建线程: thread_id=%s, user_id=%s", thread_id, request.user_id)

    return ThreadCreateResponse(thread_id=thread_id, created_at=now)


@router.get("/list", response_model=ThreadListResponse)
async def list_threads(
    user_id: str = Query(..., description="用户ID", min_length=1),
) -> ThreadListResponse:
    """
    列出用户的所有对话线程

    按更新时间倒序返回。
    """
    user_threads = [
        t for t in _thread_store.values() if t.user_id == user_id
    ]
    # 按更新时间倒序
    user_threads.sort(key=lambda t: t.updated_at, reverse=True)

    return ThreadListResponse(threads=user_threads, total=len(user_threads))


@router.delete("/{thread_id}", response_model=ThreadDeleteResponse)
async def delete_thread(thread_id: str) -> ThreadDeleteResponse:
    """
    删除指定线程

    删除线程及其关联的所有 checkpoint 数据。
    """
    if thread_id not in _thread_store:
        raise HTTPException(
            status_code=404,
            detail=f"线程不存在: {thread_id}",
        )

    del _thread_store[thread_id]
    logger.info("删除线程: thread_id=%s", thread_id)

    return ThreadDeleteResponse(thread_id=thread_id, deleted=True)
