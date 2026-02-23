# -*- coding: utf-8 -*-
"""
LangGraph Agent 节点定义（Skills 版）

三个核心节点：
1. agent_node - LLM决策（调用 Skills/工具 or 最终回答）
2. tool_node - 执行 load_skill 或 MCP 工具
3. safety_check_node - 迭代/成本/白名单检查

两个条件函数：
- should_use_tool - agent_node 后判断是否需要调用工具
- should_continue - safety_check_node 后判断是否继续循环

版本: v2.0.0 — Skills 架构接入
日期: 2026-02-19
"""

import logging
import time
from typing import Dict, Any, Literal

from .state import AgentState

logger = logging.getLogger(__name__)

# 工具白名单：load_skill + 辅助工具 + DAG 内 MCP 工具
TOOL_WHITELIST = {
    # Skills 核心
    "load_skill",
    # 辅助（信息收集，不属于任何 Skill）
    "get_user_profile",
    "query_knowledge_graph",
    # DAG 模板内的 MCP 工具（Skill 执行时需要）
    "intelligent_exercise_selector",
    "contraindications_checker",
    "postural_assessor",
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
}


# =============================================================================
# 节点函数
# =============================================================================

async def agent_node(state: AgentState, *, llm_client, tool_schemas: list) -> Dict[str, Any]:
    """
    LLM决策节点

    v2.0: tool_schemas 包含 load_skill + 辅助工具，
    LLM 优先调用 load_skill 获取 Skill 详情。

    v2.1: 首次调用使用 tool_choice="required" 强制触发 FC，
    后续循环使用 "auto" 让 LLM 自行决策。
    """
    start = time.time()
    messages = state.get("messages", [])
    call_count = state.get("tool_calls_count", 0)

    # 首次调用强制使用工具，后续循环让 LLM 自行决策
    tool_choice = "required" if call_count == 0 and tool_schemas else "auto"

    response = await llm_client.chat_with_tools(
        messages=messages,
        tools=tool_schemas,
        temperature=0.3,
        tool_choice=tool_choice,
    )

    elapsed = time.time() - start
    timings = dict(state.get("step_timings", {}))
    timings[f"agent_node_{state.get('tool_calls_count', 0)}"] = elapsed

    return {
        "messages": [response],
        "step_timings": timings,
    }


async def tool_node(
    state: AgentState,
    *,
    mcp_orchestrator,
    skill_manager=None,
) -> Dict[str, Any]:
    """
    工具执行节点（Skills 版）

    v2.0 变化：
    - load_skill 调用直接走 SkillManager，不经过 MCP
    - 其他工具仍走 MCP 编排器
    - load_skill 不计入成本（只是加载元数据）
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
    skills_loaded = list(state.get("skills_loaded", []))

    for tc in tool_calls:
        tool_name = tc["name"]
        tool_args = tc.get("args", {})
        call_id = tc["id"]

        # ── load_skill 特殊处理：直接走 SkillManager ──
        if tool_name == "load_skill" and skill_manager:
            skill_id = tool_args.get("skill_id", "")
            t0 = time.time()
            content = skill_manager.load_skill(skill_id)
            elapsed_tool = time.time() - t0

            skills_loaded.append(skill_id)
            results.append({
                "tool": "load_skill",
                "args": {"skill_id": skill_id},
                "result": {"loaded": not content.startswith("错误")},
                "duration_s": round(elapsed_tool, 3),
            })
            new_messages.append(ToolMessage(
                content=content,
                tool_call_id=call_id,
                name="load_skill",
            ))
            # load_skill 不计入成本和迭代次数
            logger.info(f"📖 load_skill: {skill_id} ({elapsed_tool:.3f}s)")
            continue

        # ── 普通 MCP 工具 ──
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
        "skills_loaded": skills_loaded,
    }


async def safety_check_node(state: AgentState) -> Dict[str, Any]:
    """安全检查节点（路由逻辑在 should_continue 中）"""
    return {}


# =============================================================================
# 条件路由函数
# =============================================================================

def should_use_tool(state: AgentState) -> Literal["safety_check", "end"]:
    """agent_node 后：有 tool_calls → safety_check，否则 → end"""
    messages = state.get("messages", [])
    if not messages:
        return "end"

    last_msg = messages[-1]
    tool_calls = getattr(last_msg, "tool_calls", [])

    if tool_calls:
        return "safety_check"

    return "end"


def should_continue(state: AgentState) -> Literal["tools", "end"]:
    """
    safety_check 后的路由

    v2.0: load_skill 始终放行（不受迭代/成本限制）
    """
    count = state.get("tool_calls_count", 0)
    max_iter = state.get("max_iterations", 5)
    cost = state.get("total_cost", 0.0)
    cost_limit = state.get("cost_limit", 2.0)

    messages = state.get("messages", [])
    if messages:
        last_msg = messages[-1]
        tool_calls = getattr(last_msg, "tool_calls", [])

        # load_skill 始终放行
        if tool_calls and all(tc["name"] == "load_skill" for tc in tool_calls):
            return "tools"

        for tc in tool_calls:
            if tc["name"] not in TOOL_WHITELIST:
                logger.warning(f"Tool {tc['name']} not in whitelist, blocking")
                return "end"

    if count >= max_iter:
        logger.warning(f"Agent reached max iterations ({max_iter}), forcing end")
        return "end"

    if cost >= cost_limit:
        logger.warning(f"Agent reached cost limit ({cost_limit}), forcing end")
        return "end"

    return "tools"
