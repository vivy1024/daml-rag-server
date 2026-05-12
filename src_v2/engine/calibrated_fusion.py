"""
CalibratedFusion — 校准融合

将向量检索分数和图谱关系分数通过 PIT + Boltzmann 校准后加权融合。
从旧代码 src/framework/retrieval/three_layer/calibrated_fusion.py 精简移植。
"""

import math
import logging
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

EPSILON = 1e-6


def pit_normalize(scores: List[float]) -> List[float]:
    """Percentile-Rank Transform: 映射到 [0,1] 均匀分布"""
    n = len(scores)
    if n == 0:
        return []
    if n == 1:
        return [1.0]

    indexed = sorted(enumerate(scores), key=lambda x: x[1])
    percentiles = [0.0] * n
    for rank, (original_idx, _) in enumerate(indexed):
        percentiles[original_idx] = (rank + 1) / n
    return percentiles


def scores_to_probabilities(scores: List[float]) -> List[float]:
    """PIT → Energy → Temperature → Boltzmann Probabilities"""
    if not scores:
        return []

    # PIT
    percentiles = pit_normalize(scores)

    # Energy: E_i = -ln(p_hat_i + ε)
    energies = [-math.log(p + EPSILON) for p in percentiles]

    # Temperature: T = mean(E) / 2
    mean_e = sum(energies) / len(energies)
    temperature = max(mean_e / 2.0, 0.01)

    # Boltzmann: P_i = exp(-E_i / T) / Z
    max_neg = max(-e / temperature for e in energies)
    raw = [math.exp(-e / temperature - max_neg) for e in energies]
    z = sum(raw)

    if z == 0:
        return [1.0 / len(scores)] * len(scores)
    return [r / z for r in raw]


def calibrated_fusion(
    vector_scores: Dict[str, float],
    graph_scores: Dict[str, float],
    alpha: float = 0.6,
    consensus_boost: float = 0.1,
    min_for_pit: int = 3,
) -> List[Tuple[str, float]]:
    """校准融合主函数

    Args:
        vector_scores: {item_id: cosine_similarity}
        graph_scores: {item_id: graph_relation_score}
        alpha: 向量权重（1-alpha = 图谱权重）
        consensus_boost: 两源都命中的额外加分
        min_for_pit: PIT 最少需要的结果数

    Returns:
        [(item_id, fused_score)] 按分数降序
    """
    all_ids = set(vector_scores.keys()) | set(graph_scores.keys())
    if not all_ids:
        return []

    # 分数太少时退化为简单加权
    v_list = list(vector_scores.values())
    g_list = list(graph_scores.values())

    if len(v_list) >= min_for_pit:
        v_ids = list(vector_scores.keys())
        v_probs = scores_to_probabilities(v_list)
        v_prob_map = dict(zip(v_ids, v_probs))
    else:
        # 简单归一化
        max_v = max(v_list) if v_list else 1.0
        v_prob_map = {k: v / max(max_v, EPSILON) for k, v in vector_scores.items()}

    if len(g_list) >= min_for_pit:
        g_ids = list(graph_scores.keys())
        g_probs = scores_to_probabilities(g_list)
        g_prob_map = dict(zip(g_ids, g_probs))
    else:
        max_g = max(g_list) if g_list else 1.0
        g_prob_map = {k: v / max(max_g, EPSILON) for k, v in graph_scores.items()}

    # 融合
    consensus_ids = set(vector_scores.keys()) & set(graph_scores.keys())
    results = []

    for item_id in all_ids:
        v_score = v_prob_map.get(item_id, 0.0)
        g_score = g_prob_map.get(item_id, 0.0)
        fused = alpha * v_score + (1 - alpha) * g_score

        # Consensus boost
        if item_id in consensus_ids:
            fused += consensus_boost

        results.append((item_id, fused))

    # 按分数降序
    results.sort(key=lambda x: x[1], reverse=True)
    return results
