# -*- coding: utf-8 -*-
"""
检索质量评测框架

提供 NDCG@K 和 Recall@K 计算，支持 A/B 对比。
用于量化 CalibratedFusion / GraphConvRerank / QueryReshaper 的效果。

用法：
  python -m src.framework.retrieval.eval.run_eval --config eval_config.json

版本: 1.0.0
日期: 2026-05-11
"""

import math
import json
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)


@dataclass
class EvalQuery:
    """评测查询"""
    query_id: str
    query_text: str
    relevant_ids: List[str]  # 人工标注的相关动作 ID
    user_profile: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EvalResult:
    """单次评测结果"""
    query_id: str
    retrieved_ids: List[str]
    ndcg_at_5: float = 0.0
    ndcg_at_10: float = 0.0
    recall_at_5: float = 0.0
    recall_at_10: float = 0.0
    recall_at_20: float = 0.0
    latency_ms: float = 0.0


@dataclass
class EvalReport:
    """评测报告"""
    config_name: str
    total_queries: int
    avg_ndcg_at_5: float = 0.0
    avg_ndcg_at_10: float = 0.0
    avg_recall_at_5: float = 0.0
    avg_recall_at_10: float = 0.0
    avg_recall_at_20: float = 0.0
    avg_latency_ms: float = 0.0
    results: List[EvalResult] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# === 指标计算 ===

def dcg_at_k(retrieved_ids: List[str], relevant_ids: set, k: int) -> float:
    """Discounted Cumulative Gain @ K"""
    dcg = 0.0
    for i, doc_id in enumerate(retrieved_ids[:k]):
        if doc_id in relevant_ids:
            dcg += 1.0 / math.log2(i + 2)  # i+2 因为 log2(1)=0
    return dcg


def ndcg_at_k(retrieved_ids: List[str], relevant_ids: List[str], k: int) -> float:
    """Normalized DCG @ K"""
    relevant_set = set(relevant_ids)
    actual_dcg = dcg_at_k(retrieved_ids, relevant_set, k)

    # Ideal DCG: 所有相关文档排在最前面
    ideal_retrieved = relevant_ids[:k]
    ideal_dcg = dcg_at_k(ideal_retrieved, relevant_set, k)

    if ideal_dcg == 0:
        return 0.0
    return actual_dcg / ideal_dcg


def recall_at_k(retrieved_ids: List[str], relevant_ids: List[str], k: int) -> float:
    """Recall @ K"""
    if not relevant_ids:
        return 0.0
    relevant_set = set(relevant_ids)
    retrieved_set = set(retrieved_ids[:k])
    hits = len(relevant_set & retrieved_set)
    return hits / len(relevant_set)


def compute_eval_result(
    query_id: str,
    retrieved_ids: List[str],
    relevant_ids: List[str],
    latency_ms: float = 0.0,
) -> EvalResult:
    """计算单个查询的评测指标"""
    return EvalResult(
        query_id=query_id,
        retrieved_ids=retrieved_ids[:20],
        ndcg_at_5=ndcg_at_k(retrieved_ids, relevant_ids, 5),
        ndcg_at_10=ndcg_at_k(retrieved_ids, relevant_ids, 10),
        recall_at_5=recall_at_k(retrieved_ids, relevant_ids, 5),
        recall_at_10=recall_at_k(retrieved_ids, relevant_ids, 10),
        recall_at_20=recall_at_k(retrieved_ids, relevant_ids, 20),
        latency_ms=latency_ms,
    )


def compute_eval_report(config_name: str, results: List[EvalResult]) -> EvalReport:
    """汇总评测报告"""
    n = len(results)
    if n == 0:
        return EvalReport(config_name=config_name, total_queries=0)

    return EvalReport(
        config_name=config_name,
        total_queries=n,
        avg_ndcg_at_5=sum(r.ndcg_at_5 for r in results) / n,
        avg_ndcg_at_10=sum(r.ndcg_at_10 for r in results) / n,
        avg_recall_at_5=sum(r.recall_at_5 for r in results) / n,
        avg_recall_at_10=sum(r.recall_at_10 for r in results) / n,
        avg_recall_at_20=sum(r.recall_at_20 for r in results) / n,
        avg_latency_ms=sum(r.latency_ms for r in results) / n,
        results=results,
    )


def compare_reports(baseline: EvalReport, experiment: EvalReport) -> Dict[str, Any]:
    """A/B 对比两个评测报告"""
    def delta(a: float, b: float) -> str:
        diff = b - a
        pct = (diff / a * 100) if a > 0 else 0
        sign = "+" if diff > 0 else ""
        return f"{sign}{diff:.4f} ({sign}{pct:.1f}%)"

    return {
        "baseline": baseline.config_name,
        "experiment": experiment.config_name,
        "queries": baseline.total_queries,
        "ndcg@5": delta(baseline.avg_ndcg_at_5, experiment.avg_ndcg_at_5),
        "ndcg@10": delta(baseline.avg_ndcg_at_10, experiment.avg_ndcg_at_10),
        "recall@5": delta(baseline.avg_recall_at_5, experiment.avg_recall_at_5),
        "recall@10": delta(baseline.avg_recall_at_10, experiment.avg_recall_at_10),
        "recall@20": delta(baseline.avg_recall_at_20, experiment.avg_recall_at_20),
        "latency_ms": delta(baseline.avg_latency_ms, experiment.avg_latency_ms),
    }
