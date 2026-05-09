# -*- coding: utf-8 -*-
"""
HarnessTracer v2 — 结构化决策链追踪

记录 Skills-first Agent 执行过程中的所有安全决策：
- Skill 选择
- PreSkillPolicy 判定
- ToolAllowlist 检查
- OutputVerifier 结果
- HITL interrupt/resume

对应需求：REQ-3（Harness v2）+ REQ-1.6（记录+评测采集）
版本: v2.0.0
日期: 2026-05-09
"""

import logging
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class TraceEvent:
    """单个追踪事件"""
    timestamp: float
    phase: str  # skill_select / pre_skill_policy / tool_allowlist / tool_execute / output_verify / hitl
    action: str  # 具体动作描述
    result: str  # allow / deny / warn / interrupt / resume
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HarnessTrace:
    """完整的 Harness 追踪记录"""
    request_id: str
    user_id: str
    thread_id: str
    skill_id: str = ""
    started_at: float = 0.0
    ended_at: float = 0.0
    events: List[TraceEvent] = field(default_factory=list)
    final_status: str = ""  # completed / degraded / denied / interrupted

    @property
    def duration_ms(self) -> float:
        if self.ended_at and self.started_at:
            return (self.ended_at - self.started_at) * 1000
        return 0.0

    @property
    def policy_denials(self) -> List[TraceEvent]:
        return [e for e in self.events if e.result == "deny"]

    @property
    def tools_executed(self) -> List[str]:
        return [
            e.details.get("tool_name", "")
            for e in self.events
            if e.phase == "tool_execute" and e.result == "allow"
        ]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "user_id": self.user_id,
            "thread_id": self.thread_id,
            "skill_id": self.skill_id,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "duration_ms": round(self.duration_ms, 1),
            "final_status": self.final_status,
            "event_count": len(self.events),
            "policy_denials": len(self.policy_denials),
            "tools_executed": self.tools_executed,
            "events": [
                {
                    "timestamp": e.timestamp,
                    "phase": e.phase,
                    "action": e.action,
                    "result": e.result,
                    "details": e.details,
                }
                for e in self.events
            ],
        }


class HarnessTracerV2:
    """
    Harness 追踪器 v2

    在 Agent 执行全程记录安全决策链，供：
    - 调试：追溯为什么某个工具被拒绝
    - 评测：分析安全策略的覆盖率和误报率
    - 审计：证明高风险操作经过了安全检查
    """

    def __init__(self):
        self._current_trace: Optional[HarnessTrace] = None

    def start_trace(
        self,
        request_id: str,
        user_id: str,
        thread_id: str,
    ) -> HarnessTrace:
        """开始新的追踪"""
        self._current_trace = HarnessTrace(
            request_id=request_id,
            user_id=user_id,
            thread_id=thread_id,
            started_at=time.time(),
        )
        logger.debug(f"📝 HarnessTracer: 开始追踪 request={request_id}")
        return self._current_trace

    def record_skill_select(self, skill_id: str, reason: str):
        """记录 Skill 选择"""
        if not self._current_trace:
            return
        self._current_trace.skill_id = skill_id
        self._current_trace.events.append(TraceEvent(
            timestamp=time.time(),
            phase="skill_select",
            action=f"选择 Skill: {skill_id}",
            result="allow",
            details={"skill_id": skill_id, "reason": reason},
        ))

    def record_policy_check(self, policy_result: Dict[str, Any]):
        """记录 PreSkillPolicy 检查结果"""
        if not self._current_trace:
            return
        result = "allow" if policy_result.get("allowed") else "deny"
        self._current_trace.events.append(TraceEvent(
            timestamp=time.time(),
            phase="pre_skill_policy",
            action=f"安全策略: {policy_result.get('action', 'unknown')}",
            result=result,
            details=policy_result,
        ))

    def record_tool_allowlist(self, tool_name: str, allowed: bool, reason: str = ""):
        """记录工具权限检查"""
        if not self._current_trace:
            return
        self._current_trace.events.append(TraceEvent(
            timestamp=time.time(),
            phase="tool_allowlist",
            action=f"工具权限: {tool_name}",
            result="allow" if allowed else "deny",
            details={"tool_name": tool_name, "reason": reason},
        ))

    def record_tool_execute(
        self, tool_name: str, success: bool, duration_ms: float = 0
    ):
        """记录工具执行"""
        if not self._current_trace:
            return
        self._current_trace.events.append(TraceEvent(
            timestamp=time.time(),
            phase="tool_execute",
            action=f"执行工具: {tool_name}",
            result="allow" if success else "error",
            details={
                "tool_name": tool_name,
                "success": success,
                "duration_ms": round(duration_ms, 1),
            },
        ))

    def record_output_verify(self, verification_result: Dict[str, Any]):
        """记录输出校验结果"""
        if not self._current_trace:
            return
        passed = verification_result.get("passed", False)
        self._current_trace.events.append(TraceEvent(
            timestamp=time.time(),
            phase="output_verify",
            action=f"输出校验: {'通过' if passed else '未通过'}",
            result="allow" if passed else "warn",
            details=verification_result,
        ))

    def record_hitl(self, action: str, user_response: Optional[bool] = None):
        """记录 HITL 事件"""
        if not self._current_trace:
            return
        if action == "interrupt":
            result = "interrupt"
        elif user_response is True:
            result = "resume"
        elif user_response is False:
            result = "deny"
        else:
            result = "interrupt"

        self._current_trace.events.append(TraceEvent(
            timestamp=time.time(),
            phase="hitl",
            action=f"HITL: {action}",
            result=result,
            details={"action": action, "user_response": user_response},
        ))

    def end_trace(self, final_status: str = "completed") -> Optional[HarnessTrace]:
        """结束追踪，返回完整 trace"""
        if not self._current_trace:
            return None

        self._current_trace.ended_at = time.time()
        self._current_trace.final_status = final_status

        trace = self._current_trace
        self._current_trace = None

        logger.info(
            f"📝 HarnessTracer: 追踪完成 request={trace.request_id}, "
            f"skill={trace.skill_id}, status={final_status}, "
            f"events={len(trace.events)}, duration={trace.duration_ms:.0f}ms"
        )

        return trace

    @property
    def current_trace(self) -> Optional[HarnessTrace]:
        """获取当前进行中的 trace"""
        return self._current_trace
