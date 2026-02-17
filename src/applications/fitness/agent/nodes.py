# -*- coding: utf-8 -*-
"""
LangGraph Agent 节点定义

三个核心节点：
1. agent_node - LLM决策（调用工具 or 最终回答）
2. tool_node - 通过MCP编排器执行工具
3. safety_check_node - 迭代/成本/白名单检查

两个条件函数：
- should_use_tool - agent_node 后判断是否需要调用工具
- should_continue - safety_check_node 后判断是否继续循环

版本: v1.0.0
日期: 2026-02-17
"""

import logging
import time
from typing import Dict, Any, Literal

from .state import AgentState

logger = logging.getLogger(__name__)

# 工具白名单（允许Agent调用的MCP工具）
TOOL_WHITELIST = {
    "get_user_profile",
    "intelligent_exercise_selector",
    "contraindications_checker",
    "injury_risk_assessor",
    "muscle_group_volume_calculator",
    "tdee_calculator",
    "professional_program_designer",
    "exercise_alternative_finder",
    "movement_pattern_balancer",
    "intelligent_weight_calculator",
    "safe_exercise_modifier",
    "nutrition_intake_analyzer",
    "meal_plan_designer",
    "exercise_nutrition_optimization",
    "periodized_program_designer",
    "training_split_designer",
    "find_similar_training_cases",
    "query_knowledge_graph",
}


# =============================================================================
# 节点函数
# =============================================================================

async def agent_node(state: AgentState, *, llm_client, tool_schemas: list) -> Dict[str, Any]:
    """
    LLM决策节点

    将当前消息历史 + 可用工具schema 发送给LLM，
    LLM返回 tool_calls 或 最终文本回答。

    Args:
        state: 当前Agent状态
        llm_client: LLM客户端（需支持 chat with tools）
        tool_schemas: 可用工具的OpenAI function-calling schema列表
    """
    start = time.time()
    messages = state.get("messages", [])

    response = await llm_client.chat_with_tools(
        messages=messages,
        tools=tool_schemas,
        temperature=0.3,
    )

    elapsed = time.time() - start
    timings = dict(state.get("step_timings", {}))
    timings[f"agent_node_{state.get('tool_calls_count', 0)}"] = elapsed

    return {
        "messages": [response],
        "step_timings": timings,
    }


async def tool_node(state: AgentState, *, mcp_orchestrator) -> Dict[str, Any]:
    """
    工具执行节点

    从最后一条AI消息中提取 tool_calls，通过MCP编排器逐个执行，
    将结果作为 ToolMessage 追加到消息列表。

    Args:
        state: 当前Agent状态
        mcp_orchestrator: MCPOrchestrator 实例
    """
    from langchain_core.messages import ToolMessage

    start = time.time()
    messages = state.get("messages", [])
    last_msg = messages[-1]

    tool_calls = getattr(last_msg, "tool_calls", [])
    if not tool_calls:
        return {}

    new_messages = []
    results = list(state.get("tool_results", []))
    cost = state.get("total_cost", 0.0)
    count = state.get("tool_calls_count", 0)
    errors = list(state.get("errors", []))

    for tc in tool_calls:
        tool_name = tc["name"]
        tool_args = tc.get("args", {})
        call_id = tc["id"]

        # 注入 user_id
        if "user_id" not in tool_args:
            tool_args["user_id"] = state.get("user_id", "")

        try:
            t0 = time.time()
            result = await mcp_orchestrator.call_tool(
                mcp_server="python_internal",
                tool_name=tool_name,
                params=tool_args,
            )
            elapsed_tool = time.time() - t0

            results.append({
                "tool": tool_name,
                "args": tool_args,
                "result": result,
                "duration_s": round(elapsed_tool, 3),
            })
            new_messages.append(ToolMessage(
                content=str(result),
                tool_call_id=call_id,
                name=tool_name,
            ))
            # 粗略成本估算：每次工具调用 0.05 元
            cost += 0.05

        except Exception as e:
            logger.error(f"Tool {tool_name} failed: {e}")
            errors.append(f"{tool_name}: {e}")
            new_messages.append(ToolMessage(
                content=f"Error: {e}",
                tool_call_id=call_id,
                name=tool_name,
            ))

        count += 1

    elapsed = time.time() - start
    timings = dict(state.get("step_timings", {}))
    timings[f"tool_node_{count}"] = elapsed

    return {
        "messages": new_messages,
        "tool_calls_count": count,
        "total_cost": cost,
        "tool_results": results,
        "errors": errors,
        "step_timings": timings,
    }


async def safety_check_node(state: AgentState) -> Dict[str, Any]:
    """
    安全检查节点

    检查：
    1. 迭代次数是否超过 max_iterations
    2. 累计成本是否超过 cost_limit
    3. 最后一次工具调用是否在白名单内

    不修改状态，仅用于条件路由判断。
    """
    # 纯透传，路由逻辑在 should_continue 中
    return {}


# =============================================================================
# 条件路由函数
# =============================================================================

def should_use_tool(state: AgentState) -> Literal["safety_check", "end"]:
    """
    agent_node 之后的路由：
    - 如果LLM返回了 tool_calls → "safety_check"
    - 否则（纯文本回答）→ "end"
    """
    messages = state.get("messages", [])
    if not messages:
        return "end"

    last_msg = messages[-1]
    tool_calls = getattr(last_msg, "tool_calls", [])

    if tool_calls:
        return "safety_check"

    # 提取最终回答
    return "end"


def should_continue(state: AgentState) -> Literal["tools", "end"]:
    """
    safety_check_node 之后的路由：
    - 通过安全检查 → "tools"（执行工具）
    - 超过迭代/成本限制 → "end"（强制结束）
    - 工具不在白名单 → "end"
    """
    count = state.get("tool_calls_count", 0)
    max_iter = state.get("max_iterations", 5)
    cost = state.get("total_cost", 0.0)
    cost_limit = state.get("cost_limit", 2.0)

    if count >= max_iter:
        logger.warning(f"Agent reached max iterations ({max_iter}), forcing end")
        return "end"

    if cost >= cost_limit:
        logger.warning(f"Agent reached cost limit ({cost_limit}), forcing end")
        return "end"

    # 检查白名单
    messages = state.get("messages", [])
    if messages:
        last_msg = messages[-1]
        tool_calls = getattr(last_msg, "tool_calls", [])
        for tc in tool_calls:
            if tc["name"] not in TOOL_WHITELIST:
                logger.warning(f"Tool {tc['name']} not in whitelist, blocking")
                return "end"

    return "tools"
