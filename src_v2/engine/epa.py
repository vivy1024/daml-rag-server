"""EPA — 嵌入投影分析 (Embedding Projection Analysis)

移植自 Wave Memory (vivy1024/astrbot_plugin_wave_memory) 的 EPA 模块，
适配健身检索场景（1024 维 GTE-Large-zh 向量）。

核心思路：将查询向量投影到预计算的 PCA 基底上，通过投影系数的分布
特征来量化查询的复杂度、信息熵和主要语义方向。
"""

import logging
from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 默认参数
# ---------------------------------------------------------------------------
DEFAULT_EMBEDDING_DIM = 1024
DEFAULT_PCA_COMPONENTS = 32
DOMINANT_AXIS_THRESHOLD = 0.15  # 投影系数占比超过此值视为主要方向


@dataclass
class EPAResult:
    """EPA 分析结果。"""

    logic_depth: float  # 0-1, 越高表示查询越复杂
    entropy: float  # 信息熵（基于投影系数分布）
    dominant_axes: List[int]  # 主要语义方向的索引
    projection_coeffs: np.ndarray = field(repr=False)  # 投影系数向量


def _safe_normalize(vec: np.ndarray) -> np.ndarray:
    """安全归一化，零向量返回自身。"""
    norm = np.linalg.norm(vec)
    if norm < 1e-12:
        return vec
    return vec / norm


def _compute_logic_depth(coeffs: np.ndarray) -> float:
    """计算逻辑深度 — 基于投影分布的集中度。

    集中度越低（能量分散在更多轴上），逻辑深度越高，
    表示查询涉及更多语义维度，复杂度更高。

    使用归一化基尼系数的补数：
    - 能量集中在少数轴 → 基尼高 → depth 低
    - 能量均匀分散 → 基尼低 → depth 高
    """
    abs_coeffs = np.abs(coeffs)
    total = abs_coeffs.sum()
    if total < 1e-12:
        return 0.0

    n = len(abs_coeffs)
    if n <= 1:
        return 0.0

    # 排序后计算基尼系数
    sorted_coeffs = np.sort(abs_coeffs)
    index = np.arange(1, n + 1)
    gini = (2.0 * np.sum(index * sorted_coeffs) / (n * total)) - (n + 1) / n

    # 补数映射到 [0, 1]
    depth = 1.0 - gini
    return float(np.clip(depth, 0.0, 1.0))


def _compute_entropy(coeffs: np.ndarray) -> float:
    """计算信息熵 — 基于投影系数的概率分布。

    将系数平方归一化为概率分布，再计算 Shannon 熵。
    """
    squared = coeffs ** 2
    total = squared.sum()
    if total < 1e-12:
        return 0.0

    probs = squared / total
    # 过滤零概率避免 log(0)
    probs = probs[probs > 1e-12]
    entropy = -np.sum(probs * np.log2(probs))
    return float(entropy)


def _find_dominant_axes(
    coeffs: np.ndarray, threshold: float = DOMINANT_AXIS_THRESHOLD
) -> List[int]:
    """找出主要语义方向 — 投影能量占比超过阈值的轴。"""
    squared = coeffs ** 2
    total = squared.sum()
    if total < 1e-12:
        return []

    ratios = squared / total
    indices = np.where(ratios >= threshold)[0]
    # 按能量占比降序排列
    sorted_idx = indices[np.argsort(-ratios[indices])]
    return sorted_idx.tolist()


def compute_epa(
    query_vec: np.ndarray,
    pca_basis: np.ndarray,
    dominant_threshold: float = DOMINANT_AXIS_THRESHOLD,
) -> EPAResult:
    """执行 EPA 嵌入投影分析。

    Args:
        query_vec: 查询向量，形状 (D,)，D 通常为 1024。
        pca_basis: PCA 基底矩阵，形状 (K, D)，K 为主成分数（默认 32）。
        dominant_threshold: 主要方向的能量占比阈值。

    Returns:
        EPAResult 包含逻辑深度、信息熵、主要方向和投影系数。

    Raises:
        ValueError: 维度不匹配时抛出。
    """
    # ------ 输入校验 ------
    query_vec = np.asarray(query_vec, dtype=np.float64).flatten()
    pca_basis = np.asarray(pca_basis, dtype=np.float64)

    if pca_basis.ndim != 2:
        raise ValueError(
            f"pca_basis 应为 2D 矩阵，实际为 {pca_basis.ndim}D"
        )

    k, d = pca_basis.shape
    if query_vec.shape[0] != d:
        raise ValueError(
            f"维度不匹配：query_vec({query_vec.shape[0]}) vs pca_basis({d})"
        )

    # ------ 零向量处理 ------
    if np.linalg.norm(query_vec) < 1e-12:
        logger.warning("EPA: 输入为零向量，返回空结果")
        return EPAResult(
            logic_depth=0.0,
            entropy=0.0,
            dominant_axes=[],
            projection_coeffs=np.zeros(k),
        )

    # ------ 投影计算 ------
    # coeffs[i] = query_vec · pca_basis[i]
    projection_coeffs = pca_basis @ query_vec  # shape: (K,)

    # ------ 指标计算 ------
    logic_depth = _compute_logic_depth(projection_coeffs)
    entropy = _compute_entropy(projection_coeffs)
    dominant_axes = _find_dominant_axes(projection_coeffs, dominant_threshold)

    logger.debug(
        "EPA 完成: depth=%.3f, entropy=%.3f, dominant_axes=%s",
        logic_depth,
        entropy,
        dominant_axes,
    )

    return EPAResult(
        logic_depth=logic_depth,
        entropy=entropy,
        dominant_axes=dominant_axes,
        projection_coeffs=projection_coeffs,
    )
