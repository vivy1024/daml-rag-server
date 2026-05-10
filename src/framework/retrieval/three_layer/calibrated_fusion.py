# -*- coding: utf-8 -*-
"""
CalibratedFusion — 校准融合模块

基于 PhaseGraph 论文 (arXiv 2603.28886) 的分数校准融合方法。
解决 Layer 1 (向量 cosine) 和 Layer 2 (图谱关系) 分数不可比的问题。

算法步骤：
1. PIT 归一化：将两种分数映射到 [0,1] 均匀分布
2. Boltzmann Energy：转换为能量值
3. 自适应 Temperature：T = mean(E) / 2
4. Boltzmann Probabilities：计算归一化概率
5. Weighted Fusion：加权融合 + consensus boost

版本: 1.0.0
日期: 2026-05-11
论文: Calibrated Fusion for Heterogeneous Graph-Vector Retrieval (2026)
"""

import math
import logging
import os
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

EPSILON = 1e-6


@dataclass
class FusionConfig:
    """融合配置"""
    alpha: float = 0.6          # 向量权重（0=纯图谱, 1=纯向量）
    beta: float = 1.0           # consensus boost（两源都命中的额外加分）
    enabled: bool = True        # feature flag
    min_results_for_pit: int = 3  # PIT 归一化最少需要的结果数


def get_fusion_config() -> FusionConfig:
    """从环境变量读取配置"""
    return FusionConfig(
        alpha=float(os.getenv("CALIBRATED_FUSION_ALPHA", "0.6")),
        beta=float(os.getenv("CALIBRATED_FUSION_BETA", "1.0")),
        enabled=os.getenv("ENABLE_CALIBRATED_FUSION", "true").lower() == "true",
        min_results_for_pit=int(os.getenv("CALIBRATED_FUSION_MIN_RESULTS", "3")),
    )


def pit_normalize(scores: List[float]) -> List[float]:
    """
    Percentile-Rank Transform (PIT)
    将分数映射到 [0,1] 均匀分布（经验 CDF）
    
    p_hat_i = |{j: s_j <= s_i}| / N
    """
    n = len(scores)
    if n == 0:
        return []
    if n == 1:
        return [1.0]
    
    # 排序获取排名
    indexed = sorted(enumerate(scores), key=lambda x: x[1])
    percentiles = [0.0] * n
    
    for rank, (original_idx, _) in enumerate(indexed):
        percentiles[original_idx] = (rank + 1) / n
    
    return percentiles


def compute_energies(percentiles: List[float]) -> List[float]:
    """
    Boltzmann Energy
    E_i = -ln(p_hat_i + epsilon)
    
    高排名 → 高 percentile → 低 energy
    """
    return [-math.log(p + EPSILON) for p in percentiles]


def compute_temperature(energies: List[float]) -> float:
    """
    自适应 Temperature
    T = mean(E) / 2
    
    论文消融实验：自适应 T 优于固定 T
    """
    if not energies:
        return 1.0
    mean_e = sum(energies) / len(energies)
    t = mean_e / 2.0
    return max(t, 0.01)  # 避免除零


def boltzmann_probabilities(energies: List[float], temperature: float) -> List[float]:
    """
    Boltzmann Probabilities
    P_i = exp(-E_i / T) / Z
    """
    if not energies:
        return []
    
    # 数值稳定：减去最大值
    max_neg_e_over_t = max(-e / temperature for e in energies)
    raw = [math.exp(-e / temperature - max_neg_e_over_t) for e in energies]
    z = sum(raw)
    
    if z == 0:
        return [1.0 / len(energies)] * len(energies)
    
    return [r / z for r in raw]


def calibrated_fusion(
    layer1_results: List[Dict[str, Any]],
    layer2_results: List[Dict[str, Any]],
    config: FusionConfig = None,
    id_field: str = "id",
    score_field: str = "score",
) -> List[Dict[str, Any]]:
    """
    校准融合主函数
    
    将 Layer 1 (向量检索) 和 Layer 2 (图谱检索) 的结果
    通过 PIT + Boltzmann 校准后加权融合。
    
    Args:
        layer1_results: 向量检索结果 [{id, score, ...}]
        layer2_results: 图谱检索结果 [{id, score, ...}]
        config: 融合配置
        id_field: 结果中的 ID 字段名
        score_field: 结果中的分数字段名
    
    Returns:
        融合后的结果列表，按 fused_score 降序排列
    """
    if config is None:
        config = get_fusion_config()
    
    if not config.enabled:
        # 未启用时 fallback 到简单合并
        return _simple_merge(layer1_results, layer2_results, id_field)
    
    # 提取分数
    l1_scores = [r.get(score_field, 0.0) for r in layer1_results]
    l2_scores = [r.get(score_field, 0.0) for r in layer2_results]
    
    # 结果太少时不做 PIT（退化为简单加权）
    if len(l1_scores) < config.min_results_for_pit and len(l2_scores) < config.min_results_for_pit:
        logger.debug("Results too few for PIT, using simple weighted merge")
        return _simple_merge(layer1_results, layer2_results, id_field)
    
    # Step 1-4: 对每个源分别做 PIT → Energy → Temperature → Probabilities
    l1_probs = _scores_to_probabilities(l1_scores)
    l2_probs = _scores_to_probabilities(l2_scores)
    
    # 构建 ID → probability 映射
    l1_prob_map: Dict[str, float] = {}
    for i, result in enumerate(layer1_results):
        doc_id = _get_id(result, id_field)
        if doc_id:
            l1_prob_map[doc_id] = l1_probs[i] if i < len(l1_probs) else 0.0
    
    l2_prob_map: Dict[str, float] = {}
    for i, result in enumerate(layer2_results):
        doc_id = _get_id(result, id_field)
        if doc_id:
            l2_prob_map[doc_id] = l2_probs[i] if i < len(l2_probs) else 0.0
    
    # Step 5: Weighted Fusion
    all_doc_ids = set(l1_prob_map.keys()) | set(l2_prob_map.keys())
    consensus_ids = set(l1_prob_map.keys()) & set(l2_prob_map.keys())
    
    fused_results: List[Tuple[str, float, Dict[str, Any]]] = []
    
    # 构建 ID → 原始结果的映射（优先取 Layer 1 的完整数据）
    result_map: Dict[str, Dict[str, Any]] = {}
    for r in layer2_results:
        doc_id = _get_id(r, id_field)
        if doc_id:
            result_map[doc_id] = r
    for r in layer1_results:  # Layer 1 覆盖 Layer 2
        doc_id = _get_id(r, id_field)
        if doc_id:
            result_map[doc_id] = r
    
    for doc_id in all_doc_ids:
        # score(d) = α * P_v(d) + (1-α) * P_g(d) + β * 1[d ∈ consensus]
        fused_score = (
            config.alpha * l1_prob_map.get(doc_id, 0.0)
            + (1 - config.alpha) * l2_prob_map.get(doc_id, 0.0)
            + (config.beta if doc_id in consensus_ids else 0.0)
        )
        
        original_result = result_map.get(doc_id, {})
        fused_results.append((doc_id, fused_score, original_result))
    
    # 按融合分数降序排列
    fused_results.sort(key=lambda x: x[1], reverse=True)
    
    # 构建输出
    output = []
    for doc_id, fused_score, original in fused_results:
        merged = dict(original)
        merged["fused_score"] = round(fused_score, 6)
        merged["in_consensus"] = doc_id in consensus_ids
        merged["_fusion_meta"] = {
            "l1_prob": round(l1_prob_map.get(doc_id, 0.0), 4),
            "l2_prob": round(l2_prob_map.get(doc_id, 0.0), 4),
            "alpha": config.alpha,
            "beta": config.beta,
        }
        output.append(merged)
    
    logger.info(
        f"CalibratedFusion: L1({len(layer1_results)}) + L2({len(layer2_results)}) "
        f"→ {len(output)} results, consensus={len(consensus_ids)}"
    )
    
    return output


def _scores_to_probabilities(scores: List[float]) -> List[float]:
    """完整的 PIT → Energy → Temperature → Probabilities 管道"""
    if not scores:
        return []
    if len(scores) == 1:
        return [1.0]
    
    percentiles = pit_normalize(scores)
    energies = compute_energies(percentiles)
    temperature = compute_temperature(energies)
    probs = boltzmann_probabilities(energies, temperature)
    return probs


def _get_id(result: Dict[str, Any], id_field: str) -> str:
    """从结果中提取 ID"""
    # 尝试多种 ID 字段
    for field in [id_field, "id", "exercise_id", "name"]:
        val = result.get(field)
        if val:
            return str(val)
    return ""


def _simple_merge(
    layer1_results: List[Dict[str, Any]],
    layer2_results: List[Dict[str, Any]],
    id_field: str,
) -> List[Dict[str, Any]]:
    """简单合并（不做校准，按原始分数排序）"""
    seen = set()
    merged = []
    
    for r in layer1_results:
        doc_id = _get_id(r, id_field)
        if doc_id and doc_id not in seen:
            seen.add(doc_id)
            merged.append(r)
    
    for r in layer2_results:
        doc_id = _get_id(r, id_field)
        if doc_id and doc_id not in seen:
            seen.add(doc_id)
            merged.append(r)
    
    return merged
