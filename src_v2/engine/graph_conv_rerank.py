"""
GraphConvRerank — 图卷积重排

测试时图卷积：利用候选集内的图谱邻接关系，平滑分数。
s'_i = α × s_i + (1-α) × mean(s_j for j in neighbors(i) ∩ candidates)

效果：如果一个动作的邻居（共享肌群的动作）也在候选集中且分数高，
则该动作的分数会被提升。反之，孤立的候选会被轻微降权。
"""

import logging
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)


def graph_conv_rerank(
    candidates: List[Tuple[str, float]],
    adjacency: Dict[str, List[Tuple[str, float]]],
    alpha: float = 0.8,
) -> List[Tuple[str, float]]:
    """图卷积重排

    Args:
        candidates: [(item_id, score)] 候选列表
        adjacency: {item_id: [(neighbor_id, weight)]} 邻接表
        alpha: 自身分数权重（1-alpha = 邻居平均分权重）

    Returns:
        [(item_id, smoothed_score)] 重排后的列表
    """
    if not candidates or alpha >= 1.0:
        return candidates

    # 构建候选集内的分数映射
    score_map = {item_id: score for item_id, score in candidates}
    candidate_set = set(score_map.keys())

    results = []
    for item_id, original_score in candidates:
        # 找到在候选集内的邻居
        neighbors = adjacency.get(item_id, [])
        neighbor_scores = []

        for neighbor_id, weight in neighbors:
            if neighbor_id in candidate_set:
                neighbor_scores.append(score_map[neighbor_id] * weight)

        # 图卷积
        if neighbor_scores:
            neighbor_mean = sum(neighbor_scores) / len(neighbor_scores)
            smoothed = alpha * original_score + (1 - alpha) * neighbor_mean
        else:
            smoothed = original_score

        results.append((item_id, smoothed))

    # 按分数降序
    results.sort(key=lambda x: x[1], reverse=True)
    return results
