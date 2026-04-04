# -*- coding: utf-8 -*-
"""
输出校验器 — REQ-6

在 DAG 执行完成后、LLM 综合前，对工具结果进行 5 维度确定性校验。
全部校验为纯 Python 逻辑，不调用 LLM，确保确定性和低延迟。

校验维度：
1. safety_conflict:     计划动作 vs hard_constraints
2. equipment_mismatch:  计划器械 vs 用户可用器械
3. duration_exceeded:   估算总时长 vs 用户可用时间
4. volume_overload:     总组数 vs MAV 上限
5. goal_mismatch:       计划类型 vs 用户训练目标

版本: v1.0.0
日期: 2026-04-04
"""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class VerificationFailure:
    """单个校验失败项"""
    dimension: str       # 校验维度
    detail: str          # 失败详情
    severity: str        # critical / warning / info


@dataclass
class VerificationResult:
    """校验结果"""
    passed: bool
    failures: List[VerificationFailure] = field(default_factory=list)
    suggested_action: str = "pass"  # pass / retry / degrade / clarify
    checks_run: int = 0

    def add_failure(self, dimension: str, detail: str, severity: str = "warning"):
        self.failures.append(VerificationFailure(
            dimension=dimension, detail=detail, severity=severity,
        ))

    @property
    def critical_failures(self) -> List[VerificationFailure]:
        return [f for f in self.failures if f.severity == "critical"]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "suggested_action": self.suggested_action,
            "checks_run": self.checks_run,
            "failure_count": len(self.failures),
            "critical_count": len(self.critical_failures),
            "failures": [
                {"dimension": f.dimension, "detail": f.detail, "severity": f.severity}
                for f in self.failures
            ],
        }


class OutputVerifier:
    """
    输出校验器

    对 DAG 执行结果进行 5 维度确定性校验，
    未通过的结果不应渲染给用户。
    """

    # 每组动作的估算时间（分钟）
    MINUTES_PER_SET = 2.5

    # 常见器械中英文映射（用于模糊匹配）
    EQUIPMENT_ALIASES = {
        "barbell": "杠铃", "dumbbell": "哑铃", "kettlebell": "壶铃",
        "cable": "绳索", "machine": "器械", "bodyweight": "自重",
        "pull_up_bar": "引体向上杆", "bench": "卧推凳",
        "resistance_band": "弹力带", "smith_machine": "史密斯机",
    }

    def verify(
        self,
        dag_results: Dict[str, Any],
        user_profile: Dict[str, Any],
        hard_constraints: Optional[List[str]] = None,
    ) -> VerificationResult:
        """
        执行 5 维度校验

        Args:
            dag_results: DAG 工具执行结果 {tool_name: result_dict}
            user_profile: 用户档案
            hard_constraints: 硬约束列表（来自 Memory v2）

        Returns:
            VerificationResult
        """
        result = VerificationResult(passed=True)

        # 1. 安全约束冲突
        self._check_safety_conflict(result, dag_results, hard_constraints or [])

        # 2. 器械可用性
        self._check_equipment_mismatch(result, dag_results, user_profile)

        # 3. 训练时长
        self._check_duration_exceeded(result, dag_results, user_profile)

        # 4. 训练量
        self._check_volume_overload(result, dag_results)

        # 5. 目标一致性
        self._check_goal_mismatch(result, dag_results, user_profile)

        # 判定最终结果
        result.checks_run = 5
        if result.critical_failures:
            result.passed = False
            result.suggested_action = "retry"
        elif result.failures:
            result.passed = True  # warning 不阻止输出
            result.suggested_action = "pass"

        if not result.passed:
            logger.warning(
                f"🚫 输出校验未通过: {len(result.failures)} 项失败, "
                f"critical={len(result.critical_failures)}, "
                f"action={result.suggested_action}"
            )
        else:
            logger.debug(
                f"✅ 输出校验通过: {len(result.failures)} warnings"
            )

        return result

    # ============================================================
    # 维度 1: 安全约束冲突
    # ============================================================

    def _check_safety_conflict(
        self,
        result: VerificationResult,
        dag_results: Dict[str, Any],
        hard_constraints: List[str],
    ):
        """检查计划中的动作是否与硬约束冲突"""
        if not hard_constraints:
            return

        # 提取计划中的动作名称
        exercises = self._extract_exercises(dag_results)
        if not exercises:
            return

        constraint_lower = [c.lower() for c in hard_constraints]

        for exercise in exercises:
            ex_lower = exercise.lower()
            for i, constraint in enumerate(constraint_lower):
                # 模糊匹配：约束文本中包含动作名，或反过来
                if ex_lower in constraint or constraint in ex_lower:
                    result.add_failure(
                        dimension="safety_conflict",
                        detail=f"动作 '{exercise}' 与硬约束冲突: '{hard_constraints[i]}'",
                        severity="critical",
                    )

    # ============================================================
    # 维度 2: 器械可用性
    # ============================================================

    def _check_equipment_mismatch(
        self,
        result: VerificationResult,
        dag_results: Dict[str, Any],
        user_profile: Dict[str, Any],
    ):
        """检查计划中的器械是否用户可用"""
        available = user_profile.get("available_equipment", [])
        if not available:
            return  # 未填写器械信息则跳过

        if isinstance(available, str):
            available = [available]
        available_lower = set(e.lower() for e in available)

        # 添加别名
        available_expanded = set(available_lower)
        for eng, chn in self.EQUIPMENT_ALIASES.items():
            if eng in available_lower or chn in available_lower:
                available_expanded.add(eng)
                available_expanded.add(chn)

        # "自重"和"bodyweight"始终可用
        available_expanded.update(["自重", "bodyweight", "徒手"])

        # 提取计划中要求的器械
        required_equipment = self._extract_equipment(dag_results)
        for equip in required_equipment:
            equip_lower = equip.lower()
            if equip_lower not in available_expanded:
                result.add_failure(
                    dimension="equipment_mismatch",
                    detail=f"计划需要 '{equip}' 但用户可用器械中未包含",
                    severity="warning",
                )

    # ============================================================
    # 维度 3: 训练时长
    # ============================================================

    def _check_duration_exceeded(
        self,
        result: VerificationResult,
        dag_results: Dict[str, Any],
        user_profile: Dict[str, Any],
    ):
        """检查估算时长是否超过用户可用时间"""
        available_time = user_profile.get("available_time")
        if not available_time:
            return

        # 将可用时间转为分钟
        if isinstance(available_time, str):
            available_minutes = self._parse_time_to_minutes(available_time)
        elif isinstance(available_time, (int, float)):
            available_minutes = float(available_time)
        else:
            return

        if available_minutes <= 0:
            return

        # 估算训练时长 = 总组数 × 每组时间
        total_sets = self._extract_total_sets(dag_results)
        estimated_minutes = total_sets * self.MINUTES_PER_SET + 10  # +10分钟热身

        if estimated_minutes > available_minutes * 1.2:  # 允许20%弹性
            result.add_failure(
                dimension="duration_exceeded",
                detail=f"估算训练时长 {estimated_minutes:.0f} 分钟 > "
                       f"用户可用时间 {available_minutes:.0f} 分钟 (+20%弹性)",
                severity="warning",
            )

    # ============================================================
    # 维度 4: 训练量
    # ============================================================

    def _check_volume_overload(
        self,
        result: VerificationResult,
        dag_results: Dict[str, Any],
    ):
        """检查总训练量是否超过 MAV 上限"""
        # 从 muscle_group_volume_calculator 结果提取
        vol_result = dag_results.get("muscle_group_volume_calculator", {})
        if not vol_result or not isinstance(vol_result, dict):
            return

        recommendations = vol_result.get("recommendations", {})
        if not recommendations:
            return

        for muscle_group, rec in recommendations.items():
            if not isinstance(rec, dict):
                continue
            planned = rec.get("planned_sets", 0)
            mav = rec.get("mav", 0) or rec.get("maximum_adaptive_volume", 0)
            if mav > 0 and planned > mav:
                result.add_failure(
                    dimension="volume_overload",
                    detail=f"肌群 '{muscle_group}' 计划 {planned} 组 > MAV 上限 {mav} 组",
                    severity="warning",
                )

    # ============================================================
    # 维度 5: 目标一致性
    # ============================================================

    def _check_goal_mismatch(
        self,
        result: VerificationResult,
        dag_results: Dict[str, Any],
        user_profile: Dict[str, Any],
    ):
        """检查计划类型是否与用户训练目标一致"""
        goal = user_profile.get("fitness_goal", "")
        if not goal:
            return

        # 从 professional_program_designer 提取计划类型
        program = dag_results.get("professional_program_designer", {})
        if not program or not isinstance(program, dict):
            return

        program_type = program.get("program_type", "") or program.get("type", "")
        if not program_type:
            return

        # 简单的目标-方案冲突检测
        goal_lower = goal.lower()
        type_lower = program_type.lower()

        conflicts = [
            (["减脂", "减肥", "fat_loss"], ["力量", "strength", "powerlifting"]),
            (["增肌", "muscle_gain", "hypertrophy"], ["有氧", "cardio", "endurance"]),
        ]

        for goal_keywords, plan_keywords in conflicts:
            goal_match = any(kw in goal_lower for kw in goal_keywords)
            plan_match = any(kw in type_lower for kw in plan_keywords)
            if goal_match and plan_match:
                result.add_failure(
                    dimension="goal_mismatch",
                    detail=f"用户目标 '{goal}' 与方案类型 '{program_type}' 可能不一致",
                    severity="warning",
                )

    # ============================================================
    # 数据提取辅助
    # ============================================================

    @staticmethod
    def _extract_exercises(dag_results: Dict[str, Any]) -> List[str]:
        """从 DAG 结果提取动作名称列表"""
        exercises = []
        for tool_name, result in dag_results.items():
            if not isinstance(result, dict):
                continue
            # 从 intelligent_exercise_selector
            if "recommended_exercises" in result:
                for ex in result["recommended_exercises"]:
                    if isinstance(ex, dict):
                        exercises.append(ex.get("name", ex.get("exercise_name", "")))
                    elif isinstance(ex, str):
                        exercises.append(ex)
            # 从 professional_program_designer
            if "exercises" in result:
                for ex in result["exercises"]:
                    if isinstance(ex, dict):
                        exercises.append(ex.get("name", ""))
                    elif isinstance(ex, str):
                        exercises.append(ex)
        return [e for e in exercises if e]

    @staticmethod
    def _extract_equipment(dag_results: Dict[str, Any]) -> List[str]:
        """从 DAG 结果提取所需器械列表"""
        equipment = set()
        for tool_name, result in dag_results.items():
            if not isinstance(result, dict):
                continue
            for key in ["recommended_exercises", "exercises"]:
                if key in result and isinstance(result[key], list):
                    for ex in result[key]:
                        if isinstance(ex, dict):
                            equip = ex.get("equipment", "")
                            if equip:
                                equipment.add(equip)
        return list(equipment)

    @staticmethod
    def _extract_total_sets(dag_results: Dict[str, Any]) -> int:
        """从 DAG 结果提取总组数"""
        total = 0
        for tool_name, result in dag_results.items():
            if not isinstance(result, dict):
                continue
            for key in ["recommended_exercises", "exercises"]:
                if key in result and isinstance(result[key], list):
                    for ex in result[key]:
                        if isinstance(ex, dict):
                            total += ex.get("sets", 0)
        return total

    @staticmethod
    def _parse_time_to_minutes(time_str: str) -> float:
        """解析时间字符串为分钟数"""
        time_str = time_str.strip().lower()
        # "60分钟" / "60min" / "1小时" / "1h"
        import re
        m = re.search(r'(\d+\.?\d*)\s*(?:分钟|min|m)', time_str)
        if m:
            return float(m.group(1))
        m = re.search(r'(\d+\.?\d*)\s*(?:小时|hour|h)', time_str)
        if m:
            return float(m.group(1)) * 60
        # 纯数字默认为分钟
        m = re.search(r'(\d+\.?\d*)', time_str)
        if m:
            return float(m.group(1))
        return 0
