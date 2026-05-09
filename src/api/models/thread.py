# -*- coding: utf-8 -*-
"""
Thread API 数据模型

定义线程管理相关的请求/响应 Pydantic 模型：
- ThreadCreateRequest: 创建线程请求
- ThreadCreateResponse: 创建线程响应
- ThreadListResponse: 线程列表响应
- ThreadInfo: 单个线程信息

版本：v1.0.0
更新日期：2026-03-15
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ThreadCreateRequest(BaseModel):
    """创建线程请求"""
    user_id: str = Field(..., description="用户ID", min_length=1)
    title: Optional[str] = Field(None, description="线程标题（可选）")
    metadata: Optional[dict] = Field(
        default_factory=dict, description="自定义元数据"
    )


class ThreadInfo(BaseModel):
    """单个线程信息"""
    thread_id: str = Field(..., description="线程唯一ID")
    user_id: str = Field(..., description="所属用户ID")
    title: Optional[str] = Field(None, description="线程标题")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="最后更新时间")
    message_count: int = Field(default=0, description="消息数量")
    metadata: dict = Field(default_factory=dict, description="自定义元数据")


class ThreadCreateResponse(BaseModel):
    """创建线程响应"""
    thread_id: str = Field(..., description="新创建的线程ID")
    created_at: datetime = Field(..., description="创建时间")


class ThreadListResponse(BaseModel):
    """线程列表响应"""
    threads: list[ThreadInfo] = Field(
        default_factory=list, description="线程列表"
    )
    total: int = Field(default=0, description="总数")


class ThreadDeleteResponse(BaseModel):
    """删除线程响应"""
    thread_id: str = Field(..., description="被删除的线程ID")
    deleted: bool = Field(default=True, description="是否成功删除")
