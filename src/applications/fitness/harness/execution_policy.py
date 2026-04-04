# -*- coding: utf-8 -*-
"""
执行策略层 — REQ-2

在 DAG 模板执行管道中插入确定性检查点，实现 fail-closed 安全策略。
根据模板风险等级（由 complexity_level 映射）决定必须执行的 guard 工具。

检查点：
1. pre_template: 模板选择后、DAG 执行前
2. pre_tool: 每个工具执行前（预留，当前仅日志）
3. pre_output: DAG 结果渲染给用户前

核心原则：
- health_conditions 非空时，高风险模板必须执行 contraindications_checker + injury_risk_assessor
- guard 未执行或失败 → 阻止执行（fail-closed）
- 每次判定产生结构化 PolicyDecisionRecord

版本: v1.0.0
日期: 2026-04-04
"""

import logging
from typing import Dict, Any, Optional, List, Set
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class TemplateRiskLevel(Enum):
    """模板风险等级 — 由 DAGTemplate.complexity_level 映射"""
    HIGH = "high"        # complexity_level=3
    MEDIUM = "medium"    # complexity_level=2
    LOW = "low"          # complexity_level=1


# complexity_level → TemplateRiskLevel
_COMPLEXITY_TO_RISK = {
    3: TemplateRiskLevel.HIGH,
    2: TemplateRiskLevel.MEDIUM,
    1: TemplateRiskLevel.LOW,
}

# 各风险等级必须执行的 guard 工具
REQUIRED_GUARDS: Dict[TemplateRiskLevel, List[str]] = {
    TemplateRiskLevel.HIGH: ["contraindications_checker", "injury_risk_assessor"],
    TemplateRiskLevel.MEDIUM: ["contraindications_checker"],
    TemplateRiskLevel.LOW: [],
}


@dataclass
class PolicyDecisionRecord:
    """策略判定记录"""
    checkpoint: str                  # pre_template / pre_tool / pre_output
    request_object: str              # 模板ID 或工具名
    decision: str                    # allow / deny / warn
    reason: str                      # 判定原因
    risk_level: str = ""             # high / medium / low
    guards_required: List[str] = field(default_factory=list)
    guards_present: List[str] = field(default_factory=list)
    guards_missing: List[str] = field(default_factory=list)
    user_has_conditions: bool = False
    fallback_action: Optional[str] = None  # None / "degrade" / "clarify"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "checkpoint": self.checkpoint,
            "request_object": self.request_object,
            "decision": self.decision,
            "reason": self.reason,
            "risk_level": self.risk_level,
            "guards_required": self.guards_required,
            "guards_missing": self.guards_missing,
            "user_has_conditions": self.user_has_conditions,
            "fallback_action": self.fallback_action,
        }


class ExecutionPolicy:
    """
    统一执行策略层

    在 DAG 模板执行管道的关键节点插入确定性检查，
    确保高风险操作在缺少安全 guard 时被阻止。
    """

    def __init__(self):
        self._decision_log: List[PolicyDecisionRecord] = []

    @property
    def decisions(self) -> List[PolicyDecisionRecord]:
        """获取本次会话的所有策略判定"""
        return self._decision_log

    def clear_decisions(self):
        """清空判定记录（新请求开始时调用）"""
        self._decision_log.clear()

    # ================================================================
    # Checkpoint 1: pre_template
    # ================================================================

    def check_pre_template(
        self,
        template_id: str,
        complexity_level: int,
        required_tools: List[str],
        user_profile: Dict[str, Any],
    ) -> PolicyDecisionRecord:
        """
        模板执行前检查

        fail-closed 逻辑：
        - 用户有 health_conditions → 必须包含对应 guard 工具
        - guard 不在 required_tools 中 → deny

        Args:
            template_id: 模板ID
            complexity_level: DAGTemplate.complexity_level (1-3)
            required_tools: DAGTemplate.required_tools
            user_profile: 用户档案字典

        Returns:
            PolicyDecisionRecord
        """
        risk_level = _COMPLEXITY_TO_RISK.get(complexity_level, TemplateRiskLevel.LOW)
        guards_required = REQUIRED_GUARDS.get(risk_level, [])
        tools_set = set(required_tools)

        # 检查用户是否有健康状况
        health_conditions = self._extract_health_conditions(user_profile)
        has_conditions = len(health_conditions) > 0

        # 计算缺失的 guard
        guards_present = [g for g in guards_required if g in tools_set]
        guards_missing = [g for g in guards_required if g not in tools_set]

        # 核心判定逻辑
        if has_conditions and guards_missing:
            # fail-closed: 用户有健康状况但模板缺少必要 guard
            record = PolicyDecisionRecord(
                checkpoint="pre_template",
                request_object=template_id,
                decision="deny",
                reason=f"用户有健康状况 ({', '.join(health_conditions[:3])}), "
                       f"但模板缺少必要安全检查: {', '.join(guards_missing)}",
                risk_level=risk_level.value,
                guards_required=guards_required,
                guards_present=guards_present,
                guards_missing=guards_missing,
                user_has_conditions=True,
                fallback_action="degrade",
            )
            logger.warning(
                f"🚫 策略拒绝: template={template_id}, "
                f"risk={risk_level.value}, missing_guards={guards_missing}"
            )
        elif not has_conditions and guards_missing and risk_level == TemplateRiskLevel.HIGH:
            # 即使无健康状况，高风险模板缺 guard 也发出警告（但放行）
            record = PolicyDecisionRecord(
                checkpoint="pre_template",
                request_object=template_id,
                decision="warn",
                reason=f"高风险模板缺少 guard: {', '.join(guards_missing)}, "
                       f"用户暂无已知健康状况，允许执行但建议补充安全检查",
                risk_level=risk_level.value,
                guards_required=guards_required,
                guards_present=guards_present,
                guards_missing=guards_missing,
                user_has_conditions=False,
            )
            logger.info(
                f"⚠️ 策略警告: template={template_id}, "
                f"missing_guards={guards_missing} (无健康状况, 放行)"
            )
        else:
            # 通过
            record = PolicyDecisionRecord(
                checkpoint="pre_template",
                request_object=template_id,
                decision="allow",
                reason="安全检查通过",
                risk_level=risk_level.value,
                guards_required=guards_required,
                guards_present=guards_present,
                guards_missing=[],
                user_has_conditions=has_conditions,
            )
            logger.debug(f"✅ 策略通过: template={template_id}, risk={risk_level.value}")

        self._decision_log.append(record)
        return record

    # ================================================================
    # Checkpoint 2: pre_tool
    # ================================================================

    def check_pre_tool(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
    ) -> PolicyDecisionRecord:
        """
        工具执行前检查（预留扩展点）

        当前仅记录日志，不做阻止。
        后续可添加：
        - 工具输入验证
        - 敏感数据脱敏
        - 调用频率限制

        Args:
            tool_name: 工具名称
            tool_input: 工具输入参数

        Returns:
            PolicyDecisionRecord (always allow)
        """
        record = PolicyDecisionRecord(
            checkpoint="pre_tool",
            request_object=tool_name,
            decision="allow",
            reason="工具检查通过（预留扩展）",
        )
        self._decision_log.append(record)
        return record

    # ================================================================
    # Checkpoint 3: pre_output
    # ================================================================

    def check_pre_output(
        self,
        template_id: str,
        dag_results: Dict[str, Any],
        user_profile: Dict[str, Any],
    ) -> PolicyDecisionRecord:
        """
        输出渲染前检查

        验证 DAG 执行结果中安全 guard 是否实际产出了结果。
        如果模板声明了 contraindications_checker 但结果中无此工具输出，
        说明 guard 执行失败或被跳过 → deny。

        Args:
            template_id: 模板ID
            dag_results: DAG 执行结果字典 (tool_name → result)
            user_profile: 用户档案

        Returns:
            PolicyDecisionRecord
        """
        health_conditions = self._extract_health_conditions(user_profile)
        has_conditions = len(health_conditions) > 0

        if not has_conditions:
            record = PolicyDecisionRecord(
                checkpoint="pre_output",
                request_object=template_id,
                decision="allow",
                reason="用户无已知健康状况，跳过输出安全检查",
                user_has_conditions=False,
            )
            self._decision_log.append(record)
            return record

        # 检查 guard 工具是否在结果中有输出
        expected_guards = ["contraindications_checker", "injury_risk_assessor"]
        executed_guards = [g for g in expected_guards if g in dag_results and dag_results[g]]
        missing_guards = [g for g in expected_guards if g not in dag_results or not dag_results[g]]

        if missing_guards:
            record = PolicyDecisionRecord(
                checkpoint="pre_output",
                request_object=template_id,
                decision="deny",
                reason=f"安全 guard 未产出结果: {', '.join(missing_guards)}, "
                       f"用户有健康状况，禁止输出未经安全验证的方案",
                guards_required=expected_guards,
                guards_present=executed_guards,
                guards_missing=missing_guards,
                user_has_conditions=True,
                fallback_action="clarify",
            )
            logger.warning(
                f"🚫 输出被拒: template={template_id}, "
                f"missing_guard_results={missing_guards}"
            )
        else:
            record = PolicyDecisionRecord(
                checkpoint="pre_output",
                request_object=template_id,
                decision="allow",
                reason="所有安全 guard 已执行并产出结果",
                guards_required=expected_guards,
                guards_present=executed_guards,
                guards_missing=[],
                user_has_conditions=True,
            )
            logger.debug(f"✅ 输出检查通过: template={template_id}")

        self._decision_log.append(record)
        return record

    # ================================================================
    # 辅助方法
    # ================================================================

    @staticmethod
    def _extract_health_conditions(user_profile: Dict[str, Any]) -> List[str]:
        """
        从用户档案提取健康状况列表

        兼容多种数据格式：
        - user_profile["health_conditions"] (List[str])
        - user_profile["medical_history"] (str 或 List)
        - user_profile["injuries"] (List[str])
        """
        conditions = []

        # 主要字段
        hc = user_profile.get("health_conditions", [])
        if isinstance(hc, list):
            conditions.extend(hc)
        elif isinstance(hc, str) and hc.strip():
            conditions.append(hc.strip())

        # 医疗历史
        mh = user_profile.get("medical_history", [])
        if isinstance(mh, list):
            conditions.extend(mh)
        elif isinstance(mh, str) and mh.strip():
            conditions.append(mh.strip())

        # 伤病
        injuries = user_profile.get("injuries", [])
        if isinstance(injuries, list):
            conditions.extend(injuries)
        elif isinstance(injuries, str) and injuries.strip():
            conditions.append(injuries.strip())

        # 去重
        return list(set(c for c in conditions if c))

    @staticmethod
    def get_risk_level(complexity_level: int) -> TemplateRiskLevel:
        """复杂度 → 风险等级"""
        return _COMPLEXITY_TO_RISK.get(complexity_level, TemplateRiskLevel.LOW)
