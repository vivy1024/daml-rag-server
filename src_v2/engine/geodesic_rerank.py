"""
测地线重排 + SVD 去重

从 Wave Memory 移植，适配健身场景：
- 时间衰减 → 替换为"用户历史偏好衰减"（最近用过的动作降权）
- SVD 去重：正交化选择，避免推荐多个高度相似的动作
"""

import logging
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


def geodesic_rerank(
    candidates: List[Tuple[str, float]],
    vectors: Dict[str, np.ndarray],
    diversity_threshold: float = 0.3,
    max_results: int = 20,
    recent_used: List[str] = None,
    recent_decay: float = 0.7,
) -> List[Tuple[str, float]]:
    """测地线重排 + SVD 去重

    Args:
        candidates: [(item_id, score)] 按分数降序
        vectors: {item_id: vector} 候选的向量
        diversity_threshold: SVD 去重阈值（残差 < 此值则跳过）
        max_results: 最大返回数
        recent_used: 最近使用过的动作 ID（降权）
        recent_decay: 最近使用的衰减系数

    Returns:
        [(item_id, adjusted_score)] 去重后的结果
    """
    if not candidates:
        return []

    recent_set = set(recent_used) if recent_used else set()

    # 1. 应用历史衰减
    adjusted = []
    for item_id, score in candidates:
        if item_id in recent_set:
            score *= recent_decay
        adjusted.append((item_id, score))

    # 2. SVD 去重（贪心正交化选择）
    selected = []
    selected_vecs = []

    for item_id, score in adjusted:
        vec = vectors.get(item_id)
        if vec is None:
            # 没有向量的直接加入
            selected.append((item_id, score))
            continue

        vec = vec.astype(np.float32)
        norm = np.linalg.norm(vec)
        if norm < 1e-8:
            selected.append((item_id, score))
            continue

        vec_normalized = vec / norm

        if selected_vecs:
            # 计算在已选向量子空间中的残差
            basis = np.vstack(selected_vecs)  # (k, dim)
            # 投影系数
            proj_coeffs = basis @ vec_normalized  # (k,)
            projection = proj_coeffs @ basis  # (dim,)
            residual = vec_normalized - projection
            residual_norm = np.linalg.norm(residual)

            # 残差太小 = 与已选内容太相似
            if residual_norm < diversity_threshold:
                logger.debug(f"SVD dedup: skipping {item_id} (residual={residual_norm:.3f})")
                continue

        # 选中
        selected.append((item_id, score))
        selected_vecs.append(vec_normalized.reshape(1, -1))

        if len(selected) >= max_results:
            break

    return selected
