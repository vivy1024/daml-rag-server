# -*- coding: utf-8 -*-
"""
skill_execute 节点 — Skill 工具链执行

职责：
- 加载 SkillDefinition
- 设置 ToolAllowlist
- 使用 SkillExecutor 执行工具链
- 记录到 HarnessTracer
- 返回 tool_results

版本: v2.0.0
日期: 2026-05-09
"""

import logging
from typing import Dict, Any

from src.skills.manager import SkillManager
from src.skills.executor import SkillExecutor, ExecutionResult
from src.harness_v2.tool_allowlist import ToolAllowlist
from src.harness_v2.harness_tracer import HarnessTracerV2
from ..state import AgentState

logger = logging.getLogger(__name__)

# 模块级依赖
_skill_manager: SkillManager | None = None
_skill_executor: SkillExecutor | None = None
_tool_allowlist: ToolAllowlist | None = None
_harness_tracer: HarnessTracerV2 | None = None
_tool_registry: Any = None


def configure_skill_execute(
    manager: SkillManager,
    executor: SkillExecutor,
    allowlist: ToolAllowlist,
    tracer: HarnessTracerV2,
    tool_registry: Any = None,
) -> None:
    """配置 skill_execute 节点依赖

    Args:
        manager: SkillManager 实例
        executor: SkillExecutor 实例
        allowlist: ToolAllowlist 实例
        tracer: HarnessTracerV2 实例
        tool_registry: 工具注册表（实现 call_tool 方法）
    """
    global _skill_manager, _skill_executor, _tool_allowlist, _harness_tracer, _tool_registry
    _skill_manager = manager
    _skill_executor = executor
    _tool_allowlist = allowlist
    _harness_tracer = tracer
    _tool_registry = tool_registry


async def skill_execute(state: AgentState) -> Dict[str, Any]:
    """Skill 工具链执行节点

    加载选中的 SkillDefinition，设置 ToolAllowlist，
    通过 SkillExecutor 执行工具链，并记录到 HarnessTracer。

    Args:
        state: 当前 Agent 状态

    Returns:
        状态更新字典（包含 tool_results）
    """
    current_skill = state.get("current_skill")

    # 如果没有 Skill（direct_reply 路径），跳过
    if not current_skill:
        return {}

    if not _skill_manager or not _skill_executor:
        logger.error("skill_execute: 依赖未配置")
        return {"error": "skill_execute 依赖未配置"}

    if not _tool_registry:
        logger.error("skill_execute: tool_registry 未配置")
        return {"error": "skill_execute tool_registry 未配置"}

    # 加载 Skill 定义
    try:
        skill_def = _skill_manager.get(current_skill)
    except Exception as e:
        logger.error(f"skill_execute: 加载 Skill [{current_skill}] 失败: {e}")
        return {"error": f"Skill [{current_skill}] 不存在"}

    # 设置 ToolAllowlist
    allowlist = _tool_allowlist or ToolAllowlist()
    allowlist.set_skill_context(
        skill_id=skill_def.id,
        required_tools=skill_def.required_tools,
        optional_tools=skill_def.optional_tools,
    )

    # 记录到 HarnessTracer
    tracer = _harness_tracer or HarnessTracerV2()
    tracer.start_trace(
        request_id=state.get("thread_id", ""),
        user_id=state.get("user_id", ""),
        thread_id=state.get("thread_id", ""),
    )
    tracer.record_skill_select(skill_id=skill_def.id, reason=state.get("skill_reason", ""))

    # 执行工具链
    try:
        user_profile = state.get("user_profile") or {}
        exec_state = {"user_profile": user_profile}

        result: ExecutionResult = await _skill_executor.execute(
            skill=skill_def,
            state=exec_state,
            tool_registry=_tool_registry,
        )

        # 记录工具执行事件
        for tool_name, tool_result in result.tool_results.items():
            tracer.record_tool_execute(
                tool_name=tool_name,
                success=tool_result.success,
                duration_ms=tool_result.duration_ms,
            )

        logger.info(
            f"skill_execute: Skill [{current_skill}] 执行完成, "
            f"success={result.success}, tools={len(result.tool_results)}"
        )

        # 构建 tool_results dict
        tool_results_dict: Dict[str, Any] = {}
        for tool_name, tool_result in result.tool_results.items():
            tool_results_dict[tool_name] = {
                "success": tool_result.success,
                "data": tool_result.data,
                "error": tool_result.error,
                "duration_ms": tool_result.duration_ms,
            }

        return {"tool_results": tool_results_dict}

    except Exception as e:
        logger.error(f"skill_execute: 执行异常: {e}")
        return {"error": f"Skill 执行失败: {e}"}
