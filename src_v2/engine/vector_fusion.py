"""向量融合 (Vector Fusion)

将查询向量、Spike 向量、用户画像偏置向量和残差信号
进行加权融合，生成最终的检索向量。

融合权重：
- α=0.7  查询本身（主导）
- β=0.15 Spike 向量（近期兴趣突变）
- γ=0.15 用户画像偏置（长期偏好）
- δ 动态  残差增强（基于 EPA novelty 调整）
"""

import logging
from dataclasses import dataclass
from typing import List, Optional

import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 默认融合权重
# ---------------------------------------------------------------------------
DEFAULT_ALPHA = 0.70  # 查询向量权重
DEFAULT_BETA = 0.15  # Spike 向量权重
DEFAULT_GAMMA = 0.15  # 用户画像偏置权重
DEFAULT_DELTA_MAX = 0.10  # 残差增强最大权重（由 novelty 动态缩放）


@dataclass
class FusionConfig:
    """融合参数配置。"""

    alpha: float = DEFAULT_ALPHA
    beta: float = DEFAULT_BETA
    gamma: float = DEFAULT_GAMMA
    delta_max: float = DEFAULT_DELTA_MAX


def _safe_normalize(vec: np.ndarray) -> np.ndarray:
    """安全归一化为单位向量，零向量返回自身。"""
    norm = np.linalg.norm(vec)
    if norm < 1e-12:
        return vec
    return vec / norm


def _aggregate_residuals(residual_signals: List[np.ndarray]) -> np.ndarray:
    """聚合多层残差信号为单一增强向量。

    策略：按层级递减加权求和（浅层残差权重更高）。
    """
    if not residual_signals:
        return np.array([])

    dim = residual_signals[0].shape[0]
    aggregated = np.zeros(dim, dtype=np.float64)

    for i, signal in enumerate(residual_signals):
        if signal.shape[0] != dim:
            logger.warning(
                "残差信号维度不一致: 期望 %d, 实际 %d, 跳过第 %d 层",
                dim,
                signal.shape[0],
                i,
            )
            continue
        # 指数衰减权重：第 0 层权重 1.0, 第 1 层 0.5, 第 2 层 0.25 ...
        weight = 0.5 ** i
        aggregated += weight * signal

    return aggregated


def fuse_vectors(
    query_vec: np.ndarray,
    spike_vec: Optional[np.ndarray] = None,
    profile_bias_vec: Optional[np.ndarray] = None,
    residual_signals: Optional[List[np.ndarray]] = None,
    novelty: float = 0.0,
    config: Optional[FusionConfig] = None,
) -> np.ndarray:
    """执行向量融合，生成最终检索向量。

    融合公式：
        fused = normalize(α×query + β×spike + γ×profile + δ×residual_boost)
        其中 δ = delta_max × novelty

    Args:
        query_vec: 查询向量，形状 (D,)。必须提供。
        spike_vec: Spike 向量（近期兴趣突变），形状 (D,)。
            None 或零向量时不参与融合。
        profile_bias_vec: 用户画像偏置向量，形状 (D,)。
            None 或零向量时不参与融合。
        residual_signals: 残差金字塔各层向量列表。
            None 或空列表时不参与融合。
        novelty: EPA 分析得到的新颖度 (0-1)，用于动态调整残差权重。
        config: 融合参数配置，None 时使用默认值。

    Returns:
        融合后的单位向量，形状 (D,)。

    Raises:
        ValueError: query_vec 为空或维度为 0 时抛出。
    """
    if config is None:
        config = FusionConfig()

    # ------ 输入校验 ------
    query_vec = np.asarray(query_vec, dtype=np.float64).flatten()
    if query_vec.shape[0] == 0:
        raise ValueError("query_vec 不能为空")

    dim = query_vec.shape[0]

    # ------ 零查询向量处理 ------
    if np.linalg.norm(query_vec) < 1e-12:
        logger.warning("向量融合: 查询向量为零向量")
        return np.zeros(dim, dtype=np.float64)

    # ------ 准备各分量 ------
    # 归一化查询向量
    query_norm = _safe_normalize(query_vec)

    # Spike 向量
    has_spike = False
    if spike_vec is not None:
        spike_vec = np.asarray(spike_vec, dtype=np.float64).flatten()
        if spike_vec.shape[0] == dim and np.linalg.norm(spike_vec) > 1e-12:
            spike_norm = _safe_normalize(spike_vec)
            has_spike = True

    # 用户画像偏置
    has_profile = False
    if profile_bias_vec is not None:
        profile_bias_vec = np.asarray(profile_bias_vec, dtype=np.float64).flatten()
        if (
            profile_bias_vec.shape[0] == dim
            and np.linalg.norm(profile_bias_vec) > 1e-12
        ):
            profile_norm = _safe_normalize(profile_bias_vec)
            has_profile = True

    # 残差增强
    has_residual = False
    residual_boost = np.zeros(dim, dtype=np.float64)
    if residual_signals and len(residual_signals) > 0:
        aggregated = _aggregate_residuals(residual_signals)
        if aggregated.shape[0] == dim and np.linalg.norm(aggregated) > 1e-12:
            residual_boost = _safe_normalize(aggregated)
            has_residual = True

    # ------ 动态权重计算 ------
    alpha = config.alpha
    beta = config.beta if has_spike else 0.0
    gamma = config.gamma if has_profile else 0.0
    delta = config.delta_max * float(np.clip(novelty, 0.0, 1.0)) if has_residual else 0.0

    # 缺失分量时将权重回收到查询向量
    unused_weight = 0.0
    if not has_spike:
        unused_weight += config.beta
    if not has_profile:
        unused_weight += config.gamma
    if not has_residual:
        unused_weight += config.delta_max * float(np.clip(novelty, 0.0, 1.0))

    alpha += unused_weight

    # ------ 加权融合 ------
    fused = alpha * query_norm

    if has_spike:
        fused += beta * spike_norm

    if has_profile:
        fused += gamma * profile_norm

    if has_residual:
        fused += delta * residual_boost

    # ------ 归一化输出 ------
    result = _safe_normalize(fused)

    logger.debug(
        "向量融合完成: α=%.2f, β=%.2f, γ=%.2f, δ=%.3f, "
        "spike=%s, profile=%s, residual=%s",
        alpha,
        beta,
        gamma,
        delta,
        has_spike,
        has_profile,
        has_residual,
    )

    return result
