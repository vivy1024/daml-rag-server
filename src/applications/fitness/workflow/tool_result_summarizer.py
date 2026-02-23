# -*- coding: utf-8 -*-
"""
MCP工具结果摘要器 — LLM专用

将MCP工具的完整返回数据压缩为LLM可消费的精简摘要。
完整数据已通过 structured_data SSE事件发送给前端，LLM不需要看完整JSON。

设计原则：
- 大型工具（>2000 chars）做专用摘要，小型工具原样保留
- 保留动作名称、组数/次数/间歇等核心训练参数
- 复用 TrainingPlanSummarizer 的链接生成和安全标记逻辑
- 不改变工具本身的返回格式（只在序列化阶段压缩）

前端动作详情路由: /exercise/:id
"""

import json
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# 前端动作详情基础URL
EXERCISE_DETAIL_PATH = "/exercise"

# 高风险动作关键词（复用 TrainingPlanSummarizer 的定义）
_HIGH_RISK_KEYWORDS = {
    '硬拉', '深蹲', '抓举', '挺举', '颈后推举', '早安式体前屈',
    'deadlift', 'squat', 'snatch', 'clean', 'jerk',
}


def _is_high_risk(name: str) -> bool:
    name_lower = name.lower()
    return any(kw in name_lower for kw in _HIGH_RISK_KEYWORDS)


def _exercise_brief(ex: Dict, include_link: bool = True) -> str:
    """单个动作的精简描述：名称(组×次,休Xs,链接)"""
    eid = ex.get("exercise_id", "")
    name = ex.get("name_zh", "") or ex.get("name_en", "") or ex.get("name", "")
    sets = ex.get("sets", "?")
    reps = ex.get("reps_range", ex.get("reps", "?"))
    rest = ex.get("rest_seconds", ex.get("rest", "?"))
    if isinstance(reps, (list, tuple)) and len(reps) == 2:
        reps = f"{reps[0]}-{reps[1]}"

    marker = "⚠️" if _is_high_risk(name) else ""
    link = f",详情:{EXERCISE_DETAIL_PATH}/{eid}" if (eid and include_link) else ""
    return f"{marker}{name}({sets}组×{reps}次,休{rest}s{link})"


def summarize_for_llm(tool_name: str, result: Any) -> Any:
    """将单个工具结果压缩为LLM摘要"""
    if not isinstance(result, dict):
        return result

    summarizer = _SUMMARIZERS.get(tool_name)
    if summarizer:
        try:
            return summarizer(result)
        except Exception as e:
            logger.warning(f"工具 {tool_name} 摘要失败，回退截断: {e}")
            return _fallback_truncate(result)

    # 无专用摘要器：小结果原样返回，大结果截断
    serialized = json.dumps(result, ensure_ascii=False, default=str)
    if len(serialized) > 2000:
        return _fallback_truncate(result)
    return result


# ═══════════════════════════════════════════════════
#  训练类工具摘要器
# ═══════════════════════════════════════════════════


def _summarize_professional_program_designer(r: Dict) -> Dict:
    """professional_program_designer: ~100K → ~1.5K"""
    overview = r.get("program_overview", {})
    weekly_programs = r.get("weekly_programs", [])

    weeks_summary = []
    for week in weekly_programs:
        week_num = week.get("week_number", "?")
        phase = week.get("periodization_phase", "")
        days = []
        for day in week.get("training_days", []):
            day_name = day.get("day_name", "")
            exercises = day.get("exercises", [])
            ex_list = [_exercise_brief(ex) for ex in exercises]
            days.append(f"{day_name}: {'; '.join(ex_list)}")
        weeks_summary.append(f"第{week_num}周({phase}): " + " | ".join(days))

    return {
        "success": r.get("success"),
        "tool_name": "professional_program_designer",
        "program_overview": {
            "training_goal": overview.get("training_goal"),
            "training_split": overview.get("training_split"),
            "training_days_per_week": overview.get("training_days_per_week"),
            "total_exercises": overview.get("total_exercises"),
            "average_weekly_sets": overview.get("average_weekly_sets"),
            "training_weeks": overview.get("training_weeks"),
            "training_pattern": overview.get("training_pattern"),
            "periodization_model": overview.get("periodization_model"),
        },
        "weekly_plans_summary": weeks_summary,
        "safety_assessment": _brief(r.get("safety_assessment")),
        "execution_guidelines": r.get("execution_guidelines", [])[:3],
        "important_notes": r.get("important_notes", [])[:3],
    }


def _summarize_training_split_designer(r: Dict) -> Dict:
    """training_split_designer: ~18K → ~500"""
    split_plan = r.get("split_plan", {})
    schedule = r.get("weekly_schedule", {})

    schedule_summary = []
    items = []
    if isinstance(schedule, dict):
        items = (schedule.get("schedule", [])
                 or schedule.get("days", [])
                 or schedule.get("training_days", []))
    elif isinstance(schedule, list):
        items = schedule

    for item in items:
        if isinstance(item, dict):
            label = (item.get("day", "") or item.get("day_name", "")
                     or str(item.get("day_number", "")))
            content = (item.get("session", "") or item.get("content", "")
                       or item.get("session_name", "") or item.get("focus", ""))
            if isinstance(content, dict):
                content = content.get("session_name", str(content)[:60])
            schedule_summary.append(f"{label}: {str(content)[:60]}")
        elif isinstance(item, str):
            schedule_summary.append(item[:60])

    # 备选：从 session_plans 提取
    if not schedule_summary:
        for sp in split_plan.get("session_plans", []):
            if isinstance(sp, dict):
                name = sp.get("session_name", sp.get("name", ""))
                muscles = sp.get("target_muscles", sp.get("focus_muscle_groups", []))
                if isinstance(muscles, list):
                    muscles = ", ".join(muscles[:3])
                schedule_summary.append(f"{name}: {muscles}"[:80])

    return {
        "success": r.get("success"),
        "tool_name": "training_split_designer",
        "split_type": split_plan.get("split_type"),
        "split_name": split_plan.get("split_name"),
        "training_days": split_plan.get("training_days"),
        "training_pattern": split_plan.get("training_pattern"),
        "cycle_days": split_plan.get("cycle_days"),
        "weekly_schedule_summary": schedule_summary[:7],
        "load_recommendations": _brief(r.get("load_recommendations")),
    }


def _summarize_periodized_program_designer(r: Dict) -> Dict:
    """periodized_program_designer: ~5K → ~400"""
    phases = r.get("periodization_phases", r.get("phases", []))
    phases_summary = []
    for p in phases if isinstance(phases, list) else []:
        if isinstance(p, dict):
            name = p.get("phase_name", p.get("name", ""))
            weeks = p.get("duration_weeks", p.get("weeks", ""))
            focus = p.get("focus", p.get("description", ""))
            phases_summary.append(f"{name}({weeks}周): {str(focus)[:80]}")

    return {
        "success": r.get("success"),
        "tool_name": "periodized_program_designer",
        "periodization_model": r.get("periodization_model", ""),
        "total_weeks": r.get("total_weeks", r.get("plan_duration_weeks", "")),
        "phases_summary": phases_summary,
        "progression_strategy": _brief(r.get("progression_strategy")),
    }


def _summarize_intelligent_exercise_selector(r: Dict) -> Dict:
    """intelligent_exercise_selector: ~7K → ~500"""
    recs = r.get("recommendations", [])
    exercises_brief = [_exercise_brief(ex, include_link=True) for ex in recs[:8]]

    return {
        "success": r.get("success"),
        "tool_name": "intelligent_exercise_selector",
        "total_found": r.get("total_found"),
        "recommended_exercises": exercises_brief,
        "safety_alerts": r.get("safety_alerts", []),
    }


def _summarize_exercise_alternative_finder(r: Dict) -> Dict:
    """exercise_alternative_finder: 替代动作推荐"""
    alternatives = r.get("alternatives", r.get("recommendations", []))
    alt_brief = [_exercise_brief(a) for a in alternatives[:6]]

    return {
        "success": r.get("success"),
        "tool_name": "exercise_alternative_finder",
        "original_exercise": r.get("original_exercise", ""),
        "reason": r.get("reason", r.get("alternative_reason", "")),
        "alternatives": alt_brief,
    }


def _summarize_safe_exercise_modifier(r: Dict) -> Dict:
    """safe_exercise_modifier: 动作安全修改建议"""
    modifications = r.get("modifications", r.get("suggestions", []))
    mod_brief = []
    for m in modifications[:5]:
        if isinstance(m, dict):
            mod_brief.append({
                "exercise": m.get("exercise_name", m.get("name", "")),
                "modification": str(m.get("modification", m.get("suggestion", "")))[:100],
                "reason": str(m.get("reason", ""))[:80],
            })

    return {
        "success": r.get("success"),
        "tool_name": "safe_exercise_modifier",
        "modifications": mod_brief,
        "safety_level": r.get("safety_level", r.get("overall_safety", "")),
    }


# ═══════════════════════════════════════════════════
#  营养类工具摘要器
# ═══════════════════════════════════════════════════


def _summarize_tdee_calculator(r: Dict) -> Dict:
    """tdee_calculator: TDEE和宏量素计算"""
    calorie = r.get("calorie_target", {})
    macro = r.get("macronutrient_distribution", {})
    bmr = r.get("bmr_calculation", {})

    return {
        "success": r.get("success"),
        "tool_name": "tdee_calculator",
        "bmr": bmr.get("bmr") or bmr.get("bmr_value"),
        "tdee": calorie.get("tdee") or calorie.get("maintenance_calories"),
        "target_calories": calorie.get("target_calories"),
        "calorie_adjustment": calorie.get("calorie_adjustment"),
        "macros": {
            "protein_g": macro.get("protein_grams", macro.get("protein_g")),
            "carbs_g": macro.get("carbs_grams", macro.get("carbs_g")),
            "fat_g": macro.get("fat_grams", macro.get("fat_g")),
        },
        "additional_recommendations": r.get("additional_recommendations", [])[:3],
    }


def _summarize_meal_plan_designer(r: Dict) -> Dict:
    """meal_plan_designer: 膳食计划"""
    summary = r.get("plan_summary", {})
    training_plan = r.get("training_day_plan", {})
    rest_plan = r.get("rest_day_plan", {})

    def _meal_brief(plan: Dict) -> List[str]:
        meals = plan.get("meals", [])
        return [
            f"{m.get('meal_name', '')}: {m.get('calories', '')}卡"
            for m in meals[:5] if isinstance(m, dict)
        ]

    return {
        "success": r.get("success"),
        "tool_name": "meal_plan_designer",
        "plan_summary": _brief(summary),
        "training_day_meals": _meal_brief(training_plan),
        "rest_day_meals": _meal_brief(rest_plan),
        "practical_tips": r.get("practical_tips", [])[:3],
    }


def _summarize_nutrition_intake_analyzer(r: Dict) -> Dict:
    """nutrition_intake_analyzer: 营养摄入分析"""
    current = r.get("current_intake", {})
    target = r.get("target_needs", {})
    gap = r.get("nutrient_gap", {})
    quality = r.get("diet_quality_score", {})

    return {
        "success": r.get("success"),
        "tool_name": "nutrition_intake_analyzer",
        "current_calories": current.get("calories"),
        "target_calories": target.get("calories"),
        "calorie_gap": gap.get("calories_gap"),
        "diet_quality_score": quality.get("overall_score", quality.get("score")),
        "improvement_suggestions": [
            str(s.get("suggestion", s))[:100] if isinstance(s, dict) else str(s)[:100]
            for s in r.get("improvement_suggestions", [])[:3]
        ],
    }


def _summarize_exercise_nutrition_optimization(r: Dict) -> Dict:
    """exercise_nutrition_optimization: 运动营养优化"""
    return {
        "success": r.get("success"),
        "tool_name": "exercise_nutrition_optimization",
        "training_summary": _brief(r.get("training_summary")),
        "pre_workout": _brief(r.get("pre_workout_nutrition")),
        "post_workout": _brief(r.get("post_workout_nutrition")),
        "hydration_strategy": _brief(r.get("hydration_strategy")),
        "personalized_tips": r.get("personalized_tips", [])[:3],
    }


# ═══════════════════════════════════════════════════
#  小型工具（<2K chars，原样返回）
# ═══════════════════════════════════════════════════


def _passthrough(r: Dict) -> Dict:
    """小型工具原样返回"""
    return r


# ═══════════════════════════════════════════════════
#  工具函数
# ═══════════════════════════════════════════════════


def _brief(obj: Any, max_len: int = 200) -> Any:
    """提取简要信息"""
    if obj is None:
        return None
    if isinstance(obj, str):
        return obj[:max_len]
    if isinstance(obj, list):
        return [
            (str(item.get("suggestion", item))[:100] if isinstance(item, dict)
             else str(item)[:100])
            for item in obj[:3]
        ]
    if isinstance(obj, dict):
        brief = {}
        for i, (k, v) in enumerate(obj.items()):
            if i >= 5:
                break
            brief[k] = str(v)[:100] if isinstance(v, str) else v
        return brief
    return obj


def _fallback_truncate(result: Dict, max_chars: int = 1500) -> Dict:
    """通用截断：保留 success/tool_name + 截断其余"""
    truncated = {}
    remaining = max_chars

    for key in ("success", "tool_name", "user_id", "confidence_score"):
        if key in result:
            truncated[key] = result[key]

    for key, value in result.items():
        if key in truncated:
            continue
        if remaining <= 0:
            truncated["_truncated"] = True
            break
        serialized = json.dumps(value, ensure_ascii=False, default=str)
        if len(serialized) <= remaining:
            truncated[key] = value
            remaining -= len(serialized)
        else:
            if isinstance(value, str):
                truncated[key] = value[:remaining] + "...(已截断)"
            elif isinstance(value, list):
                truncated[key] = value[:2]
            elif isinstance(value, dict):
                truncated[key] = {k: "..." for k in list(value.keys())[:3]}
            remaining = 0

    return truncated


# ═══════════════════════════════════════════════════
#  摘要器注册表（覆盖全部MCP工具）
# ═══════════════════════════════════════════════════


_SUMMARIZERS = {
    # 训练类（大型，需要压缩）
    "professional_program_designer": _summarize_professional_program_designer,
    "training_split_designer": _summarize_training_split_designer,
    "periodized_program_designer": _summarize_periodized_program_designer,
    "intelligent_exercise_selector": _summarize_intelligent_exercise_selector,
    "exercise_alternative_finder": _summarize_exercise_alternative_finder,
    "safe_exercise_modifier": _summarize_safe_exercise_modifier,
    # 营养类（中型，提取核心数值）
    "tdee_calculator": _summarize_tdee_calculator,
    "meal_plan_designer": _summarize_meal_plan_designer,
    "nutrition_intake_analyzer": _summarize_nutrition_intake_analyzer,
    "exercise_nutrition_optimization": _summarize_exercise_nutrition_optimization,
    # 小型工具（<2K chars，原样返回）
    "contraindications_checker": _passthrough,
    "injury_risk_assessor": _passthrough,
    "muscle_group_volume_calculator": _passthrough,
    "intelligent_weight_calculator": _passthrough,
    "movement_pattern_balancer": _passthrough,
    "record_training_feedback": _passthrough,
    # 内部/辅助工具
    "get_user_profile": _passthrough,
    "postural_assessor": _passthrough,
    "find_similar_training_cases": _passthrough,
}
