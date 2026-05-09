# -*- coding: utf-8 -*-
"""
AgentState v2 — Skills-first Agent 状态定义

使用 TypedDict + Annotated 定义 LangGraph 状态，
支持 reducer（messages 使用 add 合并）。

版本: v2.0.0
日期: 2026-05-09
"""

from typing import TypedDict, Optional, Dict, Any, Annotated
from operator import add


class AgentState(TypedDict):
    """Agent v2 状态

    Attributes:
        messages: 对话消息列表（使用 add reducer 追加合并）
        user_id: 用户唯一标识
        thread_id: 会话线程 ID
        user_profile: 用户档案（从 MCP 加载）
        current_skill: 当前选择的 skill_id
        skill_reason: Skill 选择理由
        tool_results: 工具执行结果
        harness_trace: Harness 追踪记录
        approval_status: HITL 审批状态 (pending / approved / denied)
        direct_reply: 直接回答（不走 Skill）
        final_output: 最终输出文本
        error: 错误信息
    """

    messages: Annotated[list, add]
    user_id: str
    thread_id: str
    user_profile: Optional[Dict[str, Any]]
    current_skill: Optional[str]
    skill_reason: Optional[str]
    tool_results: Optional[Dict[str, Any]]
    harness_trace: Optional[Dict[str, Any]]
    approval_status: Optional[str]
    direct_reply: Optional[str]
    final_output: Optional[str]
    error: Optional[str]
