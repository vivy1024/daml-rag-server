# -*- coding: utf-8 -*-
"""
Approval API 数据模型

定义 HITL 审批相关的请求/响应 Pydantic 模型。

版本：v1.0.0
更新日期：2026-05-09
"""

from typing import Optional
from pydantic import BaseModel, Field


class ApprovalRespondRequest(BaseModel):
    """审批响应请求"""
    thread_id: str = Field(..., description="线程ID", min_length=1)
    approved: bool = Field(..., description="是否批准")
    user_id: str = Field(..., description="用户ID", min_length=1)


class ApprovalRespondResponse(BaseModel):
    """审批响应结果"""
    thread_id: str = Field(..., description="线程ID")
    resumed: bool = Field(..., description="是否成功恢复执行")
    current_skill: Optional[str] = Field(None, description="恢复后执行的 Skill")
    final_output: Optional[str] = Field(None, description="最终输出（非流式时返回）")


class ApprovalPendingResponse(BaseModel):
    """待审批状态查询响应"""
    has_pending: bool = Field(..., description="是否有待审批的 interrupt")
    thread_id: str = Field(..., description="线程ID")
    interrupt_info: Optional[dict] = Field(None, description="中断详情")
