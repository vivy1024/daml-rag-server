"""
MCP 工具: search_exercises — 动作智能检索

这是浪潮引擎的入口工具。接收自然语言查询，
经过 Embedding → WaveEngine 全管线，返回推荐动作列表。
"""

import logging
import time
from typing import Any, Dict, List, Optional

import numpy as np

from ..engine.wave_engine import WaveEngine
from ..rules.safety_engine import SafetyEngine
from .embedding import encode_query

logger = logging.getLogger(__name__)


async def search_exercises(
    query_text: str,
    user_profile: Optional[Dict[str, Any]] = None,
    filters: Optional[Dict[str, Any]] = None,
    top_k: int = 10,
    *,
    wave_engine: WaveEngine,
    safety_engine: Optional[SafetyEngine] = None,
) -> Dict[str, Any]:
    """搜索健身动作

    Args:
        query_text: 用户查询文本（自然语言）
        user_profile: 用户档案（含伤病、水平、器械等）
        filters: 过滤条件 {muscle_group, equipment, difficulty, ...}
        top_k: 返回数量
        wave_engine: WaveEngine 实例（注入）
        safety_engine: SafetyEngine 实例（注入，可选）

    Returns:
        {
            "exercises": [...],
            "total": int,
            "timing_ms": float,
            "safety_warnings": [...],
            "debug": {...}  # EPA/Spike 等中间结果
        }
    """
    t_start = time.time()

    # 1. 文本 → 向量
    t0 = time.time()
    query_vec = encode_query(query_text)
    t_embed = (time.time() - t0) * 1000

    # 2. 提取关键词（用于 debug 输出 + 注入 filters）
    keywords = _extract_keywords(query_text, filters)

    # 2b. 将肌群关键词注入 filters（驱动图谱加分）
    muscle_keywords_found = _get_muscle_keywords(keywords)
    enriched_filters = dict(filters) if filters else {}
    if muscle_keywords_found and "muscle_group" not in enriched_filters:
        enriched_filters["muscle_group"] = muscle_keywords_found[0]

    # 3. WaveEngine 检索
    # 请求更多候选（安全过滤后可能减少）
    fetch_k = min(top_k * 3, 50)
    wave_result = await wave_engine.search(
        query_vec=query_vec,
        domain="exercises",
        user_profile=user_profile,
        filters=enriched_filters if enriched_filters else None,
        top_k=fetch_k,
    )

    # 5. 安全规则过滤
    safety_warnings = []
    candidate_ids = [str(r["id"]) for r in wave_result.results]
    candidate_scores = {str(r["id"]): r["score"] for r in wave_result.results}

    if safety_engine and user_profile:
        context = _build_safety_context(user_profile)
        report = safety_engine.check(candidate_ids, user_profile, context)

        # 应用安全报告
        scored_list = [(cid, candidate_scores[cid]) for cid in candidate_ids]
        scored_list = safety_engine.apply_report(scored_list, report)

        # 收集警告
        for w in report.warnings:
            safety_warnings.append({
                "exercise_id": w.item_id,
                "rule": w.rule_name,
                "message": w.reason,
            })

        # 更新候选
        candidate_ids = [cid for cid, _ in scored_list]
        candidate_scores = {cid: score for cid, score in scored_list}

    # 6. 应用过滤条件
    # 构建 ID → payload 映射（从 wave_result 中获取）
    id_to_payload = {}
    for r in wave_result.results:
        rid = str(r["id"])
        id_to_payload[rid] = r

    if filters:
        candidate_ids = _apply_filters(
            candidate_ids, filters, wave_engine.data.metadata, id_to_payload
        )

    # 6b. 肌群验证重排：如果查询含肌群关键词，降权不匹配的动作
    if muscle_keywords_found:
        candidate_ids = _muscle_rerank(
            candidate_ids, candidate_scores, muscle_keywords_found,
            wave_engine.data.metadata, id_to_payload,
        )

    # 7. 截取 top_k
    final_ids = candidate_ids[:top_k]

    # 8. 组装结果（精简字段，避免 token 浪费）
    SUMMARY_FIELDS = [
        "name_zh", "name_en", "muscles_primary_zh", "muscles_primary_en",
        "difficulty_zh", "equipment_zh", "force_zh", "mechanic_zh",
        "safety_level", "smart_tags", "slug",
    ]

    exercises = []
    for eid in final_ids:
        # 优先从 wave_result payload 获取（Qdrant 导出的完整数据）
        payload = id_to_payload.get(eid, {})
        # 其次尝试 MetadataStore（Neo4j 导出的数据，key 可能不匹配）
        meta = wave_engine.data.metadata.get_exercise(eid) if wave_engine.data.metadata else None

        item = {
            "id": eid,
            "score": round(candidate_scores.get(eid, 0.0), 4),
        }

        # 从 payload 或 meta 中提取摘要字段
        source = meta if meta else payload
        if source:
            for field in SUMMARY_FIELDS:
                val = source.get(field)
                if val:  # 跳过空值
                    item[field] = val

        exercises.append(item)

    total_ms = (time.time() - t_start) * 1000

    return {
        "exercises": exercises,
        "total": len(exercises),
        "timing_ms": round(total_ms, 1),
        "safety_warnings": safety_warnings,
        "debug": {
            "embedding_ms": round(t_embed, 1),
            "wave_timing": wave_result.timing,
            "keywords": keywords,
            "candidates_before_safety": wave_result.total_candidates,
            "candidates_after_safety": len(candidate_ids),
        },
    }


def _extract_keywords(query_text: str, filters: Optional[Dict]) -> List[str]:
    """从查询文本和过滤条件中提取关键词（用于脉冲传播）

    简单实现：分词 + 过滤条件值。
    后续可接入 jieba 或 LLM 提取。
    """
    keywords = []

    # 从 filters 提取
    if filters:
        for key in ["muscle_group", "body_part", "equipment", "movement_type"]:
            val = filters.get(key)
            if val:
                if isinstance(val, list):
                    keywords.extend(val)
                else:
                    keywords.append(val)

    # 从查询文本提取（简单字符匹配）
    # 常见肌群/部位关键词
    muscle_keywords = [
        "胸", "背", "肩", "腿", "臀", "腹", "核心", "手臂", "二头", "三头",
        "胸大肌", "背阔肌", "三角肌", "股四头", "腘绳肌", "臀大肌",
        "腹直肌", "斜方肌", "竖脊肌", "小腿", "前臂",
        "chest", "back", "shoulder", "leg", "glute", "core", "arm",
    ]
    for kw in muscle_keywords:
        if kw in query_text.lower():
            keywords.append(kw)

    # 伤病关键词
    injury_keywords = [
        "腰椎", "膝盖", "肩袖", "颈椎", "腕管", "足底筋膜",
        "腰突", "腰间盘", "半月板", "十字韧带",
    ]
    for kw in injury_keywords:
        if kw in query_text:
            keywords.append(kw)

    return list(set(keywords))


# 肌群关键词 → 元数据中的肌群名称映射
_MUSCLE_KEYWORD_MAP = {
    "胸": "胸肌",
    "背": "背阔肌",
    "肩": "三角肌",
    "腿": "股四头肌",
    "臀": "臀大肌",
    "腹": "腹直肌",
    "核心": "腹直肌",
    "手臂": "肱二头肌",
    "二头": "肱二头肌",
    "三头": "肱三头肌",
    "小腿": "小腿",
    "前臂": "前臂",
    "胸大肌": "胸肌",
    "背阔肌": "背阔肌",
    "三角肌": "三角肌",
    "股四头": "股四头肌",
    "腘绳肌": "腘绳肌",
    "臀大肌": "臀大肌",
    "腹直肌": "腹直肌",
    "斜方肌": "斜方肌",
    "竖脊肌": "竖脊肌",
}


def _get_muscle_keywords(keywords: List[str]) -> List[str]:
    """从关键词列表中提取肌群相关的关键词"""
    muscles = []
    for kw in keywords:
        if kw in _MUSCLE_KEYWORD_MAP:
            muscles.append(kw)
    return muscles


def _muscle_rerank(
    candidate_ids: List[str],
    candidate_scores: Dict[str, float],
    muscle_keywords: List[str],
    metadata_store,
    id_to_payload: Dict[str, Dict] = None,
) -> List[str]:
    """肌群验证重排

    如果查询包含肌群关键词（如"胸"），则：
    - 目标肌群匹配的动作：保持原分
    - 目标肌群不匹配的动作：降权 50%

    这解决了"仰卧双膝抱胸"（下背部）排在胸肌动作前面的问题。
    """
    if not muscle_keywords:
        return candidate_ids

    # 构建目标肌群匹配集合
    target_muscles = set()
    for kw in muscle_keywords:
        mapped = _MUSCLE_KEYWORD_MAP.get(kw)
        if mapped:
            target_muscles.add(mapped)
        target_muscles.add(kw)  # 也保留原始关键词

    # 分为匹配组和不匹配组
    matched = []
    unmatched = []

    for eid in candidate_ids:
        # 优先从 payload 获取肌群信息
        muscles_primary = None
        if id_to_payload and eid in id_to_payload:
            muscles_primary = id_to_payload[eid].get("muscles_primary_zh", [])
        elif metadata_store:
            meta = metadata_store.get_exercise(eid)
            if meta:
                muscles_primary = meta.get("muscles_primary_zh", [])

        if muscles_primary is None:
            unmatched.append(eid)
            continue

        if isinstance(muscles_primary, str):
            muscles_primary = [muscles_primary]

        # 检查是否有任何目标肌群匹配
        is_match = False
        for muscle in muscles_primary:
            for target in target_muscles:
                if target in muscle or muscle in target:
                    is_match = True
                    break
            if is_match:
                break

        if is_match:
            matched.append(eid)
        else:
            unmatched.append(eid)

    # 匹配的排前面，不匹配的排后面（各自保持原有顺序）
    return matched + unmatched


def _apply_filters(
    candidate_ids: List[str],
    filters: Dict[str, Any],
    metadata_store,
    id_to_payload: Dict[str, Dict] = None,
) -> List[str]:
    """应用硬过滤条件"""
    filtered = []
    for eid in candidate_ids:
        # 优先从 payload 获取
        meta = None
        if id_to_payload and eid in id_to_payload:
            meta = id_to_payload[eid]
        elif metadata_store:
            meta = metadata_store.get_exercise(eid)

        if not meta:
            filtered.append(eid)  # 无元数据的保留
            continue

        match = True
        for key, val in filters.items():
            if key in ("muscle_group", "body_part", "equipment", "difficulty"):
                meta_val = meta.get(key, "")
                if isinstance(val, list):
                    if meta_val and meta_val not in val:
                        match = False
                        break
                else:
                    if meta_val and val and str(meta_val).lower() != str(val).lower():
                        match = False
                        break

        if match:
            filtered.append(eid)

    return filtered


def _build_safety_context(user_profile: Dict) -> Dict:
    """从用户档案构建安全检查上下文"""
    context = {}

    # 最近训练的肌群
    recent_workouts = user_profile.get("recent_workouts", [])
    if recent_workouts:
        recent_muscles = {}
        for workout in recent_workouts:
            muscles = workout.get("target_muscles", [])
            hours = workout.get("hours_ago", 999)
            for m in muscles:
                if m not in recent_muscles or hours < recent_muscles[m]:
                    recent_muscles[m] = hours
        context["recent_trained_muscles"] = recent_muscles

    return context
