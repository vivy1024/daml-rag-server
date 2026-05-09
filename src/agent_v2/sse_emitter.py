# -*- coding: utf-8 -*-
"""
SSE 流式输出 — Agent v2 事件流

定义 SSE 事件类型，提供 async generator 将 Agent 执行过程
转换为 Server-Sent Events 流。

版本: v2.0.0
日期: 2026-05-09
"""

import json
import logging
from enum import Enum
from typing import Any, AsyncGenerator, Dict, Optional

logger = logging.getLogger(__name__)


class SSEEventType(str, Enum):
    """SSE 事件类型枚举"""
    SKILL_STARTED = "skill_started"
    TOOL_EXECUTING = "tool_executing"
    TOOL_COMPLETED = "tool_completed"
    APPROVAL_REQUIRED = "approval_required"
    CONTENT = "content"
    DONE = "done"
    ERROR = "error"


def emit_event(event_type: SSEEventType, data: Any) -> str:
    """格式化为 SSE 文本

    Args:
        event_type: 事件类型
        data: 事件数据（将被 JSON 序列化）

    Returns:
        SSE 格式文本（event: xxx\\ndata: xxx\\n\\n）
    """
    if isinstance(data, str):
        payload = data
    else:
        payload = json.dumps(data, ensure_ascii=False)

    return f"event: {event_type.value}\ndata: {payload}\n\n"


async def stream_agent_response(
    graph,
    input_state: Dict[str, Any],
    config: Optional[Dict[str, Any]] = None,
) -> AsyncGenerator[str, None]:
    """流式输出 Agent 执行过程

    将 Agent Graph 的执行过程转换为 SSE 事件流。
    每个节点执行完成后 yield 对应的 SSE 事件。

    Args:
        graph: 编译后的 LangGraph CompiledGraph
        input_state: 输入状态
        config: LangGraph 配置（包含 thread_id 等）

    Yields:
        SSE 格式文本
    """
    run_config = config or {}

    try:
        async for event in graph.astream(input_state, config=run_config):
            # LangGraph astream 返回 {node_name: state_update} 格式
            for node_name, state_update in event.items():
                if node_name == "init_thread":
                    # 初始化完成，不发送事件
                    continue

                elif node_name == "skill_select":
                    skill_id = state_update.get("current_skill")
                    if skill_id:
                        yield emit_event(
                            SSEEventType.SKILL_STARTED,
                            {"skill_id": skill_id, "reason": state_update.get("skill_reason", "")},
                        )

                elif node_name == "safety_check":
                    approval = state_update.get("approval_status")
                    if approval == "pending":
                        yield emit_event(
                            SSEEventType.APPROVAL_REQUIRED,
                            {"reason": state_update.get("skill_reason", "需要确认")},
                        )

                elif node_name == "skill_execute":
                    tool_results = state_update.get("tool_results", {})
                    for tool_name, result in tool_results.items():
                        yield emit_event(
                            SSEEventType.TOOL_COMPLETED,
                            {
                                "tool_name": tool_name,
                                "success": result.get("success", False),
                                "duration_ms": result.get("duration_ms", 0),
                            },
                        )

                elif node_name == "output_generate":
                    final_output = state_update.get("final_output", "")
                    if final_output:
                        yield emit_event(SSEEventType.CONTENT, {"text": final_output})

                elif node_name == "record":
                    # 追踪完成
                    pass

        # 流结束
        yield emit_event(SSEEventType.DONE, {"status": "completed"})

    except Exception as e:
        logger.error(f"stream_agent_response: 流式输出异常: {e}")
        yield emit_event(SSEEventType.ERROR, {"message": str(e)})
