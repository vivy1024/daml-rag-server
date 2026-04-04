# -*- coding: utf-8 -*-
"""
Harness v1 — 确定性执行壳层

提供策略层、上下文包、验证器等核心组件。
通过 HarnessConfig feature flag 灰度启用。
"""

from .execution_policy import ExecutionPolicy, PolicyDecisionRecord, TemplateRiskLevel
from .context_packet_builder import ContextPacketBuilder, ContextPacket, ContextLayer
from .output_verifier import OutputVerifier, VerificationResult

__all__ = [
    # REQ-2: 执行策略
    "ExecutionPolicy",
    "PolicyDecisionRecord",
    "TemplateRiskLevel",
    # REQ-3: 上下文包
    "ContextPacketBuilder",
    "ContextPacket",
    "ContextLayer",
    # REQ-6: 输出校验
    "OutputVerifier",
    "VerificationResult",
]
