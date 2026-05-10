# -*- coding: utf-8 -*-
"""
结构化工具结果格式 — 百万上下文优化

将工具返回结果分为 4 层，帮助 LLM 在百万上下文中聚焦关键信息：
- core: 必须关注的核心结果（LLM 必须基于此回复）
- safety: 安全约束（不可违反）
- detailed: 详细参数（按需引用）
- metadata: 调试信息（通常忽略）

版本: 1.0.0
日期: 2026-05-11
"""

from typing import Dict, List, Any, Optional


def structure_exercise_results(
    raw_results: List[Dict[str, Any]],
    user_injuries: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    将动作搜索结果结构化为分层格式
    
    Args:
        raw_results: 原始搜索结果
        user_injuries: 用户伤病列表（用于标注安全信息）
    
    Returns:
        分层结构化结果
    """
    core_items = []
    safety_items = []
    detailed_items = []

    for r in raw_results[:10]:
        # Core: 动作名 + 主要肌群 + 推荐理由
        core_items.append({
            "name": r.get("name_zh") or r.get("name") or r.get("id", ""),
            "primary_muscles": r.get("muscles_primary_zh") or r.get("primary_muscles", []),
            "difficulty": r.get("difficulty_zh") or r.get("difficulty", ""),
            "score": round(r.get("reranked_score") or r.get("fused_score") or r.get("score", 0), 3),
        })

        # Safety: 禁忌和风险
        if r.get("contraindicated") or r.get("has_contraindications"):
            safety_items.append({
                "exercise": r.get("name_zh") or r.get("name", ""),
                "risk": "contraindicated",
                "reason": r.get("contraindication_reason") or "存在禁忌症",
            })
        elif r.get("_gc_boost", 0) < -0.1:
            # 图卷积降分的动作可能不太适合
            safety_items.append({
                "exercise": r.get("name_zh") or r.get("name", ""),
                "risk": "caution",
                "reason": "与用户常用动作关联度较低",
            })

        # Detailed: 完整参数
        detailed_items.append({
            "id": r.get("id", ""),
            "name_zh": r.get("name_zh", ""),
            "name_en": r.get("name_en") or r.get("name", ""),
            "equipment": r.get("equipment_zh") or r.get("equipment", []),
            "secondary_muscles": r.get("muscles_secondary_zh") or r.get("secondary_muscles", []),
            "movement_pattern": r.get("movement_pattern", ""),
            "instructions": r.get("instructions", ""),
            "fusion_meta": r.get("_fusion_meta"),
            "gc_boost": r.get("_gc_boost"),
        })

    return {
        "core": {
            "description": "推荐动作列表（按综合评分排序）",
            "count": len(core_items),
            "items": core_items,
        },
        "safety": {
            "description": "安全约束（不可违反）",
            "issues": safety_items,
            "user_injuries": user_injuries or [],
        },
        "detailed": {
            "description": "详细参数（按需引用）",
            "items": detailed_items,
        },
        "metadata": {
            "total_candidates": len(raw_results),
            "fusion_enabled": any(r.get("fused_score") for r in raw_results),
            "rerank_enabled": any(r.get("reranked_score") for r in raw_results),
        },
    }


def structure_volume_results(raw_result: Dict[str, Any]) -> Dict[str, Any]:
    """将训练容量结果结构化"""
    return {
        "core": {
            "muscle_group": raw_result.get("muscle_group", ""),
            "recommended_sets_per_week": raw_result.get("recommended") or raw_result.get("mav"),
            "frequency": raw_result.get("frequency", {}),
        },
        "safety": {
            "mrv_limit": raw_result.get("mrv"),
            "warning": f"不要超过 MRV ({raw_result.get('mrv')} 组/周)，否则恢复不足",
        },
        "detailed": {
            "mev": raw_result.get("mev"),
            "mav": raw_result.get("mav"),
            "mrv": raw_result.get("mrv"),
            "recovery_days": raw_result.get("recovery_days"),
            "sets_per_session": raw_result.get("sets_per_session"),
            "notes": raw_result.get("notes"),
        },
        "metadata": {
            "source": "RP Hypertrophy Guide",
        },
    }


def structure_contraindication_results(raw_result: Dict[str, Any]) -> Dict[str, Any]:
    """将禁忌症检查结果结构化"""
    exercises = raw_result.get("exercise_results", [])

    safe_exercises = [e for e in exercises if not e.get("has_contraindications")]
    risky_exercises = [e for e in exercises if e.get("has_contraindications")]

    return {
        "core": {
            "safe_count": len(safe_exercises),
            "risky_count": len(risky_exercises),
            "overall_risk": raw_result.get("overall_assessment", {}).get("risk_level", "LOW"),
        },
        "safety": {
            "description": "以下动作存在禁忌，必须替换或修改",
            "contraindicated_exercises": [
                {
                    "name": e.get("exercise_name_zh", ""),
                    "risk_level": e.get("max_risk_level", ""),
                    "reasons": [c.get("reason", "") for c in e.get("contraindications", [])[:3]],
                }
                for e in risky_exercises
            ],
            "medical_guidance": raw_result.get("medical_guidance", ""),
        },
        "detailed": {
            "exercise_results": exercises,
        },
        "metadata": {
            "checked_count": raw_result.get("checked_exercises", 0),
            "execution_time_ms": raw_result.get("execution_time_ms", 0),
        },
    }
