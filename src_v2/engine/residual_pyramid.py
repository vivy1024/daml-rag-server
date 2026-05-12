"""残差金字塔 (Residual Pyramid)

移植自 Wave Memory (vivy1024/astrbot_plugin_wave_memory)，
适配健身检索场景。

核心思路：对查询向量进行逐层 Gram-Schmidt 正交分解，
每层捕获"已有基底解释不了的残差"。残差中包含的新信息
可用于发现用户查询中超出常规语义空间的独特需求。
"""

import logging
from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 默认参数
# ---------------------------------------------------------------------------
DEFAULT_ENERGY_THRESHOLD = 0.01  # 残差能量占比低于此值时停止分解
DEFAULT_MAX_LEVELS = 16  # 最大分解层数（防止无限循环）


@dataclass
class PyramidResult:
    """残差金字塔分解结果。"""

    levels: List[np.ndarray] = field(repr=False)  # 各层残差向量
    coverage: float  # 已解释的方差比例 (0-1)
    novelty: float  # 残差中的新信息量 (0-1)


def _gram_schmidt_project(vec: np.ndarray, basis: np.ndarray) -> np.ndarray:
    """将 vec 投影到 basis 张成的子空间上。

    Args:
        vec: 待投影向量，形状 (D,)。
        basis: 基底矩阵，形状 (K, D)，各行应近似正交。

    Returns:
        投影向量，形状 (D,)。
    """
    if basis.shape[0] == 0:
        return np.zeros_like(vec)

    # 投影系数
    coeffs = basis @ vec  # (K,)
    projection = coeffs @ basis  # (D,)
    return projection


def decompose_residual_pyramid(
    query_vec: np.ndarray,
    pca_basis: np.ndarray,
    energy_threshold: float = DEFAULT_ENERGY_THRESHOLD,
    max_levels: int = DEFAULT_MAX_LEVELS,
) -> PyramidResult:
    """执行残差金字塔分解。

    逐层将查询向量分解为：可被当前基底解释的部分 + 残差。
    每层使用 Gram-Schmidt 正交化确保残差与已用基底正交。

    分解策略：
    - Level 0: 使用前 N/4 个基底（最主要的语义方向）
    - Level 1: 使用 N/4 ~ N/2 基底
    - Level 2: 使用 N/2 ~ 3N/4 基底
    - Level 3: 使用剩余基底
    - 后续层：对残差做自正交化（捕获完全新颖的方向）

    Args:
        query_vec: 查询向量，形状 (D,)。
        pca_basis: PCA 基底矩阵，形状 (K, D)，按方差贡献降序排列。
        energy_threshold: 残差能量占比低于此值时停止。
        max_levels: 最大分解层数。

    Returns:
        PyramidResult 包含各层残差、覆盖率和新颖度。
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
    original_energy = np.dot(query_vec, query_vec)
    if original_energy < 1e-12:
        logger.warning("残差金字塔: 输入为零向量")
        return PyramidResult(levels=[], coverage=0.0, novelty=0.0)

    # ------ 分层基底划分 ------
    chunk_size = max(1, k // 4)
    basis_chunks: List[np.ndarray] = []
    for i in range(0, k, chunk_size):
        basis_chunks.append(pca_basis[i : i + chunk_size])

    # ------ 逐层分解 ------
    levels: List[np.ndarray] = []
    residual = query_vec.copy()
    explained_energy = 0.0

    for level_idx in range(min(len(basis_chunks) + max_levels, max_levels)):
        residual_energy = np.dot(residual, residual)
        energy_ratio = residual_energy / original_energy

        # 能量截断
        if energy_ratio < energy_threshold:
            logger.debug(
                "残差金字塔: Level %d 能量比 %.4f < 阈值，停止",
                level_idx,
                energy_ratio,
            )
            break

        if level_idx < len(basis_chunks):
            # 使用预定义基底块
            basis_chunk = basis_chunks[level_idx]
            projection = _gram_schmidt_project(residual, basis_chunk)
        else:
            # 超出基底范围：残差本身就是新信息，记录后停止
            levels.append(residual.copy())
            break

        # 计算本层残差
        new_residual = residual - projection
        layer_explained = np.dot(projection, projection)
        explained_energy += layer_explained

        # 记录本层的投影分量（被解释的部分）
        if np.linalg.norm(projection) > 1e-12:
            levels.append(projection)

        residual = new_residual

    # ------ 最终残差作为最后一层 ------
    final_residual_energy = np.dot(residual, residual)
    if final_residual_energy / original_energy >= energy_threshold:
        if len(levels) == 0 or not np.allclose(levels[-1], residual):
            levels.append(residual.copy())

    # ------ 计算覆盖率和新颖度 ------
    coverage = float(explained_energy / original_energy)
    coverage = min(coverage, 1.0)  # 数值稳定性

    # 新颖度 = 未被基底解释的能量比例
    novelty = float(final_residual_energy / original_energy)
    novelty = float(np.clip(novelty, 0.0, 1.0))

    logger.debug(
        "残差金字塔完成: %d 层, coverage=%.3f, novelty=%.3f",
        len(levels),
        coverage,
        novelty,
    )

    return PyramidResult(
        levels=levels,
        coverage=coverage,
        novelty=novelty,
    )
