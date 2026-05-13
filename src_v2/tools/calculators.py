"""
MCP 工具: 计算规划类

- calculate_tdee: 基础代谢 + 活动系数 → 每日总消耗
- calculate_training_volume: MEV/MAV/MRV 训练容量计算
- calculate_1rm: Epley 公式估算 1RM
- assess_strength_level: 力量水平评估
- design_training_split: 训练分化设计建议
"""

import math
from typing import Any, Dict, List, Optional


# === TDEE 计算 ===

def calculate_tdee(
    gender: str,
    age: int,
    weight_kg: float,
    height_cm: float,
    activity_level: str = "moderate",
    goal: str = "maintain",
) -> Dict[str, Any]:
    """计算每日总能量消耗 (TDEE)

    Args:
        gender: male/female
        age: 年龄
        weight_kg: 体重(kg)
        height_cm: 身高(cm)
        activity_level: sedentary/light/moderate/active/very_active
        goal: lose_fat/maintain/lean_bulk/bulk

    Returns:
        {bmr, tdee, target_calories, macros: {protein, fat, carbs}}
    """
    # Mifflin-St Jeor 公式
    if gender.lower() == "male":
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age + 5
    else:
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age - 161

    # 活动系数
    activity_multipliers = {
        "sedentary": 1.2,       # 久坐
        "light": 1.375,         # 轻度活动（1-3天/周）
        "moderate": 1.55,       # 中度活动（3-5天/周）
        "active": 1.725,        # 高度活动（6-7天/周）
        "very_active": 1.9,     # 极高活动（运动员）
    }
    multiplier = activity_multipliers.get(activity_level, 1.55)
    tdee = bmr * multiplier

    # 目标热量调整
    goal_adjustments = {
        "lose_fat": -500,       # 减脂：-500 kcal
        "maintain": 0,          # 维持
        "lean_bulk": 250,       # 精益增肌：+250 kcal
        "bulk": 500,            # 增肌：+500 kcal
    }
    adjustment = goal_adjustments.get(goal, 0)
    target_calories = tdee + adjustment

    # 宏量营养素分配
    protein_g = weight_kg * _get_protein_multiplier(goal)
    protein_cal = protein_g * 4

    fat_ratio = 0.25 if goal == "lose_fat" else 0.30
    fat_cal = target_calories * fat_ratio
    fat_g = fat_cal / 9

    carbs_cal = target_calories - protein_cal - fat_cal
    carbs_g = max(carbs_cal / 4, 50)  # 最低 50g 碳水

    return {
        "bmr": round(bmr),
        "tdee": round(tdee),
        "target_calories": round(target_calories),
        "adjustment": adjustment,
        "goal": goal,
        "macros": {
            "protein_g": round(protein_g),
            "fat_g": round(fat_g),
            "carbs_g": round(carbs_g),
            "protein_ratio": round(protein_cal / target_calories * 100),
            "fat_ratio": round(fat_cal / target_calories * 100),
            "carbs_ratio": round(carbs_cal / target_calories * 100),
        },
        "notes": _get_nutrition_notes(goal, weight_kg),
    }


def _get_protein_multiplier(goal: str) -> float:
    """根据目标确定蛋白质系数 (g/kg)"""
    return {
        "lose_fat": 2.2,    # 减脂期高蛋白保肌肉
        "maintain": 1.8,
        "lean_bulk": 2.0,
        "bulk": 1.8,
    }.get(goal, 1.8)


def _get_nutrition_notes(goal: str, weight_kg: float) -> List[str]:
    """生成营养建议备注"""
    notes = []
    if goal == "lose_fat":
        notes.append(f"每周减重目标: 0.5-1% 体重 ({weight_kg*0.005:.1f}-{weight_kg*0.01:.1f} kg)")
        notes.append("优先保证蛋白质摄入，防止肌肉流失")
    elif goal in ("lean_bulk", "bulk"):
        notes.append(f"每周增重目标: 0.25-0.5% 体重 ({weight_kg*0.0025:.1f}-{weight_kg*0.005:.1f} kg)")
        notes.append("训练日可适当增加碳水摄入")
    return notes


# === 训练容量计算 ===

def calculate_training_volume(
    muscle_group: str,
    training_level: str = "intermediate",
    goal: str = "hypertrophy",
    recovery_capacity: str = "normal",
) -> Dict[str, Any]:
    """计算肌群训练容量 (MEV/MAV/MRV)

    基于 Mike Israetel 的训练容量理论。

    Args:
        muscle_group: 肌群名称
        training_level: beginner/intermediate/advanced
        goal: hypertrophy/strength/endurance
        recovery_capacity: low/normal/high

    Returns:
        {mev, mav, mrv, recommended_sets, frequency, notes}
    """
    # 基础容量数据（每周组数）
    # 来源: Renaissance Periodization Volume Landmarks
    volume_data = {
        "chest": {"mev": 8, "mav": 14, "mrv": 20},
        "back": {"mev": 8, "mav": 14, "mrv": 22},
        "shoulders": {"mev": 6, "mav": 12, "mrv": 18},
        "biceps": {"mev": 4, "mav": 10, "mrv": 16},
        "triceps": {"mev": 4, "mav": 10, "mrv": 16},
        "quads": {"mev": 6, "mav": 14, "mrv": 20},
        "hamstrings": {"mev": 4, "mav": 10, "mrv": 16},
        "glutes": {"mev": 4, "mav": 12, "mrv": 18},
        "calves": {"mev": 6, "mav": 10, "mrv": 16},
        "abs": {"mev": 0, "mav": 10, "mrv": 20},
        "traps": {"mev": 0, "mav": 10, "mrv": 18},
        "forearms": {"mev": 2, "mav": 8, "mrv": 14},
    }

    # 中文映射
    zh_to_en = {
        "胸": "chest", "胸部": "chest", "胸大肌": "chest",
        "背": "back", "背部": "back", "背阔肌": "back",
        "肩": "shoulders", "肩部": "shoulders", "三角肌": "shoulders",
        "二头": "biceps", "肱二头肌": "biceps",
        "三头": "triceps", "肱三头肌": "triceps",
        "腿": "quads", "股四头肌": "quads", "大腿前侧": "quads",
        "腘绳肌": "hamstrings", "大腿后侧": "hamstrings",
        "臀": "glutes", "臀部": "glutes", "臀大肌": "glutes",
        "小腿": "calves", "腓肠肌": "calves",
        "腹": "abs", "腹肌": "abs", "核心": "abs",
        "斜方肌": "traps",
        "前臂": "forearms",
    }

    # 标准化肌群名
    muscle_en = zh_to_en.get(muscle_group, muscle_group.lower())
    base = volume_data.get(muscle_en, {"mev": 6, "mav": 12, "mrv": 18})

    # 训练水平调整
    level_factor = {"beginner": 0.7, "intermediate": 1.0, "advanced": 1.2}.get(training_level, 1.0)

    # 恢复能力调整
    recovery_factor = {"low": 0.8, "normal": 1.0, "high": 1.15}.get(recovery_capacity, 1.0)

    factor = level_factor * recovery_factor

    mev = round(base["mev"] * factor)
    mav = round(base["mav"] * factor)
    mrv = round(base["mrv"] * factor)

    # 推荐组数（MAV 附近）
    recommended = mav

    # 训练频率建议
    if recommended <= 8:
        frequency = 1
    elif recommended <= 14:
        frequency = 2
    else:
        frequency = 3

    return {
        "muscle_group": muscle_group,
        "muscle_group_en": muscle_en,
        "mev": mev,
        "mav": mav,
        "mrv": mrv,
        "recommended_sets_per_week": recommended,
        "frequency_per_week": frequency,
        "sets_per_session": round(recommended / frequency),
        "training_level": training_level,
        "goal": goal,
        "notes": [
            f"MEV (最小有效容量): {mev} 组/周 — 维持肌肉的最低量",
            f"MAV (最大适应容量): {mav} 组/周 — 最佳增长区间",
            f"MRV (最大恢复容量): {mrv} 组/周 — 超过此量恢复不足",
            f"建议每次训练 {round(recommended/frequency)} 组，每周 {frequency} 次",
        ],
    }


# === 1RM 估算 ===

def calculate_1rm(
    weight: float,
    reps: int,
    formula: str = "epley",
) -> Dict[str, Any]:
    """估算 1RM (一次最大重复重量)

    Args:
        weight: 使用重量 (kg)
        reps: 完成次数 (1-30)
        formula: epley/brzycki/lombardi

    Returns:
        {estimated_1rm, percentages: {5rm, 8rm, 10rm, 12rm}, formula_used}
    """
    if reps <= 0:
        return {"error": "次数必须大于 0"}
    if reps == 1:
        estimated_1rm = weight
    elif formula == "epley":
        estimated_1rm = weight * (1 + reps / 30)
    elif formula == "brzycki":
        estimated_1rm = weight * (36 / (37 - reps))
    elif formula == "lombardi":
        estimated_1rm = weight * (reps ** 0.10)
    else:
        estimated_1rm = weight * (1 + reps / 30)  # default epley

    # 各 RM 对应百分比
    rm_percentages = {
        "1rm": 1.00,
        "2rm": 0.95,
        "3rm": 0.93,
        "5rm": 0.87,
        "8rm": 0.80,
        "10rm": 0.75,
        "12rm": 0.70,
        "15rm": 0.65,
        "20rm": 0.60,
    }

    percentages = {
        k: round(estimated_1rm * v, 1)
        for k, v in rm_percentages.items()
    }

    return {
        "estimated_1rm": round(estimated_1rm, 1),
        "input": {"weight": weight, "reps": reps},
        "formula": formula,
        "percentages": percentages,
        "training_zones": {
            "strength": f"{percentages['3rm']}-{percentages['5rm']} kg × 3-5 reps",
            "hypertrophy": f"{percentages['8rm']}-{percentages['12rm']} kg × 8-12 reps",
            "endurance": f"{percentages['15rm']}-{percentages['20rm']} kg × 15-20 reps",
        },
    }


# === 力量水平评估 ===

def assess_strength_level(
    exercise: str,
    weight_lifted: float,
    body_weight: float,
    gender: str = "male",
    reps: int = 1,
) -> Dict[str, Any]:
    """评估力量水平

    基于体重比评估训练水平。

    Args:
        exercise: 动作名称（bench_press/squat/deadlift/overhead_press）
        weight_lifted: 举起重量 (kg)
        body_weight: 体重 (kg)
        gender: male/female
        reps: 完成次数（>1 时先估算 1RM）

    Returns:
        {level, ratio, percentile, next_level_target}
    """
    # 先估算 1RM
    if reps > 1:
        one_rm = weight_lifted * (1 + reps / 30)
    else:
        one_rm = weight_lifted

    ratio = one_rm / body_weight

    # 力量标准（男性，体重比）
    # 来源: Strength Level / ExRx
    male_standards = {
        "bench_press": {"beginner": 0.5, "novice": 0.75, "intermediate": 1.0, "advanced": 1.5, "elite": 2.0},
        "squat": {"beginner": 0.75, "novice": 1.0, "intermediate": 1.5, "advanced": 2.0, "elite": 2.5},
        "deadlift": {"beginner": 1.0, "novice": 1.25, "intermediate": 1.75, "advanced": 2.5, "elite": 3.0},
        "overhead_press": {"beginner": 0.35, "novice": 0.55, "intermediate": 0.75, "advanced": 1.0, "elite": 1.35},
    }

    female_standards = {
        "bench_press": {"beginner": 0.25, "novice": 0.5, "intermediate": 0.75, "advanced": 1.0, "elite": 1.5},
        "squat": {"beginner": 0.5, "novice": 0.75, "intermediate": 1.25, "advanced": 1.5, "elite": 2.0},
        "deadlift": {"beginner": 0.75, "novice": 1.0, "intermediate": 1.5, "advanced": 2.0, "elite": 2.5},
        "overhead_press": {"beginner": 0.2, "novice": 0.35, "intermediate": 0.5, "advanced": 0.75, "elite": 1.0},
    }

    # 中文映射
    exercise_map = {
        "卧推": "bench_press", "杠铃卧推": "bench_press",
        "深蹲": "squat", "杠铃深蹲": "squat",
        "硬拉": "deadlift", "杠铃硬拉": "deadlift",
        "推举": "overhead_press", "肩推": "overhead_press", "杠铃推举": "overhead_press",
    }
    exercise_en = exercise_map.get(exercise, exercise.lower())

    standards = male_standards if gender.lower() == "male" else female_standards
    exercise_standards = standards.get(exercise_en)

    if not exercise_standards:
        return {
            "error": f"不支持的动作: {exercise}",
            "supported": list(male_standards.keys()),
            "ratio": round(ratio, 2),
        }

    # 确定水平
    level = "beginner"
    for lvl in ["elite", "advanced", "intermediate", "novice", "beginner"]:
        if ratio >= exercise_standards[lvl]:
            level = lvl
            break

    # 下一级目标
    levels_order = ["beginner", "novice", "intermediate", "advanced", "elite"]
    current_idx = levels_order.index(level)
    next_level = None
    next_target = None
    if current_idx < len(levels_order) - 1:
        next_level = levels_order[current_idx + 1]
        next_target = round(exercise_standards[next_level] * body_weight, 1)

    return {
        "exercise": exercise,
        "exercise_en": exercise_en,
        "one_rm": round(one_rm, 1),
        "body_weight": body_weight,
        "ratio": round(ratio, 2),
        "level": level,
        "level_zh": {"beginner": "初学者", "novice": "新手", "intermediate": "中级", "advanced": "高级", "elite": "精英"}.get(level, level),
        "next_level": next_level,
        "next_target_kg": next_target,
        "standards": exercise_standards,
    }


# === 训练分化设计 ===

def design_training_split(
    days_per_week: int = 4,
    goal: str = "hypertrophy",
    training_level: str = "intermediate",
    weak_points: List[str] = None,
) -> Dict[str, Any]:
    """设计训练分化方案

    Args:
        days_per_week: 每周训练天数 (2-6)
        goal: hypertrophy/strength/general
        training_level: beginner/intermediate/advanced
        weak_points: 弱项肌群列表

    Returns:
        {split_name, schedule: [{day, focus, muscle_groups, sets}], notes}
    """
    days_per_week = max(2, min(6, days_per_week))

    if days_per_week <= 3 and training_level == "beginner":
        return _full_body_split(days_per_week, goal)
    elif days_per_week <= 3:
        return _upper_lower_split(days_per_week, goal)
    elif days_per_week == 4:
        return _upper_lower_4day(goal, weak_points)
    elif days_per_week == 5:
        return _ppl_split(goal, weak_points)
    else:  # 6 days
        return _ppl_2x_split(goal, weak_points)


def _full_body_split(days: int, goal: str) -> Dict:
    schedule = []
    for i in range(days):
        schedule.append({
            "day": i + 1,
            "focus": "全身",
            "muscle_groups": ["胸", "背", "腿", "肩", "核心"],
            "total_sets": 15,
            "example": "深蹲3×8, 卧推3×8, 划船3×10, 推举2×10, 平板支撑2×30s",
        })
    return {
        "split_name": "全身训练",
        "days_per_week": days,
        "schedule": schedule,
        "notes": ["适合新手", "每个肌群每周训练频率高", "每次训练时间控制在 45-60 分钟"],
    }


def _upper_lower_split(days: int, goal: str) -> Dict:
    schedule = [
        {"day": 1, "focus": "上肢", "muscle_groups": ["胸", "背", "肩", "二头", "三头"], "total_sets": 18},
        {"day": 2, "focus": "下肢", "muscle_groups": ["股四头", "腘绳肌", "臀", "小腿", "核心"], "total_sets": 16},
    ]
    if days >= 3:
        schedule.append({"day": 3, "focus": "上肢", "muscle_groups": ["胸", "背", "肩", "二头", "三头"], "total_sets": 16})
    return {
        "split_name": "上下肢分化",
        "days_per_week": days,
        "schedule": schedule,
        "notes": ["适合中级训练者", "每个肌群每周 2 次频率"],
    }


def _upper_lower_4day(goal: str, weak_points: List[str] = None) -> Dict:
    schedule = [
        {"day": 1, "focus": "上肢 (力量)", "muscle_groups": ["胸", "背", "肩"], "total_sets": 18},
        {"day": 2, "focus": "下肢 (力量)", "muscle_groups": ["股四头", "腘绳肌", "臀"], "total_sets": 16},
        {"day": 3, "focus": "休息", "muscle_groups": [], "total_sets": 0},
        {"day": 4, "focus": "上肢 (肌肥大)", "muscle_groups": ["胸", "背", "肩", "手臂"], "total_sets": 20},
        {"day": 5, "focus": "下肢 (肌肥大)", "muscle_groups": ["股四头", "腘绳肌", "臀", "小腿"], "total_sets": 18},
    ]
    return {
        "split_name": "上下肢 4 天",
        "days_per_week": 4,
        "schedule": schedule,
        "notes": ["力量日: 3-5 reps, 肌肥大日: 8-12 reps", "每个肌群每周 2 次"],
    }


def _ppl_split(goal: str, weak_points: List[str] = None) -> Dict:
    schedule = [
        {"day": 1, "focus": "推 (Push)", "muscle_groups": ["胸", "肩前束", "三头"], "total_sets": 18},
        {"day": 2, "focus": "拉 (Pull)", "muscle_groups": ["背", "肩后束", "二头"], "total_sets": 18},
        {"day": 3, "focus": "腿 (Legs)", "muscle_groups": ["股四头", "腘绳肌", "臀", "小腿"], "total_sets": 18},
        {"day": 4, "focus": "上肢补充", "muscle_groups": ["弱项肌群", "手臂"], "total_sets": 14},
        {"day": 5, "focus": "下肢/全身", "muscle_groups": ["臀", "核心", "有氧"], "total_sets": 14},
    ]
    return {
        "split_name": "PPL + 补充",
        "days_per_week": 5,
        "schedule": schedule,
        "notes": ["经典 PPL 变体", "第 4-5 天针对弱项"],
    }


def _ppl_2x_split(goal: str, weak_points: List[str] = None) -> Dict:
    schedule = [
        {"day": 1, "focus": "推 A (力量)", "muscle_groups": ["胸", "肩", "三头"], "total_sets": 16},
        {"day": 2, "focus": "拉 A (力量)", "muscle_groups": ["背", "二头", "后链"], "total_sets": 16},
        {"day": 3, "focus": "腿 A (力量)", "muscle_groups": ["股四头", "腘绳肌", "臀"], "total_sets": 16},
        {"day": 4, "focus": "推 B (肌肥大)", "muscle_groups": ["胸", "肩", "三头"], "total_sets": 18},
        {"day": 5, "focus": "拉 B (肌肥大)", "muscle_groups": ["背", "二头", "后链"], "total_sets": 18},
        {"day": 6, "focus": "腿 B (肌肥大)", "muscle_groups": ["股四头", "腘绳肌", "臀", "小腿"], "total_sets": 18},
    ]
    return {
        "split_name": "PPL ×2",
        "days_per_week": 6,
        "schedule": schedule,
        "notes": ["高频率高容量", "适合高级训练者", "确保睡眠和营养充足"],
    }
