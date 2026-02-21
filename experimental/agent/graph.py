# -*- coding: utf-8 -*-
"""
LangGraph Agent 图构建（Skills 版）

构建 StateGraph: agent → safety_check → tools → agent / END

v2.0: tool_node 接收 skill_manager，支持 load_skill 调用

版本: v2.0.0
日期: 2026-02-19
"""

import logging
from functools import partial

from langgraph.graph import StateGraph, END

from .state import AgentState
from .nodes import (
    agent_node,
    tool_node,
    safety_check_node,
    should_use_tool,
    should_continue,
)

logger = logging.getLogger(__name__)


def build_agent_graph(
    llm_client,
    mcp_orchestrator,
    tool_schemas: list,
    skill_manager=None,
) -> StateGraph:
    """
    构建 LangGraph Agent 执行图

    图结构:
        START → agent → (should_use_tool) → safety_check / END
        safety_check → (should_continue) → tools / END
        tools → agent

    Args:
        llm_client: LLM客户端（需支持 chat_with_tools）
        mcp_orchestrator: MCPOrchestrator 实例
        tool_schemas: 工具的 OpenAI function-calling schema 列表
        skill_manager: SkillManager 实例（v2.0 新增）

    Returns:
        编译后的 LangGraph 可执行图
    """
    graph = StateGraph(AgentState)

    # 绑定依赖到节点函数
    bound_agent = partial(agent_node, llm_client=llm_client, tool_schemas=tool_schemas)
    bound_tools = partial(
        tool_node,
        mcp_orchestrator=mcp_orchestrator,
        skill_manager=skill_manager,
    )

    # 添加节点
    graph.add_node("agent", bound_agent)
    graph.add_node("safety_check", safety_check_node)
    graph.add_node("tools", bound_tools)

    # 设置入口
    graph.set_entry_point("agent")

    # 条件边：agent → safety_check 或 END
    graph.add_conditional_edges(
        "agent",
        should_use_tool,
        {
            "safety_check": "safety_check",
            "end": END,
        },
    )

    # 条件边：safety_check → tools 或 END
    graph.add_conditional_edges(
        "safety_check",
        should_continue,
        {
            "tools": "tools",
            "end": END,
        },
    )

    # 普通边：tools → agent（循环回去让LLM继续决策）
    graph.add_edge("tools", "agent")

    compiled = graph.compile()
    logger.info(
        f"LangGraph Agent graph compiled: "
        f"skills={'enabled' if skill_manager else 'disabled'}"
    )
    return compiled
