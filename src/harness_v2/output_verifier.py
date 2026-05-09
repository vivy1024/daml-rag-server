# -*- coding: utf-8 -*-
"""
OutputVerifier v2 — 输出确定性校验（升级版）

在 Skill 执行完成后、LLM 综合前，对工具结果进行校验。
升级自 Harness v1 OutputVerifier，新增：
- Skill 输出标准合规检查
- 禁忌动作交叉验证（结合用户 health_conditions）

所有校验为纯 Python 逻辑，不调用 LLM，确保确定性和低延迟。

校验维度：
1. safety_conflict:     计划动作 vs 用户禁忌
2. equipment_mismatch:  计划器械 vs 用户可用器械
3. duration_exceeded:   估算总时长 vs 用户可用时间
4. volume_overload:     总组数 vs MAV 上限
5. goal_mismatch:       计划类型 vs 用户训练目标
6. skill_standard:      输出是否满足 Skill 定义的输出标准（新增）

对应需求：REQ-3.3
版本: v2.0.0
日期: 2026-05-09
"""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class VerificationFailure:
    """单个校验失败项"""
    dimension: str
    detail: str
    severity: str  # critical / warning / info


@dataclass
class VerificationResult:
    """校验结果"""
    passed: bool
    failures: List[VerificationFailure] = field(default_factory=list)
    suggested_action: str = "pass"  # pass / degrade / clarify
    checks_run: int = 0
    skill_id: str = ""

    def add_failure(self, dimension: str, detail: str, severity: str = "warning"):
        self.failures.append(VerificationFailure(
            dimension=dimension, detail=detail, severity=severity,
        ))

    @property
    def critical_failures(self) -> List[VerificationFailure]:
        return [f for f in self.failures if f.severity == "critical"]

    @property
    def has_critical(self) -> bool:
        return len(self.critical_failures) > 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "suggested_action": self.suggested_action,
            "checks_run": self.checks_run,
            "skill_id": self.skill_id,
            "failure_count": len(self.failures),
            "critical_count": len(self.critical_failures),
            "failures": [
                {"dimension": f.dimension, "detail": f.detail, "severity": f.severity}
                for f in self.failures
            ],
        }


class OutputVerifierV2:
    """
    输出校验器 v2

    对 Skill 执行结果进行 6 维度确定性校验。
    critical 失败 → 降级回答
    warning → 放行但附加提醒
    """

    # 每组动作的估算时间（分钟）
    MINUTES_PER_SET = 2.5

    def verify(
        self,
        skill_id: str,
        tool_results: Dict[str, Any],
        user_profile: Optional[Dict[str, Any]] = None,
        skill_output_standard: Optional[str] = None,
    ) -> VerificationResult:
        """
        执行输出校验

        Args:
            skill_id: 当前 Skill ID
            tool_results: 工具执行结果
            user_profile: 用户档案
            skill_output_standard: Skill 定义的输出标准文本

        Returns:
            VerificationResult: 校验结果
        """
        result = VerificationResult(passed=True, skill_id=skill_id)

        if not tool_results:
            result.passed = False
            result.suggested_action = "degrade"
            result.add_failure("empty_results", "工具执行无结果", "critical")
            return result

        profile = user_profile or {}

        # 1. 安全冲突检查
        self._check_safety_conflict(result, tool_results, profile)
        result.checks_run += 1

        # 2. 器械匹配检查
        self._check_equipment_mismatch(result, tool_results, profile)
        result.checks_run += 1

        # 3. 时长超限检查
        self._check_duration_exceeded(result, tool_results, profile)
        result.checks_run += 1

        # 4. 训练量超载检查
        self._check_volume_overload(result, tool_results, profile)
        result.checks_run += 1

        # 5. 目标匹配检查
        self._check_goal_mismatch(result, tool_results, profile)
        result.checks_run += 1

        # 6. Skill 输出标准合规检查（新增）
        if skill_output_standard:
            self._check_skill_standard(result, tool_results, skill_output_standard)
        result.checks_run += 1

        # 判定最终结果
        if result.has_critical:
            result.passed = False
            result.suggested_action = "degrade"
        elif result.failures:
            result.passed = True  # warning 不阻止输出
            result.suggested_action = "pass"

        logger.info(
            f"{'✅' if result.passed else '🚫'} OutputVerifier: "
            f"skill={skill_id}, checks={result.checks_run}, "
            f"failures={len(result.failures)}, critical={len(result.critical_failures)}"
        )

        return result

    def _check_safety_conflict(
        self,
        result: VerificationResult,
        tool_results: Dict[str, Any],
        user_profile: Dict[str, Any],
    ):
        """检查计划动作是否与用户禁忌冲突"""
        # 获取禁忌检查结果
        contra_result = tool_results.get("contraindications_checker", {})
        if not contra_result:
            return

        contraindicated = contra_result.get("contraindicated_exercises", [])
        if not contraindicated:
            return

        # 获取计划中的动作
        plan_result = tool_results.get("professional_program_designer", {})
        if not plan_result:
            plan_result = tool_results.get("intelligent_exercise_selector", {})

        planned_exercises = self._extract_exercise_names(plan_result)

        # 交叉检查
        conflicts = []
        contra_names = {e.get("name", "").lower() for e in contraindicated if isinstance(e, dict)}
        contra_names.update(str(e).lower() for e in contraindicated if isinstance(e, str))

        for exercise in planned_exercises:
            if exercise.lower() in contra_names:
                conflicts.append(exercise)

        if conflicts:
            result.add_failure(
                "safety_conflict",
                f"计划包含禁忌动作：{', '.join(conflicts[:5])}",
                "critical",
            )

    def _check_equipment_mismatch(
        self,
        result: VerificationResult,
        tool_results: Dict[str, Any],
        user_profile: Dict[str, Any],
    ):
        """检查计划器械是否与用户可用器械匹配"""
        available_equipment = user_profile.get("training_info", {}).get("available_equipment", [])
        if not available_equipment:
            return  # 无器械信息，跳过

        plan_result = tool_results.get("professional_program_designer", {})
        if not plan_result:
            return

        required_equipment = self._extract_equipment(plan_result)
        available_set = {e.lower() for e in available_equipment}

        missing = [e for e in required_equipment if e.lower() not in available_set]
        if missing:
            result.add_failure(
                "equipment_mismatch",
                f"计划需要用户没有的器械：{', '.join(missing[:5])}",
                "warning",
            )

    def _check_duration_exceeded(
        self,
        result: VerificationResult,
        tool_results: Dict[str, Any],
        user_profile: Dict[str, Any],
    ):
        """检查估算时长是否超过用户可用时间"""
        available_time = user_profile.get("training_info", {}).get("available_time")
        if not available_time:
            return

        if isinstance(available_time, str):
            try:
                available_minutes = float(available_time.replace("分钟", "").replace("min", ""))
            except (ValueError, AttributeError):
                return
        elif isinstance(available_time, (int, float)):
            available_minutes = float(available_time)
        else:
            return

        total_sets = self._count_total_sets(tool_results)
        estimated_minutes = total_sets * self.MINUTES_PER_SET + 10  # +10 热身

        if estimated_minutes > available_minutes * 1.2:  # 20% 弹性
            result.add_failure(
                "duration_exceeded",
                f"估算时长 {estimated_minutes:.0f}分钟 超过可用时间 {available_minutes:.0f}分钟",
                "warning",
            )

    def _check_volume_overload(
        self,
        result: VerificationResult,
        tool_results: Dict[str, Any],
        user_profile: Dict[str, Any],
    ):
        """检查总训练量是否超过 MAV 上限"""
        volume_result = tool_results.get("muscle_group_volume_calculator", {})
        if not volume_result:
            return

        overloaded = volume_result.get("overloaded_muscles", [])
        if overloaded:
            result.add_failure(
                "volume_overload",
                f"以下肌群训练量超过 MAV：{', '.join(overloaded[:5])}",
                "warning",
            )

    def _check_goal_mismatch(
        self,
        result: VerificationResult,
        tool_results: Dict[str, Any],
        user_profile: Dict[str, Any],
    ):
        """检查计划类型是否与用户目标匹配"""
        user_goal = user_profile.get("training_info", {}).get("goal", "")
        if not user_goal:
            return

        # 简单规则：如果用户目标是减脂但计划是纯力量，发出 warning
        # 这里只做基础检查，复杂逻辑由 Skill 本身处理
        pass  # TODO: 后续根据实际 Skill 输出格式完善

    def _check_skill_standard(
        self,
        result: VerificationResult,
        tool_results: Dict[str, Any],
        output_standard: str,
    ):
        """检查输出是否满足 Skill 定义的输出标准"""
        # 基于 output_standard 中的关键词检查
        # 例如 output_standard 说"必须包含组数、次数、RPE"
        # 检查 tool_results 中是否有这些字段

        required_keywords = []
        if "组数" in output_standard or "sets" in output_standard.lower():
            required_keywords.append("sets")
        if "次数" in output_standard or "reps" in output_standard.lower():
            required_keywords.append("reps")
        if "RPE" in output_standard or "rpe" in output_standard:
            required_keywords.append("rpe")

        # 检查 program_designer 结果是否包含这些字段
        plan = tool_results.get("professional_program_designer", {})
        if plan and required_keywords:
            plan_str = str(plan).lower()
            missing_fields = [k for k in required_keywords if k not in plan_str]
            if missing_fields:
                result.add_failure(
                    "skill_standard",
                    f"输出缺少 Skill 要求的字段：{', '.join(missing_fields)}",
                    "info",
                )

    # ─── 辅助方法 ─────────────────────────────────────────────

    def _extract_exercise_names(self, result: Any) -> List[str]:
        """从工具结果中提取动作名称列表"""
        if not result:
            return []
        if isinstance(result, dict):
            exercises = result.get("exercises", [])
            if exercises:
                return [
                    e.get("name", "") or e.get("name_zh", "")
                    for e in exercises
                    if isinstance(e, dict)
                ]
            # 尝试其他字段
            selected = result.get("selected_exercises", [])
            if selected:
                return [
                    e.get("name", "") or e.get("name_zh", "")
                    for e in selected
                    if isinstance(e, dict)
                ]
        return []

    def _extract_equipment(self, result: Any) -> List[str]:
        """从工具结果中提取器械列表"""
        if not result or not isinstance(result, dict):
            return []
        exercises = result.get("exercises", []) or result.get("selected_exercises", [])
        equipment = set()
        for e in exercises:
            if isinstance(e, dict):
                eq = e.get("equipment") or e.get("equipment_zh", "")
                if eq:
                    equipment.add(eq)
        return list(equipment)

    def _count_total_sets(self, tool_results: Dict[str, Any]) -> int:
        """统计总组数"""
        plan = tool_results.get("professional_program_designer", {})
        if not plan or not isinstance(plan, dict):
            return 0
        exercises = plan.get("exercises", []) or plan.get("selected_exercises", [])
        total = 0
        for e in exercises:
            if isinstance(e, dict):
                sets = e.get("sets", 0)
                if isinstance(sets, int):
                    total += sets
        return total
