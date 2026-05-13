"""
MCP 工具: search_knowledge — 训练知识检索
MCP 工具: search_foods — 食物营养检索
MCP 工具: get_food_detail — 食物详情
MCP 工具: get_strength_standards — 力量标准查询

复用 WaveEngine 的 domain 参数切换检索领域。
"""

import logging
import time
from typing import Any, Dict, List, Optional

import numpy as np

from ..engine.wave_engine import WaveEngine
from ..data.loader import DataStore
from .embedding import encode_query

logger = logging.getLogger(__name__)


# === search_knowledge ===

async def search_knowledge(
    query_text: str,
    top_k: int = 5,
    *,
    wave_engine: WaveEngine,
) -> Dict[str, Any]:
    """搜索训练知识库

    Args:
        query_text: 查询文本（如"渐进超负荷原则"、"如何安排休息日"）
        top_k: 返回数量
        wave_engine: WaveEngine 实例

    Returns:
        {
            "results": [{title, content, source, score}],
            "total": int,
            "timing_ms": float,
        }
    """
    t_start = time.time()

    # Embedding
    query_vec = encode_query(query_text)

    # WaveEngine 检索（knowledge 领域不走安全过滤和图谱加分）
    wave_result = await wave_engine.search(
        query_vec=query_vec,
        domain="knowledge",
        top_k=top_k,
    )

    # 格式化结果
    results = []
    for item in wave_result.results[:top_k]:
        payload = item.get("payload", {})
        results.append({
            "title": payload.get("title", payload.get("chunk_title", "")),
            "content": payload.get("content", payload.get("text", "")),
            "source": payload.get("source", payload.get("document_name", "")),
            "category": payload.get("category", ""),
            "score": round(item["score"], 4),
        })

    timing_ms = (time.time() - t_start) * 1000

    return {
        "results": results,
        "total": len(results),
        "timing_ms": round(timing_ms, 1),
    }


# === search_foods ===

async def search_foods(
    query_text: str,
    top_k: int = 10,
    *,
    wave_engine: WaveEngine,
) -> Dict[str, Any]:
    """搜索食物营养数据

    Args:
        query_text: 查询文本（如"高蛋白食物"、"鸡胸肉"、"低GI碳水"）
        top_k: 返回数量
        wave_engine: WaveEngine 实例

    Returns:
        {
            "foods": [{name, category, energy_kcal, protein, fat, carbohydrate, score}],
            "total": int,
            "timing_ms": float,
        }
    """
    t_start = time.time()

    query_vec = encode_query(query_text)

    wave_result = await wave_engine.search(
        query_vec=query_vec,
        domain="foods",
        top_k=top_k,
    )

    foods = []
    for item in wave_result.results[:top_k]:
        payload = item.get("payload", {})
        foods.append({
            "name": payload.get("name", ""),
            "category": payload.get("category", ""),
            "energy_kcal": payload.get("energy_kcal", payload.get("energy", 0)),
            "protein": payload.get("protein", 0),
            "fat": payload.get("fat", 0),
            "carbohydrate": payload.get("carbohydrate", payload.get("carbs", 0)),
            "fiber": payload.get("fiber", 0),
            "score": round(item["score"], 4),
        })

    timing_ms = (time.time() - t_start) * 1000

    return {
        "foods": foods,
        "total": len(foods),
        "timing_ms": round(timing_ms, 1),
    }


# === get_food_detail ===

def get_food_detail(
    food_id: str,
    *,
    data_store: DataStore,
) -> Dict[str, Any]:
    """获取食物详细营养信息

    Args:
        food_id: 食物节点 ID
        data_store: DataStore 实例

    Returns:
        完整营养成分数据
    """
    # 从元数据获取
    meta = data_store.metadata.get_node(food_id)
    if not meta:
        return {"error": f"食物 {food_id} 不存在"}

    # 从图谱获取营养素关系
    nutrient_edges = data_store.graph.get_relations(food_id, "CONTAINS_NUTRIENT")
    nutrients = []
    for edge in nutrient_edges:
        nutrient_meta = data_store.metadata.get_node(edge["target"])
        if nutrient_meta:
            nutrients.append({
                "name": nutrient_meta.get("name", edge.get("target_name_zh", "")),
                "amount": edge.get("props", {}).get("amount", 0),
                "unit": edge.get("props", {}).get("unit", "g"),
            })

    return {
        "id": food_id,
        "name": meta.get("name", ""),
        "category": meta.get("category", ""),
        "energy_kcal": meta.get("energy_kcal", meta.get("energy", 0)),
        "protein": meta.get("protein", 0),
        "fat": meta.get("fat", 0),
        "carbohydrate": meta.get("carbohydrate", 0),
        "fiber": meta.get("fiber", 0),
        "sodium": meta.get("sodium", 0),
        "nutrients": nutrients,
        "per_100g": True,
    }


# === get_strength_standards ===

def get_strength_standards(
    exercise_name: str = None,
    level: str = None,
    gender: str = None,
    body_weight: float = None,
    *,
    data_store: DataStore,
) -> Dict[str, Any]:
    """查询力量标准

    Args:
        exercise_name: 动作名称（如"卧推"、"深蹲"）
        level: 训练水平（beginner/novice/intermediate/advanced/elite）
        gender: 性别（male/female）
        body_weight: 体重（kg）
        data_store: DataStore 实例

    Returns:
        匹配的力量标准列表
    """
    # 从图谱中查找 StrengthStandard 节点
    standards = []

    for nid, node_data in data_store.graph._graph.items():
        if node_data.get("_label") != "StrengthStandard":
            continue

        meta = data_store.metadata.get_node(nid)
        if not meta:
            continue

        # 过滤条件
        if exercise_name:
            node_exercise = meta.get("exercise_name", "")
            if exercise_name.lower() not in node_exercise.lower():
                continue

        if level:
            node_level = meta.get("level", "")
            if level.lower() != node_level.lower():
                continue

        if gender:
            node_gender = meta.get("gender", "")
            if gender.lower() != node_gender.lower():
                continue

        standards.append({
            "id": nid,
            "exercise_name": meta.get("exercise_name", ""),
            "level": meta.get("level", ""),
            "gender": meta.get("gender", ""),
            "body_weight_kg": meta.get("body_weight_kg", 0),
            "standard_weight_kg": meta.get("standard_weight_kg", 0),
            "ratio": meta.get("ratio", 0),  # 标准重量/体重
        })

    # 如果指定了体重，按最接近的排序
    if body_weight and standards:
        standards.sort(
            key=lambda s: abs(s.get("body_weight_kg", 0) - body_weight)
        )

    return {
        "standards": standards[:20],
        "total": len(standards),
        "filters_applied": {
            "exercise_name": exercise_name,
            "level": level,
            "gender": gender,
            "body_weight": body_weight,
        },
    }
