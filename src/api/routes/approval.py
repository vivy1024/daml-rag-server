# -*- coding: utf-8 -*-
"""
Approval Route - HITL 审批接口

提供 Agent v2 HITL（Human-in-the-Loop）审批操作：
- POST /api/v1/approval/respond  - 用户响应审批（批准/拒绝）
- GET  /api/v1/approval/pending  - 查询线程是否有待审批中断

当 Agent 检测到高风险操作（如有伤病用户请求高强度训练），
会通过 LangGraph interrupt 暂停执行，等待用户确认。
用户通过此接口响应后，Agent 恢复执行。

版本：v1.0.0
更新日期：2026-05-09
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from langgraph.types import Command

from ..models.approval import (
    ApprovalPendingResponse,
    ApprovalRespondRequest,
    ApprovalRespondResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/approval")

# Agent graph 实例引用（由 configure_approval_route 注入）
_agent_graph = None


def configure_approval_route(agent_graph):
    """注入 Agent graph 实例

    Args:
        agent_graph: 编译后的 LangGraph CompiledGraph
    """
    global _agent_graph
    _agent_graph = agent_graph
    logger.info("Approval route: agent_graph 已配置")


@router.post("/respond", response_model=ApprovalRespondResponse)
async def respond_approval(request: ApprovalRespondRequest) -> ApprovalRespondResponse:
    """
    响应审批请求

    用户确认（approved=True）后，Agent 恢复执行被中断的 Skill。
    用户拒绝（approved=False）后，Agent 使用保守方案。
    """
    if not _agent_graph:
        raise HTTPException(status_code=503, detail="Agent 服务未就绪")

    thread_id = request.thread_id
    config = {"configurable": {"thread_id": thread_id}}

    logger.info(
        "[Approval] 收到审批响应: thread_id=%s, approved=%s, user_id=%s",
        thread_id, request.approved, request.user_id,
    )

    try:
        # 检查是否有 pending interrupt
        graph_state = await _agent_graph.aget_state(config)

        if not graph_state or not graph_state.next:
            return ApprovalRespondResponse(
                thread_id=thread_id,
                resumed=False,
                current_skill=None,
                final_output="该线程没有待审批的操作",
            )

        # 恢复执行
        resume_value = "approved" if request.approved else "denied"
        result = await _agent_graph.ainvoke(
            Command(resume=resume_value),
            config=config,
        )

        return ApprovalRespondResponse(
            thread_id=thread_id,
            resumed=True,
            current_skill=result.get("current_skill"),
            final_output=result.get("final_output"),
        )

    except Exception as e:
        logger.error("[Approval] 恢复执行失败: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"恢复执行失败: {str(e)}")


@router.get("/pending", response_model=ApprovalPendingResponse)
async def get_pending_approval(
    thread_id: str = Query(..., description="线程ID", min_length=1),
) -> ApprovalPendingResponse:
    """
    查询线程是否有待审批的中断

    前端可轮询此接口检查是否需要弹出确认弹窗。
    """
    if not _agent_graph:
        return ApprovalPendingResponse(
            has_pending=False,
            thread_id=thread_id,
            interrupt_info=None,
        )

    config = {"configurable": {"thread_id": thread_id}}

    try:
        graph_state = await _agent_graph.aget_state(config)

        if not graph_state or not graph_state.tasks:
            return ApprovalPendingResponse(
                has_pending=False,
                thread_id=thread_id,
                interrupt_info=None,
            )

        # 检查是否有 interrupt
        for task in graph_state.tasks:
            if task.interrupts:
                interrupt = task.interrupts[0]
                return ApprovalPendingResponse(
                    has_pending=True,
                    thread_id=thread_id,
                    interrupt_info=interrupt.value if hasattr(interrupt, 'value') else None,
                )

        return ApprovalPendingResponse(
            has_pending=False,
            thread_id=thread_id,
            interrupt_info=None,
        )

    except Exception as e:
        logger.warning("[Approval] 查询 pending 失败: %s", e)
        return ApprovalPendingResponse(
            has_pending=False,
            thread_id=thread_id,
            interrupt_info=None,
        )
