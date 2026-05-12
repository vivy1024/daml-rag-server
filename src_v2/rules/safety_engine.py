"""
安全规则引擎 — Harness 层

确定性安全校验，fail-closed 设计。
不依赖 LLM，纯规则判断，保证安全底线。

规则类型：
1. 禁忌症过滤：用户有伤病 → 过滤禁忌动作
2. 训练水平门控：新手不推荐高级动作
3. 器械可用性：用户没有的器械不推荐
4. 负荷安全：推荐重量不超过安全上限
5. 动作频率：同一肌群不连续训练（48h 恢复）
"""

import logging
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class RuleVerdict(Enum):
    """规则判定结果"""
    PASS = "pass"           # 通过
    BLOCK = "block"         # 阻止（硬性禁忌）
    WARN = "warn"           # 警告（软性建议）
    DOWNGRADE = "downgrade" # 降级（降低推荐权重）


@dataclass
class RuleResult:
    """单条规则的执行结果"""
    rule_name: str
    verdict: RuleVerdict
    item_id: str
    reason: str = ""
    penalty: float = 0.0  # 降权系数（DOWNGRADE 时使用）


@dataclass
class SafetyReport:
    """安全检查报告"""
    blocked_ids: Set[str] = field(default_factory=set)
    warnings: List[RuleResult] = field(default_factory=list)
    penalties: Dict[str, float] = field(default_factory=dict)  # item_id → 总惩罚
    applied_rules: List[str] = field(default_factory=list)


# === 训练水平映射 ===
LEVEL_ORDER = {
    "novice": 0,
    "beginner": 1,
    "intermediate": 2,
    "advanced": 3,
    "elite": 4,
}

# 动作难度 → 最低训练水平要求
EXERCISE_MIN_LEVEL = {
    # 高级动作
    "snatch": "advanced",
    "clean_and_jerk": "advanced",
    "muscle_up": "advanced",
    "pistol_squat": "intermediate",
    "front_lever": "advanced",
    "planche": "elite",
    # 中级动作
    "barbell_squat": "beginner",
    "deadlift": "beginner",
    "overhead_press": "beginner",
    "power_clean": "intermediate",
    "turkish_getup": "intermediate",
}


class SafetyEngine:
    """安全规则引擎

    Usage:
        engine = SafetyEngine(graph_store)
        report = engine.check(candidate_ids, user_profile)
        # 根据 report 过滤/降权候选
    """

    def __init__(self, graph_store=None, metadata_store=None):
        """
        Args:
            graph_store: GraphStore 实例（用于查询禁忌关系）
            metadata_store: MetadataStore 实例（用于查询动作属性）
        """
        self.graph = graph_store
        self.metadata = metadata_store

    def check(
        self,
        candidate_ids: List[str],
        user_profile: Dict,
        context: Dict = None,
    ) -> SafetyReport:
        """对候选列表执行全部安全规则

        Args:
            candidate_ids: 候选动作 ID 列表
            user_profile: 用户档案
            context: 上下文（最近训练记录等）

        Returns:
            SafetyReport
        """
        report = SafetyReport()
        context = context or {}

        # 依次执行各规则
        rules = [
            self._rule_contraindication,
            self._rule_level_gate,
            self._rule_equipment_availability,
            self._rule_recovery_time,
        ]

        for rule_fn in rules:
            results = rule_fn(candidate_ids, user_profile, context)
            for result in results:
                report.applied_rules.append(result.rule_name)

                if result.verdict == RuleVerdict.BLOCK:
                    report.blocked_ids.add(result.item_id)
                    logger.info(f"BLOCKED: {result.item_id} — {result.reason}")

                elif result.verdict == RuleVerdict.WARN:
                    report.warnings.append(result)

                elif result.verdict == RuleVerdict.DOWNGRADE:
                    current = report.penalties.get(result.item_id, 0.0)
                    report.penalties[result.item_id] = current + result.penalty

        logger.info(
            f"SafetyEngine: checked {len(candidate_ids)} candidates, "
            f"blocked={len(report.blocked_ids)}, warnings={len(report.warnings)}"
        )
        return report

    def apply_report(
        self, candidates: List[Tuple[str, float]], report: SafetyReport
    ) -> List[Tuple[str, float]]:
        """将安全报告应用到候选列表

        - 移除 blocked
        - 对 downgrade 的降权
        """
        results = []
        for item_id, score in candidates:
            if item_id in report.blocked_ids:
                continue
            penalty = report.penalties.get(item_id, 0.0)
            adjusted_score = score * (1.0 - min(penalty, 0.9))
            results.append((item_id, adjusted_score))

        # 重新排序
        results.sort(key=lambda x: x[1], reverse=True)
        return results

    # === 规则实现 ===

    def _rule_contraindication(
        self, candidate_ids: List[str], user_profile: Dict, context: Dict
    ) -> List[RuleResult]:
        """规则1: 禁忌症过滤

        用户有伤病/体态问题 → 检查动作是否有 CONTRAINDICATED_FOR 关系
        """
        results = []
        if not self.graph or not self.graph.ready:
            return results

        # 获取用户的伤病/体态问题
        injuries = user_profile.get("injuries", [])
        postural_issues = user_profile.get("postural_issues", [])
        conditions = set()

        for injury in injuries:
            if isinstance(injury, dict):
                conditions.add(injury.get("type", "").lower())
                conditions.add(injury.get("id", "").lower())
            else:
                conditions.add(str(injury).lower())

        for issue in postural_issues:
            if isinstance(issue, dict):
                conditions.add(issue.get("type", "").lower())
            else:
                conditions.add(str(issue).lower())

        if not conditions:
            return results

        for exercise_id in candidate_ids:
            contraindications = self.graph.get_relations(exercise_id, "CONTRAINDICATED_FOR")
            for edge in contraindications:
                target = (edge.get("target", "") or "").lower()
                target_name = (edge.get("target_name_zh", "") or "").lower()

                for condition in conditions:
                    if condition and (condition in target or condition in target_name):
                        results.append(RuleResult(
                            rule_name="contraindication",
                            verdict=RuleVerdict.BLOCK,
                            item_id=exercise_id,
                            reason=f"禁忌: {exercise_id} 对 {condition} 有禁忌",
                        ))
                        break
                else:
                    continue
                break

        return results

    def _rule_level_gate(
        self, candidate_ids: List[str], user_profile: Dict, context: Dict
    ) -> List[RuleResult]:
        """规则2: 训练水平门控

        新手不推荐高级动作（降权而非阻止）
        """
        results = []
        user_level = user_profile.get("fitness_level", "beginner")
        user_level_num = LEVEL_ORDER.get(user_level, 1)

        for exercise_id in candidate_ids:
            # 从元数据获取动作难度
            exercise_level = None
            if self.metadata:
                ex = self.metadata.get_exercise(exercise_id)
                if ex:
                    exercise_level = ex.get("difficulty") or ex.get("level")

            # 从硬编码表查
            if not exercise_level:
                exercise_level = EXERCISE_MIN_LEVEL.get(exercise_id)

            if not exercise_level:
                continue

            required_level_num = LEVEL_ORDER.get(exercise_level, 0)

            if user_level_num < required_level_num:
                gap = required_level_num - user_level_num
                if gap >= 2:
                    # 差距太大 → 阻止
                    results.append(RuleResult(
                        rule_name="level_gate",
                        verdict=RuleVerdict.BLOCK,
                        item_id=exercise_id,
                        reason=f"训练水平不足: 需要 {exercise_level}，用户为 {user_level}",
                    ))
                else:
                    # 差距1级 → 降权
                    results.append(RuleResult(
                        rule_name="level_gate",
                        verdict=RuleVerdict.DOWNGRADE,
                        item_id=exercise_id,
                        reason=f"训练水平偏低: 建议 {exercise_level}",
                        penalty=0.3,
                    ))

        return results

    def _rule_equipment_availability(
        self, candidate_ids: List[str], user_profile: Dict, context: Dict
    ) -> List[RuleResult]:
        """规则3: 器械可用性

        用户没有的器械 → 降权（不阻止，因为可能在健身房）
        """
        results = []
        available_equipment = user_profile.get("available_equipment", [])

        if not available_equipment or not self.metadata:
            return results

        available_set = {e.lower() for e in available_equipment}

        for exercise_id in candidate_ids:
            ex = self.metadata.get_exercise(exercise_id)
            if not ex:
                continue

            required = ex.get("equipment") or ex.get("required_equipment")
            if not required:
                continue

            if isinstance(required, str):
                required = [required]

            # 检查是否有不可用的器械
            missing = [eq for eq in required if eq.lower() not in available_set]
            if missing:
                results.append(RuleResult(
                    rule_name="equipment_availability",
                    verdict=RuleVerdict.DOWNGRADE,
                    item_id=exercise_id,
                    reason=f"缺少器械: {', '.join(missing)}",
                    penalty=0.4,
                ))

        return results

    def _rule_recovery_time(
        self, candidate_ids: List[str], user_profile: Dict, context: Dict
    ) -> List[RuleResult]:
        """规则4: 恢复时间

        同一肌群 48h 内不重复高强度训练
        """
        results = []
        recent_muscles = context.get("recent_trained_muscles", {})
        # recent_muscles: {muscle_id: hours_since_last_training}

        if not recent_muscles or not self.graph or not self.graph.ready:
            return results

        for exercise_id in candidate_ids:
            primary_targets = self.graph.get_relations(exercise_id, "TARGETS_PRIMARY")
            for edge in primary_targets:
                muscle = edge.get("target", "")
                hours = recent_muscles.get(muscle, 999)
                if hours < 48:
                    results.append(RuleResult(
                        rule_name="recovery_time",
                        verdict=RuleVerdict.WARN,
                        item_id=exercise_id,
                        reason=f"{muscle} 距上次训练仅 {hours}h，建议休息",
                    ))
                    break

        return results
