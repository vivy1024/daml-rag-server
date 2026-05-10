# -*- coding: utf-8 -*-
"""
GraphConvRerank — 非参数图卷积重排序

基于 Non-parametric Graph Convolution for Re-ranking (RecSys 2025)。
在 test-time 对融合分数做图卷积传播，利用邻居信息提升排序质量。

核心公式：
  s_tilde_i = α * s_i + (1-α) * Σ_j∈N(i) w_ij * s_j / Σ_j w_ij

特点：
- 非参数化：不需要训练
- 低开销：<0.5% 额外推理时间
- 即插即用：叠加在 CalibratedFusion 之后

版本: 1.0.0
日期: 2026-05-11
论文: arXiv 2507.09969
代码参考: github.com/zyouyang/RecSys2025_NonParamGC
"""

import os
import math
import logging
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger(__name__)


def graph_conv_rerank(
    results: List[Dict[str, Any]],
    adjacency: Dict[str, List[Tuple[str, float]]],
    alpha: float = 0.8,
    K: int = 1,
    score_field: str = "fused_score",
    id_field: str = "id",
    max_neighbors: int = 20,
) -> List[Dict[str, Any]]:
    """
    非参数图卷积重排序
    
    Args:
        results: 融合后的结果列表 [{id, fused_score, ...}]
        adjacency: 动作邻接关系 {exercise_id: [(neighbor_id, weight)]}
        alpha: 自身分数权重（0.7-0.9，过低会过度平滑）
        K: 传播层数（1-2，我们的图较小用 1 层）
        score_field: 分数字段名
        id_field: ID 字段名
        max_neighbors: 每个节点最多考虑的邻居数
    
    Returns:
        重排序后的结果列表（按 reranked_score 降序）
    """
    if not results or not adjacency:
        return results

    # 构建 ID → score 映射
    score_map: Dict[str, float] = {}
    for r in results:
        eid = _get_id(r, id_field)
        if eid:
            score_map[eid] = r.get(score_field, r.get("score", 0.0))

    if not score_map:
        return results

    # K 轮图卷积传播
    current_scores = dict(score_map)

    for layer in range(K):
        new_scores: Dict[str, float] = {}

        for eid, score in current_scores.items():
            neighbors = adjacency.get(eid, [])[:max_neighbors]

            if not neighbors:
                # 无邻居：保持原分数
                new_scores[eid] = score
                continue

            # 计算邻居贡献（加权平均）
            neighbor_sum = 0.0
            weight_sum = 0.0

            for neighbor_id, edge_weight in neighbors:
                if neighbor_id in current_scores:
                    # Symmetric normalization: w / sqrt(deg_i * deg_j)
                    deg_i = len(adjacency.get(eid, []))
                    deg_j = len(adjacency.get(neighbor_id, []))
                    if deg_i > 0 and deg_j > 0:
                        norm_weight = edge_weight / math.sqrt(deg_i * deg_j)
                    else:
                        norm_weight = edge_weight

                    neighbor_sum += norm_weight * current_scores[neighbor_id]
                    weight_sum += norm_weight

            # 融合：α * self + (1-α) * neighbors
            if weight_sum > 0:
                neighbor_avg = neighbor_sum / weight_sum
                new_scores[eid] = alpha * score + (1 - alpha) * neighbor_avg
            else:
                new_scores[eid] = score

        current_scores = new_scores

    # 将重排序分数写回结果
    for r in results:
        eid = _get_id(r, id_field)
        if eid and eid in current_scores:
            r["reranked_score"] = round(current_scores[eid], 6)
            r["_gc_boost"] = round(current_scores[eid] - score_map.get(eid, 0.0), 6)

    # 按重排序分数降序排列
    results.sort(key=lambda r: r.get("reranked_score", r.get(score_field, 0.0)), reverse=True)

    logger.debug(
        f"[GraphConvRerank] K={K}, α={alpha}, "
        f"items={len(results)}, "
        f"avg_boost={sum(r.get('_gc_boost', 0) for r in results) / max(len(results), 1):.4f}"
    )

    return results


def get_graph_conv_config() -> Dict[str, Any]:
    """从环境变量读取配置"""
    return {
        "enabled": os.getenv("ENABLE_GRAPH_CONV_RERANK", "true").lower() == "true",
        "alpha": float(os.getenv("GRAPH_CONV_ALPHA", "0.8")),
        "K": int(os.getenv("GRAPH_CONV_LAYERS", "1")),
        "max_neighbors": int(os.getenv("GRAPH_CONV_MAX_NEIGHBORS", "20")),
    }


def _get_id(result: Dict[str, Any], id_field: str) -> str:
    """从结果中提取 ID"""
    for field in [id_field, "id", "exercise_id", "name"]:
        val = result.get(field)
        if val:
            return str(val)
    return ""
