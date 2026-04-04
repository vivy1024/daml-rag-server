# -*- coding: utf-8 -*-
"""
Harness 追踪器 — REQ-7

在 harness 管道每个阶段产生结构化 trace 日志，
用于性能分析、回归评估和调试。

版本: v1.0.0
日期: 2026-04-04
"""

import logging
import time
import uuid
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


@dataclass
class HarnessTrace:
    """完整的 harness 执行追踪"""
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    user_id: str = ""
    template_selected: str = ""

    # 各阶段结果
    policy_decisions: List[Dict[str, Any]] = field(default_factory=list)
    resources_read: List[str] = field(default_factory=list)
    context_packet_version: str = ""
    context_token_usage: Dict[str, int] = field(default_factory=dict)
    tools_executed: List[Dict[str, Any]] = field(default_factory=list)
    verifier_result: Optional[Dict[str, Any]] = None

    # 计时
    stage_durations_ms: Dict[str, float] = field(default_factory=dict)
    total_duration_ms: float = 0

    # 结果
    output_rendered: bool = False
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "timestamp": self.timestamp,
            "user_id": self.user_id,
            "template_selected": self.template_selected,
            "policy_decisions": self.policy_decisions,
            "resources_read": self.resources_read,
            "context_packet_version": self.context_packet_version,
            "context_token_usage": self.context_token_usage,
            "tools_executed": self.tools_executed,
            "verifier_result": self.verifier_result,
            "stage_durations_ms": self.stage_durations_ms,
            "total_duration_ms": self.total_duration_ms,
            "output_rendered": self.output_rendered,
            "error": self.error,
        }


class HarnessTracer:
    """
    Harness 追踪器

    记录管道执行的每个阶段，产出结构化 trace。
    通过 HarnessConfig.tracer_enabled 控制。
    """

    def __init__(self):
        self._current_trace: Optional[HarnessTrace] = None
        self._stage_start: float = 0
        self._total_start: float = 0

    def start_trace(self, user_id: str, template_id: str = "") -> HarnessTrace:
        """开始新的追踪"""
        self._current_trace = HarnessTrace(
            user_id=user_id,
            template_selected=template_id,
        )
        self._total_start = time.monotonic()
        logger.debug(f"🔍 Trace 开始: {self._current_trace.trace_id}")
        return self._current_trace

    def start_stage(self, stage_name: str):
        """标记阶段开始"""
        self._stage_start = time.monotonic()

    def end_stage(self, stage_name: str):
        """标记阶段结束并记录耗时"""
        if self._current_trace is None:
            return
        duration = (time.monotonic() - self._stage_start) * 1000
        self._current_trace.stage_durations_ms[stage_name] = round(duration, 2)

    def record_policy(self, decisions: List[Dict[str, Any]]):
        """记录策略判定"""
        if self._current_trace:
            self._current_trace.policy_decisions.extend(decisions)

    def record_resources(self, resources: List[str]):
        """记录读取的资源"""
        if self._current_trace:
            self._current_trace.resources_read.extend(resources)

    def record_context_packet(self, version: str, token_usage: Dict[str, int]):
        """记录上下文包信息"""
        if self._current_trace:
            self._current_trace.context_packet_version = version
            self._current_trace.context_token_usage = token_usage

    def record_tool_execution(self, tool_name: str, duration_ms: float, success: bool):
        """记录工具执行"""
        if self._current_trace:
            self._current_trace.tools_executed.append({
                "tool": tool_name,
                "duration_ms": round(duration_ms, 2),
                "success": success,
            })

    def record_verifier(self, result: Dict[str, Any]):
        """记录验证器结果"""
        if self._current_trace:
            self._current_trace.verifier_result = result

    def end_trace(self, output_rendered: bool = True, error: Optional[str] = None) -> Optional[HarnessTrace]:
        """
        结束追踪，输出最终 trace

        Args:
            output_rendered: 是否成功渲染输出
            error: 错误信息

        Returns:
            完成的 HarnessTrace
        """
        if self._current_trace is None:
            return None

        self._current_trace.total_duration_ms = round(
            (time.monotonic() - self._total_start) * 1000, 2
        )
        self._current_trace.output_rendered = output_rendered
        self._current_trace.error = error

        trace = self._current_trace
        self._current_trace = None

        # 输出结构化日志
        logger.info(
            f"📊 Trace 完成: id={trace.trace_id}, "
            f"template={trace.template_selected}, "
            f"duration={trace.total_duration_ms}ms, "
            f"tools={len(trace.tools_executed)}, "
            f"rendered={trace.output_rendered}"
        )

        return trace
