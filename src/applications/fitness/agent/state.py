# -*- coding: utf-8 -*-
"""
LangGraph Agent 状态定义

定义 Agent 执行引擎的状态数据结构，使用 LangGraph 的 Annotated 消息累加模式。

版本: v1.0.0
日期: 2026-02-17
"""

from typing import TypedDict, Optional, List, Dict, Any, Annotated
from langgraph.graph.message import add_messages


class AgentState(TypedDict, total=False):
    """
    LangGraph Agent 状态

    使用 Annotated[list, add_messages] 实现消息自动累加，
    其余字段为普通覆盖式更新。
    """
    # ========== 请求上下文 ==========
    request_id: str
    user_id: str
    query: str

    # ========== 用户上下文 ==========
    user_profile: Optional[Dict[str, Any]]
    conversation_history: Optional[List[Dict[str, Any]]]
    membership_level: str

    # ========== LangGraph 消息（自动累加） ==========
    messages: Annotated[list, add_messages]

    # ========== 执行追踪 ==========
    tool_calls_count: int
    total_cost: float
    tool_results: List[Dict[str, Any]]

    # ========== 安全限制 ==========
    max_iterations: int
    cost_limit: float

    # ========== 输出 ==========
    final_response: Optional[str]

    # ========== 元数据 ==========
    errors: List[str]
    step_timings: Dict[str, float]
