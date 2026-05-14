"""
智能推理工具 — 组合多个数据源进行训练规划

- generate_training_cycle: 生成完整训练周期
- analyze_training_balance: 分析训练平衡性
- calculate_progressive_overload: 计算渐进超负荷建议

这些工具不是简单的检索/计算，而是组合逻辑：
用户档案 + 训练记录 + 图谱数据 + 计算公式 → 个性化方案
"""

import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional

from .calculators import (
    calculate_training_volume,
    assess_strength_level,
    design_training_split,
    calculate_1rm,
)
from .graph_queries import get_muscle_exercise_map, get_contraindications
from ..data.graph_store import GraphStore

logger = logging.getLogger(__name__)

# 渐进超负荷策略
PROGRESSION_STRATEGIES = {
    "linear": {
        "name": "线性渐进",
        "description": "每个周期固定增加重量",
        "suitable_for": ["beginner", "novice"],
        "increment_kg": {"compound": 2.5, "isolation": 1.25},
    },
    "double_progression": {
        "name": "双重渐进",
        "description": "先增加次数到上限，再增加重量回到下限",
        "suitable_for": ["intermediate"],
        "rep_range": {"min": 6, "max": 10},
        "increment_kg": {"compound": 2.5, "isolation": 1.25},
    },
    "undulating": {
        "name": "波动周期",
        "description": "每次训练变化强度（重/中/轻）",
        "suitable_for": ["intermediate", "advanced"],
        "intensity_pattern": [0.85, 0.75, 0.80],
    },
}

# 每肌群推荐容量（组/星期）— 与 calculators.py 保持一致
# 来源：RP Strength (Dr. Mike Israetel) 训练容量理论
# 参考：https://rpstrength.com/training-volume-landmarks-muscle-growth
# 注意：这些是群体平均值，个体差异大（±30%），后续应从知识库动态获取
# MEV = Minimum Effective Volume（最小有效容量）
# MAV = Maximum Adaptive Volume（最大适应容量，最佳增长区间）
# MRV = Maximum Recoverable Volume（最大可恢复容量，超过则过度训练）
VOLUME_STANDARDS = {
    "胸": {"mev": 8, "mav": 14, "mrv": 20},
    "背": {"mev": 8, "mav": 14, "mrv": 20},
    "肩": {"mev": 6, "mav": 12, "mrv": 18},
    "股四头肌": {"mev": 6, "mav": 14, "mrv": 20},
    "腘绳肌": {"mev": 4, "mav": 10, "mrv": 16},
    "臀部": {"mev": 4, "mav": 12, "mrv": 16},
    "肱二头肌": {"mev": 4, "mav": 10, "mrv": 16},
    "肱三头肌": {"mev": 4, "mav": 8, "mrv": 14},
    "小腿": {"mev": 6, "mav": 10, "mrv": 14},
    "腹部": {"mev": 0, "mav": 8, "mrv": 16},
}


def generate_training_cycle(
    user_profile: Dict[str, Any],
    goal: str = "hypertrophy",
    days_per_week: int = 4,
    available_equipment: List[str] = None,
    cycle_weeks: int = 4,
    graph: GraphStore = None,
) -> Dict[str, Any]:
    """生成完整训练周期方案

    组合逻辑:
    1. 确定训练水平和分化方案
    2. 为每个训练日选择动作（考虑器械和伤病）
    3. 设定组数/次数/强度
    4. 应用渐进超负荷策略
    5. 安排 deload

    Returns:
        {
            "cycle_type": str,
            "cycle_weeks": int,
            "deload_week": int,
            "sessions": [{day, focus, exercises: [{name, sets, reps, intensity, progression}]}],
            "progression_rules": str,
            "deload_protocol": str
        }
    """
    # 1. 确定训练水平
    training_level = user_profile.get("training", {}).get("level", "intermediate")
    injuries = user_profile.get("health", {}).get("injuries", [])

    # 2. 设计分化方案
    split = design_training_split(
        days_per_week=days_per_week,
        goal=goal,
        training_level=training_level,
    )

    # 3. 选择渐进策略
    if training_level in ("beginner", "novice"):
        strategy = PROGRESSION_STRATEGIES["linear"]
    elif training_level == "intermediate":
        strategy = PROGRESSION_STRATEGIES["double_progression"]
    else:
        strategy = PROGRESSION_STRATEGIES["undulating"]

    # 4. 获取禁忌动作（如果有伤病）
    blocked_exercises = set()
    if injuries and graph:
        contra_result = get_contraindications(injuries, graph)
        blocked_exercises = {c["exercise"] for c in contra_result.get("contraindicated", [])}

    # 5. 为每个训练日选择动作
    sessions = []
    for day_info in split.get("schedule", []):
        day_num = day_info.get("day", len(sessions) + 1)
        focus = day_info.get("focus", "全身")
        muscle_groups = day_info.get("muscle_groups", [focus])

        exercises = []
        for muscle in muscle_groups:
            # 从图谱获取该肌群的动作
            if graph:
                muscle_map = get_muscle_exercise_map(
                    muscle=muscle,
                    graph=graph,
                    level=_level_to_zh(training_level),
                    equipment=available_equipment[0] if available_equipment else None,
                )
                candidates = muscle_map.get("primary_exercises", [])
            else:
                candidates = []

            # 过滤禁忌动作
            safe_candidates = [e for e in candidates if e not in blocked_exercises]

            # 选择动作（复合优先，2-3个/肌群）
            selected = safe_candidates[:3] if safe_candidates else [f"{muscle}训练动作"]

            # 设定参数
            for i, ex_name in enumerate(selected):
                is_compound = i == 0  # 第一个动作视为复合动作
                if goal == "strength":
                    sets, reps, intensity = (5, "3-5", "80-90%") if is_compound else (3, "6-8", "70-80%")
                elif goal == "hypertrophy":
                    sets, reps, intensity = (4, "6-10", "70-80%") if is_compound else (3, "10-12", "60-70%")
                else:  # general_fitness
                    sets, reps, intensity = (3, "8-12", "65-75%") if is_compound else (3, "12-15", "55-65%")

                increment = strategy["increment_kg"]["compound" if is_compound else "isolation"]
                exercises.append({
                    "name": ex_name,
                    "sets": sets,
                    "reps": reps,
                    "intensity": intensity,
                    "progression": f"+{increment}kg/周期" if strategy["name"] == "线性渐进" else strategy["description"],
                })

        sessions.append({
            "day": day_num,
            "focus": focus,
            "exercises": exercises,
        })

    # 6. Deload 安排（根据训练水平调整频率）
    deload_intervals = {"beginner": None, "novice": 6, "intermediate": 4, "advanced": 3}
    deload_interval = deload_intervals.get(training_level, 4)

    if deload_interval:
        deload_week = cycle_weeks + 1
        deload_protocol = "容量减半（组数×0.5），强度保持（重量不变），持续1个周期"
    else:
        deload_week = None
        deload_protocol = "新手阶段通常不需要 deload，持续线性进步直到停滞"

    return {
        "cycle_type": strategy["name"],
        "cycle_weeks": cycle_weeks,
        "deload_week": deload_week,
        "sessions": sessions,
        "progression_rules": strategy["description"],
        "deload_protocol": deload_protocol,
        "notes": f"基于{training_level}水平设计，目标{goal}",
    }


def analyze_training_balance(
    training_records: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """分析训练平衡性

    输入: 训练记录列表 [{exercise, muscle_group, sets, date}]
    输出: 各肌群容量 vs 推荐标准 + 失衡分析

    Returns:
        {
            "period": str,
            "by_muscle_group": {muscle: {sets_per_week, status, vs_standard}},
            "imbalances": [str],
            "recommendations": [str]
        }
    """
    if not training_records:
        return {
            "error": "无训练记录",
            "fallback_hint": "请询问用户最近的训练安排（每个肌群每星期练几组）",
        }

    # 按肌群聚合每星期组数
    muscle_sets = defaultdict(int)
    total_days = set()

    for record in training_records:
        muscle = record.get("muscle_group", "未知")
        sets = record.get("sets", 0)
        date = record.get("date", "")
        muscle_sets[muscle] += sets
        if date:
            total_days.add(date)

    # 计算周数（用日期跨度而非训练日数量）
    if len(total_days) >= 2:
        sorted_days = sorted(total_days)
        try:
            from datetime import datetime
            first = datetime.strptime(sorted_days[0], "%Y-%m-%d")
            last = datetime.strptime(sorted_days[-1], "%Y-%m-%d")
            span_days = (last - first).days
            num_weeks = max(span_days / 7, 1)
        except (ValueError, TypeError):
            num_weeks = max(len(total_days) / 7, 1)
    else:
        num_weeks = 1

    # 对比标准
    by_muscle_group = {}
    imbalances = []
    recommendations = []

    for muscle, total_sets in muscle_sets.items():
        sets_per_week = round(total_sets / num_weeks, 1)
        standard = VOLUME_STANDARDS.get(muscle)

        if standard:
            if sets_per_week < standard["mev"]:
                status = "insufficient"
                vs_standard = f"低于 MEV({standard['mev']}组)"
                recommendations.append(f"增加{muscle}训练至{standard['mav']}组/星期")
            elif sets_per_week > standard["mrv"]:
                status = "excessive"
                vs_standard = f"超过 MRV({standard['mrv']}组)"
                recommendations.append(f"减少{muscle}训练至{standard['mav']}组/星期，注意恢复")
                imbalances.append(f"{muscle}训练过量({sets_per_week}组/星期)")
            elif sets_per_week < standard["mav"]:
                status = "below_optimal"
                vs_standard = f"MEV-MAV之间({standard['mev']}-{standard['mav']})"
            else:
                status = "optimal"
                vs_standard = f"MAV范围内({standard['mav']}组)"
        else:
            status = "unknown"
            vs_standard = "无标准数据"

        by_muscle_group[muscle] = {
            "sets_per_week": sets_per_week,
            "status": status,
            "vs_standard": vs_standard,
        }

    # 推拉平衡检查（注意：肩部只算一半到推，因为后束属于拉链）
    push_sets = sum(
        v["sets_per_week"] for k, v in by_muscle_group.items()
        if k in ("胸", "肱三头肌")
    ) + by_muscle_group.get("肩", {}).get("sets_per_week", 0) * 0.5
    pull_sets = sum(
        v["sets_per_week"] for k, v in by_muscle_group.items()
        if k in ("背", "肱二头肌")
    ) + by_muscle_group.get("肩", {}).get("sets_per_week", 0) * 0.5
    if push_sets > 0 and pull_sets > 0:
        ratio = push_sets / pull_sets
        if ratio > 1.3:
            imbalances.append(f"推拉比例失衡({ratio:.1f}:1)，推多拉少")
            recommendations.append("增加背部和二头训练，或减少胸部训练")
        elif ratio < 0.75:
            imbalances.append(f"推拉比例失衡(1:{1/ratio:.1f})，拉多推少")
            recommendations.append("增加胸部和三头训练以平衡推拉比")

    return {
        "period": f"最近{int(num_weeks)}星期",
        "by_muscle_group": by_muscle_group,
        "imbalances": imbalances,
        "recommendations": recommendations,
    }


def calculate_progressive_overload(
    exercise_name: str,
    recent_records: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """计算渐进超负荷建议

    输入: 动作名 + 最近几次记录 [{weight, reps, date}]
    输出: 下次建议 + 趋势分析 + deload 判断

    Returns:
        {
            "exercise": str,
            "current_estimated_1rm": float,
            "trend": str,
            "next_session": {weight, reps, strategy, rationale},
            "deload_needed": bool,
            "deload_reason": str | None
        }
    """
    if not recent_records or len(recent_records) < 2:
        return {
            "error": "记录不足（至少需要2次）",
            "fallback_hint": f"请询问用户最近几次{exercise_name}的重量和次数",
        }

    # 计算每次的估算 1RM
    estimated_1rms = []
    for record in recent_records:
        weight = record.get("weight", 0)
        reps = record.get("reps", 0)
        if weight > 0 and reps > 0:
            result = calculate_1rm(weight, reps)
            estimated_1rms.append(result["estimated_1rm"])

    if not estimated_1rms:
        return {"error": "记录数据无效", "fallback_hint": "请确认重量和次数数据"}

    current_1rm = estimated_1rms[-1]
    prev_1rm = estimated_1rms[0]

    # 趋势分析
    change_pct = (current_1rm - prev_1rm) / prev_1rm * 100 if prev_1rm > 0 else 0

    if change_pct > 3:
        trend = "improving"
    elif change_pct < -5:
        trend = "declining"
    else:
        trend = "plateau"

    # 判断是否需要 deload
    deload_needed = False
    deload_reason = None

    if trend == "declining" and len(estimated_1rms) >= 3:
        # 检查最近3次是否连续下降
        recent_3 = estimated_1rms[-3:]
        if all(recent_3[i] > recent_3[i+1] for i in range(len(recent_3)-1)):
            deload_needed = True
            deload_reason = "连续多次训练力量下降，可能过度训练"

    if trend == "plateau" and len(estimated_1rms) >= 4:
        # 长期停滞
        variance = max(estimated_1rms) - min(estimated_1rms)
        if variance < current_1rm * 0.03:  # 波动 < 3%
            deload_needed = True
            deload_reason = "长期停滞（4次以上无进步），建议 deload 后重新开始"

    # 生成下次建议
    last_record = recent_records[-1]
    last_weight = last_record.get("weight", 0)
    last_reps = last_record.get("reps", 0)

    if deload_needed:
        next_weight = round(last_weight * 0.85, 1)  # 减重 15%
        next_reps = last_reps
        strategy = "deload"
        rationale = deload_reason
    elif trend == "improving":
        # 线性加重
        next_weight = last_weight + 2.5
        next_reps = last_reps
        strategy = "linear_increase"
        rationale = "力量持续进步，继续线性加重"
    elif trend == "plateau":
        # 尝试微加载或变换次数
        if last_reps < 8:
            next_weight = last_weight
            next_reps = last_reps + 1
            strategy = "rep_increase"
            rationale = "重量停滞，先增加1次重复"
        else:
            next_weight = last_weight + 1.25
            next_reps = max(last_reps - 2, 3)  # 最少3次
            strategy = "micro_load"
            rationale = "尝试微加载(+1.25kg)，降低次数"
    else:  # declining
        next_weight = last_weight
        next_reps = last_reps
        strategy = "maintain"
        rationale = "力量下降中，保持当前负荷观察恢复"

    return {
        "exercise": exercise_name,
        "current_estimated_1rm": round(current_1rm, 1),
        "trend": trend,
        "trend_detail": f"{'+'if change_pct>0 else ''}{change_pct:.1f}% vs 首次记录",
        "next_session": {
            "weight": next_weight,
            "reps": next_reps,
            "strategy": strategy,
            "rationale": rationale,
        },
        "deload_needed": deload_needed,
        "deload_reason": deload_reason,
    }


def _level_to_zh(level: str) -> str:
    """训练水平英文→中文"""
    return {
        "beginner": "初级",
        "novice": "初级",
        "intermediate": "中级",
        "advanced": "高级",
        "elite": "高级",
    }.get(level, "中级")
