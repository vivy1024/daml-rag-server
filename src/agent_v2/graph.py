# -*- coding: utf-8 -*-
"""
Agent Graph v2 — Skills-first Agent 编排图

使用 LangGraph StateGraph 构建 6 步流程：
init_thread → skill_select → safety_check → skill_execute → output_generate → record

条件边：
- skill_select 后：如果 is_direct_reply → 直接到 output_generate（跳过 safety_check + skill_execute）
- safety_check 后：如果 direct_reply 被设置（require_profile / denied）→ 跳到 output_generate

版本: v2.0.0
日期: 2026-05-09
"""

import logging
from typing import Optional

from langgraph.graph import StateGraph, START, END

from src.framework.persistence.checkpointer import get_checkpointer
from src.skills.router import SkillRouter
from src.skills.manager import SkillManager
from src.skills.executor import SkillExecutor
from src.harness_v2.pre_skill_policy import PreSkillPolicy
from src.harness_v2.tool_allowlist import ToolAllowlist
from src.harness_v2.output_verifier import OutputVerifierV2
from src.harness_v2.harness_tracer import HarnessTracerV2
from src.framework.models.llm_pool import LLMPoolManager

from .state import AgentState
from .nodes.init_thread import init_thread
from .nodes.skill_select import skill_select, configure_skill_select
from .nodes.safety_check import safety_check, configure_safety_check
from .nodes.skill_execute import skill_execute, configure_skill_execute
from .nodes.output_generate import output_generate, configure_output_generate
from .nodes.record import record, configure_record

logger = logging.getLogger(__name__)


def _route_after_skill_select(state: AgentState) -> str:
    """skill_select 后的条件路由

    如果设置了 direct_reply（简单问候/闲聊），跳过 safety_check 和 skill_execute，
    直接到 output_generate。

    Args:
        state: 当前 Agent 状态

    Returns:
        下一个节点名称
    """
    if state.get("direct_reply"):
        return "output_generate"
    return "safety_check"


def _route_after_safety_check(state: AgentState) -> str:
    """safety_check 后的条件路由

    如果 safety_check 设置了 direct_reply（require_profile / denied），
    跳过 skill_execute，直接到 output_generate。

    Args:
        state: 当前 Agent 状态

    Returns:
        下一个节点名称
    """
    if state.get("direct_reply"):
        return "output_generate"
    if not state.get("current_skill"):
        return "output_generate"
    return "skill_execute"


def build_agent_graph(
    skill_router: Optional[SkillRouter] = None,
    skill_manager: Optional[SkillManager] = None,
    skill_executor: Optional[SkillExecutor] = None,
    policy: Optional[PreSkillPolicy] = None,
    tool_allowlist: Optional[ToolAllowlist] = None,
    output_verifier: Optional[OutputVerifierV2] = None,
    harness_tracer: Optional[HarnessTracerV2] = None,
    llm_pool: Optional[LLMPoolManager] = None,
    use_memory_checkpointer: bool = True,
):
    """构建 Agent v2 编排图

    Args:
        skill_router: SkillRouter 实例
        skill_manager: SkillManager 实例
        skill_executor: SkillExecutor 实例
        policy: PreSkillPolicy 实例
        tool_allowlist: ToolAllowlist 实例
        output_verifier: OutputVerifierV2 实例
        harness_tracer: HarnessTracerV2 实例
        llm_pool: LLMPoolManager 实例
        use_memory_checkpointer: 是否使用内存 checkpointer（测试用）

    Returns:
        编译后的 LangGraph CompiledGraph
    """
    # 配置节点依赖
    if skill_router and skill_manager:
        configure_skill_select(router=skill_router, manager=skill_manager)

    if policy:
        configure_safety_check(policy=policy)

    _allowlist = tool_allowlist or ToolAllowlist()
    _tracer = harness_tracer or HarnessTracerV2()

    if skill_manager and skill_executor:
        configure_skill_execute(
            manager=skill_manager,
            executor=skill_executor,
            allowlist=_allowlist,
            tracer=_tracer,
        )

    _verifier = output_verifier or OutputVerifierV2()
    if llm_pool:
        configure_output_generate(verifier=_verifier, llm_pool=llm_pool)

    configure_record(tracer=_tracer)

    # 构建 StateGraph
    graph = StateGraph(AgentState)

    # 添加节点
    graph.add_node("init_thread", init_thread)
    graph.add_node("skill_select", skill_select)
    graph.add_node("safety_check", safety_check)
    graph.add_node("skill_execute", skill_execute)
    graph.add_node("output_generate", output_generate)
    graph.add_node("record", record)

    # 添加边
    graph.add_edge(START, "init_thread")
    graph.add_edge("init_thread", "skill_select")

    # 条件边：skill_select → safety_check 或 output_generate
    graph.add_conditional_edges(
        "skill_select",
        _route_after_skill_select,
        {"safety_check": "safety_check", "output_generate": "output_generate"},
    )

    # 条件边：safety_check → skill_execute 或 output_generate
    graph.add_conditional_edges(
        "safety_check",
        _route_after_safety_check,
        {"skill_execute": "skill_execute", "output_generate": "output_generate"},
    )

    graph.add_edge("skill_execute", "output_generate")
    graph.add_edge("output_generate", "record")
    graph.add_edge("record", END)

    # 编译
    if use_memory_checkpointer:
        from langgraph.checkpoint.memory import MemorySaver
        checkpointer = MemorySaver()
    else:
        checkpointer = get_checkpointer()

    compiled = graph.compile(checkpointer=checkpointer)

    logger.info("✅ Agent v2 Graph 构建完成 (6 nodes, 条件边)")
    return compiled
