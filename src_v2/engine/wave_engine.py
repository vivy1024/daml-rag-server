"""
WaveEngine — 浪潮检索引擎主入口

五阶段查询管线：
  EPA → 残差金字塔 → 脉冲传播 → 向量融合 → 内存检索 + 后处理

从 Wave Memory (VCP TagMemo) 移植，适配健身领域。
"""

import time
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass, field

import numpy as np

from ..config import EngineConfig
from ..data.loader import DataStore
from .epa import compute_epa, EPAResult
from .residual_pyramid import decompose_residual_pyramid, PyramidResult
from .spike_routing import SpikeRouter, SpikeResult
from .vector_fusion import fuse_vectors
from .query_reshaper import QueryReshaper
from .calibrated_fusion import calibrated_fusion
from .graph_conv_rerank import graph_conv_rerank
from .geodesic_rerank import geodesic_rerank

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """检索结果"""
    results: List[Dict]           # 最终结果列表
    total_candidates: int         # 初始候选数
    filtered_count: int           # 被规则过滤的数量
    timing: Dict[str, float] = field(default_factory=dict)  # 各阶段耗时(ms)


class WaveEngine:
    """浪潮检索引擎

    Usage:
        engine = WaveEngine(data_store, config)
        result = await engine.search("练胸的动作", domain="exercises", user_profile={...})
    """

    def __init__(self, data_store: DataStore, config: EngineConfig):
        self.data = data_store
        self.config = config

        # 初始化各阶段模块
        self._epa_enabled = config.epa_enabled and data_store.pca_bases is not None
        self._pyramid_enabled = config.pyramid_enabled

        self.spike = SpikeRouter(
            graph=data_store.graph,
            decay=config.spike_decay,
            max_depth=config.spike_depth,
        ) if data_store.graph.ready else None

        self.reshaper = QueryReshaper(
            anchors=data_store.profile_anchors,
        ) if config.reshaper_enabled and data_store.profile_anchors is not None else None

    async def search(
        self,
        query_vec: np.ndarray,
        domain: str = "exercises",
        user_profile: Dict = None,
        filters: Dict = None,
        top_k: int = 10,
        recent_used: List[str] = None,
    ) -> SearchResult:
        """执行完整的浪潮检索管线

        Args:
            query_vec: 查询向量（已经过 Embedding）
            domain: 检索领域 ("exercises" | "foods" | "knowledge")
            user_profile: 用户档案
            filters: 过滤条件
            top_k: 返回数量
            recent_used: 最近使用过的动作（用于去重）

        Returns:
            SearchResult
        """
        timing = {}
        t0 = time.time()

        # === Phase 1: EPA 分析 ===
        epa_result: Optional[EPAResult] = None
        if self._epa_enabled:
            t = time.time()
            epa_result = compute_epa(query_vec, self.data.pca_bases)
            timing["epa"] = (time.time() - t) * 1000

        # === Phase 2: 残差金字塔 ===
        pyramid_result: Optional[PyramidResult] = None
        if self._pyramid_enabled and self.data.pca_bases is not None:
            t = time.time()
            pyramid_result = decompose_residual_pyramid(
                query_vec, self.data.pca_bases,
                max_levels=self.config.pyramid_max_levels,
            )
            timing["pyramid"] = (time.time() - t) * 1000

        # === Phase 3: 脉冲传播 ===
        spike_result: Optional[SpikeResult] = None
        if self.spike and domain == "exercises":
            t = time.time()
            # 从 filters 中提取关键词
            keywords = self._extract_keywords(filters, user_profile)
            spike_depth = 2
            if epa_result and epa_result.logic_depth > 0.5:
                spike_depth = 3

            exercise_vectors = self.data.exercise_index.get_all_vectors() if self.data.exercise_index else None
            spike_result = self.spike.propagate(
                keywords=keywords,
                depth=spike_depth,
                exercise_vectors=exercise_vectors,
                exercise_ids=self.data.exercise_ids,
            )
            timing["spike"] = (time.time() - t) * 1000

        # === Phase 4: 向量融合 ===
        t = time.time()
        profile_bias = None
        if self.reshaper and user_profile:
            profile_bias = self.reshaper.compute_bias(user_profile)

        spike_vec = spike_result.spike_vector if spike_result else None
        residual_signals = pyramid_result.levels if pyramid_result else None
        novelty = pyramid_result.novelty if pyramid_result else 0.0

        search_vec = fuse_vectors(
            query_vec=query_vec,
            spike_vec=spike_vec,
            profile_bias_vec=profile_bias,
            residual_signals=residual_signals,
            novelty=novelty,
        )
        timing["fusion"] = (time.time() - t) * 1000

        # === Phase 5: 内存检索 + 后处理 ===
        t = time.time()
        index = self.data.get_index(domain)
        if index is None:
            return SearchResult(results=[], total_candidates=0, filtered_count=0, timing=timing)

        # 5a. 向量检索
        candidates_k = top_k * 3
        raw_results = index.search(search_vec, k=candidates_k)
        timing["vector_search"] = (time.time() - t) * 1000

        if not raw_results:
            return SearchResult(results=[], total_candidates=0, filtered_count=0, timing=timing)

        # 获取 ID 和分数
        ids_list = self.data.get_ids(domain)
        payloads_list = self.data.get_payloads(domain)

        vector_scores: Dict[str, float] = {}
        candidate_data: Dict[str, Dict] = {}

        for idx, similarity in raw_results:
            if idx < len(ids_list):
                item_id = ids_list[idx]
                vector_scores[item_id] = similarity
                payload = payloads_list[idx] if idx < len(payloads_list) else {}
                candidate_data[item_id] = {"id": item_id, "similarity": similarity, **payload}

        total_candidates = len(vector_scores)

        # 5b. 计算图谱关系分（仅 exercises 领域）
        t = time.time()
        if domain == "exercises" and self.config.fusion_enabled:
            graph_scores = self._compute_graph_scores(
                list(vector_scores.keys()), filters
            )
            # CalibratedFusion
            fused = calibrated_fusion(
                vector_scores=vector_scores,
                graph_scores=graph_scores,
                alpha=self.config.fusion_alpha,
            )
        else:
            fused = sorted(vector_scores.items(), key=lambda x: x[1], reverse=True)
        timing["calibrated_fusion"] = (time.time() - t) * 1000

        # 5c. GraphConvRerank
        t = time.time()
        if domain == "exercises" and self.config.gc_enabled:
            fused = graph_conv_rerank(
                candidates=fused,
                adjacency=self.data.exercise_adjacency,
                alpha=self.config.gc_alpha,
            )
        timing["graph_conv"] = (time.time() - t) * 1000

        # 5d. 测地线重排 + SVD 去重
        t = time.time()
        if self.config.geodesic_enabled and index.get_all_vectors() is not None:
            # 构建候选向量映射
            candidate_vectors = {}
            for item_id in [f[0] for f in fused]:
                idx_in_list = ids_list.index(item_id) if item_id in ids_list else -1
                if idx_in_list >= 0:
                    vec = index.get_vector(idx_in_list)
                    if vec is not None:
                        candidate_vectors[item_id] = vec

            fused = geodesic_rerank(
                candidates=fused,
                vectors=candidate_vectors,
                diversity_threshold=self.config.svd_diversity_threshold,
                max_results=top_k * 2,
                recent_used=recent_used,
            )
        timing["geodesic"] = (time.time() - t) * 1000

        # 5e. 构建最终结果
        final_results = []
        for item_id, score in fused[:top_k]:
            result = candidate_data.get(item_id, {"id": item_id})
            result["score"] = score
            final_results.append(result)

        timing["total"] = (time.time() - t0) * 1000
        logger.info(
            f"WaveEngine.search: domain={domain}, candidates={total_candidates}, "
            f"results={len(final_results)}, total={timing['total']:.1f}ms"
        )

        return SearchResult(
            results=final_results,
            total_candidates=total_candidates,
            filtered_count=total_candidates - len(final_results),
            timing=timing,
        )

    def _extract_keywords(self, filters: Dict = None, user_profile: Dict = None) -> List[str]:
        """从过滤条件和用户档案中提取关键词（用于脉冲传播）"""
        keywords = []

        if filters:
            # 肌群
            muscle = filters.get("muscle_group")
            if muscle:
                keywords.append(muscle)
            # 器械
            equipment = filters.get("equipment")
            if equipment:
                if isinstance(equipment, list):
                    keywords.extend(equipment)
                else:
                    keywords.append(equipment)

        if user_profile:
            # 训练目标
            goal = user_profile.get("primary_goal")
            if goal:
                keywords.append(goal)

        return keywords

    def _compute_graph_scores(
        self, candidate_ids: List[str], filters: Dict = None
    ) -> Dict[str, float]:
        """计算候选动作的图谱关系分

        基于过滤条件中的目标肌群/器械/目标，计算每个候选与查询意图的图谱匹配度。
        """
        if not filters or not self.data.graph.ready:
            return {}

        graph_scores: Dict[str, float] = {}
        target_muscle = filters.get("muscle_group")
        target_goal = filters.get("goal")

        for exercise_id in candidate_ids:
            score = 0.0

            if target_muscle:
                # 检查是否 TARGETS_PRIMARY 目标肌群
                primary_targets = self.data.graph.get_relations(exercise_id, "TARGETS_PRIMARY")
                for edge in primary_targets:
                    if target_muscle.lower() in (edge.get("target", "") or "").lower():
                        score += 1.0
                        break
                    if target_muscle.lower() in (edge.get("target_name_zh", "") or "").lower():
                        score += 1.0
                        break

                # TARGETS_SECONDARY
                secondary_targets = self.data.graph.get_relations(exercise_id, "TARGETS_SECONDARY")
                for edge in secondary_targets:
                    if target_muscle.lower() in (edge.get("target", "") or "").lower():
                        score += 0.5
                        break
                    if target_muscle.lower() in (edge.get("target_name_zh", "") or "").lower():
                        score += 0.5
                        break

            if target_goal:
                # 检查 RECOMMENDED_FOR_GOAL
                goals = self.data.graph.get_relations(exercise_id, "RECOMMENDED_FOR_GOAL")
                for edge in goals:
                    if target_goal.lower() in (edge.get("target", "") or "").lower():
                        score += 0.6
                        break

            if score > 0:
                graph_scores[exercise_id] = score

        return graph_scores
