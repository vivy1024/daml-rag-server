# -*- coding: utf-8 -*-
"""
record 节点 — 追踪记录收尾

职责：
- 结束 HarnessTracer
- 构建 trace dict
- 设置 state.harness_trace
- 评测采集暂时只记录，不实际推送

版本: v2.0.0
日期: 2026-05-09
"""

import logging
from typing import Dict, Any

from src.harness_v2.harness_tracer import HarnessTracerV2
from ..state import AgentState

logger = logging.getLogger(__name__)

# 模块级依赖
_harness_tracer: HarnessTracerV2 | None = None


def configure_record(tracer: HarnessTracerV2) -> None:
    """配置 record 节点依赖

    Args:
        tracer: HarnessTracerV2 实例
    """
    global _harness_tracer
    _harness_tracer = tracer


async def record(state: AgentState) -> Dict[str, Any]:
    """追踪记录收尾节点

    结束 HarnessTracer，构建 trace dict 并写入 state。
    评测采集暂时只记录到日志，不实际推送到外部系统。

    Args:
        state: 当前 Agent 状态

    Returns:
        状态更新字典（包含 harness_trace）
    """
    tracer = _harness_tracer

    if not tracer:
        logger.debug("record: HarnessTracer 未配置，跳过")
        return {"harness_trace": {}}

    # 确定最终状态
    final_status = _determine_final_status(state)

    # 结束追踪
    trace = tracer.end_trace(final_status=final_status)

    if trace:
        trace_dict = trace.to_dict()
        logger.info(
            f"📝 record: 追踪完成, skill={trace.skill_id}, "
            f"status={final_status}, duration={trace.duration_ms:.0f}ms"
        )
        # TODO: 评测采集 — 推送到评测系统
        return {"harness_trace": trace_dict}

    return {"harness_trace": {}}


def _determine_final_status(state: AgentState) -> str:
    """根据 state 确定最终状态

    Args:
        state: 当前 Agent 状态

    Returns:
        最终状态字符串
    """
    if state.get("error"):
        return "error"
    if state.get("approval_status") == "denied":
        return "denied"
    if state.get("direct_reply") and not state.get("current_skill"):
        return "direct_reply"
    if state.get("final_output"):
        return "completed"
    return "unknown"
