# -*- coding: utf-8 -*-
"""
InMemoryHotCache — 内存化热数据缓存

将 Qdrant 向量和 Neo4j 关系数据拉取到内存，用 numpy 做本地搜索。
热路径延迟从 ~200ms（网络往返）降到 <5ms（内存计算）。

设计：
- 启动时异步加载（不阻塞服务启动）
- 加载完成前 fallback 到远程查询
- 支持手动刷新（POST /api/cache/refresh）
- 内存占用预估：1790 动作 × 768 维 ≈ 5.5MB + 关系 dict ≈ 2MB

版本: 1.0.0
日期: 2026-05-11
"""

import os
import time
import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


class InMemoryHotCache:
    """内存化热数据缓存"""

    def __init__(self):
        # 向量数据
        self._exercise_vectors: Optional[np.ndarray] = None  # shape: (N, dim)
        self._exercise_ids: List[str] = []                    # 与向量行对应的 ID
        self._exercise_metadata: Dict[str, Dict[str, Any]] = {}  # id → metadata

        # 关系数据
        self._muscle_to_exercises: Dict[str, List[str]] = {}  # muscle → [exercise_ids]
        self._exercise_to_muscles: Dict[str, List[Tuple[str, float]]] = {}  # exercise → [(muscle, activation)]
        self._exercise_adjacency: Dict[str, List[Tuple[str, float]]] = {}  # exercise → [(neighbor, weight)]

        # 状态
        self._ready = False
        self._loading = False
        self._load_time_ms: float = 0
        self._exercise_count: int = 0
        self._vector_dim: int = 0

    @property
    def ready(self) -> bool:
        return self._ready

    @property
    def stats(self) -> Dict[str, Any]:
        return {
            "ready": self._ready,
            "loading": self._loading,
            "exercise_count": self._exercise_count,
            "vector_dim": self._vector_dim,
            "memory_mb": self._estimate_memory_mb(),
            "load_time_ms": self._load_time_ms,
            "muscle_groups": len(self._muscle_to_exercises),
            "adjacency_edges": sum(len(v) for v in self._exercise_adjacency.values()),
        }

    def _estimate_memory_mb(self) -> float:
        if self._exercise_vectors is None:
            return 0.0
        vector_bytes = self._exercise_vectors.nbytes
        # 粗略估算 metadata + relations
        meta_bytes = self._exercise_count * 500  # ~500 bytes per exercise metadata
        return (vector_bytes + meta_bytes) / (1024 * 1024)

    # === 加载 ===

    async def load_from_qdrant(self, qdrant_client, collection: str = "exercises"):
        """从 Qdrant 拉取全量向量数据"""
        logger.info(f"[HotCache] Loading vectors from Qdrant collection '{collection}'...")
        start = time.time()

        try:
            # 滚动获取所有点
            all_points = []
            offset = None
            batch_size = 100

            while True:
                points, next_offset = await qdrant_client.scroll(
                    collection_name=collection,
                    limit=batch_size,
                    offset=offset,
                    with_vectors=True,
                    with_payload=True,
                )

                all_points.extend(points)

                if next_offset is None or len(points) < batch_size:
                    break
                offset = next_offset

            if not all_points:
                logger.warning("[HotCache] No points found in Qdrant collection")
                return

            # 构建 numpy 矩阵
            vectors = []
            ids = []
            metadata = {}

            for point in all_points:
                point_id = str(point.id) if hasattr(point, 'id') else str(point.get('id', ''))
                vector = point.vector if hasattr(point, 'vector') else point.get('vector', [])
                payload = point.payload if hasattr(point, 'payload') else point.get('payload', {})

                if vector and point_id:
                    vectors.append(vector)
                    ids.append(point_id)
                    metadata[point_id] = payload

            self._exercise_vectors = np.array(vectors, dtype=np.float32)
            self._exercise_ids = ids
            self._exercise_metadata = metadata
            self._exercise_count = len(ids)
            self._vector_dim = self._exercise_vectors.shape[1] if len(vectors) > 0 else 0

            # 归一化向量（用于 cosine similarity = dot product）
            norms = np.linalg.norm(self._exercise_vectors, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            self._exercise_vectors = self._exercise_vectors / norms

            elapsed = (time.time() - start) * 1000
            logger.info(
                f"[HotCache] Vectors loaded: {self._exercise_count} exercises, "
                f"dim={self._vector_dim}, {elapsed:.0f}ms"
            )

        except Exception as e:
            logger.error(f"[HotCache] Failed to load vectors: {e}")

    async def load_from_neo4j(self, neo4j_client):
        """从 Neo4j 导出关系数据"""
        logger.info("[HotCache] Loading relations from Neo4j...")
        start = time.time()

        try:
            # 1. 肌群 → 动作 关系
            query_muscles = """
            MATCH (e:Exercise)-[r:TARGETS|ASSISTS]->(m:MuscleGroup)
            RETURN e.id as exercise_id, m.name as muscle, 
                   type(r) as relation, r.activation as activation
            """
            results = await neo4j_client.execute_query(query_muscles, {})

            for row in results:
                eid = row.get("exercise_id")
                muscle = row.get("muscle")
                activation = row.get("activation", 0.5)
                relation = row.get("relation", "TARGETS")

                if not eid or not muscle:
                    continue

                # muscle → exercises
                if muscle not in self._muscle_to_exercises:
                    self._muscle_to_exercises[muscle] = []
                self._muscle_to_exercises[muscle].append(eid)

                # exercise → muscles
                if eid not in self._exercise_to_muscles:
                    self._exercise_to_muscles[eid] = []
                weight = float(activation) if activation else (1.0 if relation == "TARGETS" else 0.5)
                self._exercise_to_muscles[eid].append((muscle, weight))

            # 2. 构建动作-动作邻接（共享肌群）
            self._build_exercise_adjacency()

            elapsed = (time.time() - start) * 1000
            logger.info(
                f"[HotCache] Relations loaded: {len(self._muscle_to_exercises)} muscles, "
                f"{len(self._exercise_to_muscles)} exercises with relations, "
                f"{sum(len(v) for v in self._exercise_adjacency.values())} adjacency edges, "
                f"{elapsed:.0f}ms"
            )

        except Exception as e:
            logger.error(f"[HotCache] Failed to load relations: {e}")

    def _build_exercise_adjacency(self):
        """构建动作-动作邻接关系（基于共享肌群）"""
        # 反向索引：muscle → set of exercise_ids
        muscle_exercises: Dict[str, set] = {}
        for muscle, exercises in self._muscle_to_exercises.items():
            muscle_exercises[muscle] = set(exercises)

        # 对每个动作，找到共享肌群的邻居
        for eid, muscles in self._exercise_to_muscles.items():
            neighbors: Dict[str, float] = {}

            for muscle, activation in muscles:
                # 找到同一肌群的其他动作
                for neighbor_id in muscle_exercises.get(muscle, set()):
                    if neighbor_id == eid:
                        continue
                    # 权重 = 共享肌群的 activation 之和
                    neighbors[neighbor_id] = neighbors.get(neighbor_id, 0.0) + activation

            # 只保留 top-20 邻居（避免热门动作过度连接）
            sorted_neighbors = sorted(neighbors.items(), key=lambda x: x[1], reverse=True)[:20]
            self._exercise_adjacency[eid] = sorted_neighbors

    # === 初始化 ===

    async def initialize(self, qdrant_client, neo4j_client, collection: str = "exercises"):
        """异步初始化（不阻塞服务启动）"""
        if self._loading:
            return
        self._loading = True
        start = time.time()

        try:
            await asyncio.gather(
                self.load_from_qdrant(qdrant_client, collection),
                self.load_from_neo4j(neo4j_client),
            )
            self._ready = True
            self._load_time_ms = (time.time() - start) * 1000
            logger.info(f"[HotCache] ✅ Fully initialized in {self._load_time_ms:.0f}ms")
        except Exception as e:
            logger.error(f"[HotCache] Initialization failed: {e}")
        finally:
            self._loading = False

    # === 查询 ===

    def vector_search(
        self,
        query_vector: np.ndarray,
        top_k: int = 10,
        filter_ids: Optional[set] = None,
    ) -> List[Dict[str, Any]]:
        """
        内存向量搜索（cosine similarity via dot product）
        
        Args:
            query_vector: 查询向量 (dim,)
            top_k: 返回数量
            filter_ids: 只在这些 ID 中搜索（可选）
        
        Returns:
            [{id, score, ...metadata}] 按分数降序
        """
        if not self._ready or self._exercise_vectors is None:
            return []

        # 归一化查询向量
        qv = np.array(query_vector, dtype=np.float32)
        norm = np.linalg.norm(qv)
        if norm > 0:
            qv = qv / norm

        # dot product = cosine similarity（因为向量已归一化）
        scores = self._exercise_vectors @ qv  # shape: (N,)

        # 过滤
        if filter_ids:
            mask = np.array([eid in filter_ids for eid in self._exercise_ids])
            scores = np.where(mask, scores, -1.0)

        # Top-K
        top_indices = np.argsort(scores)[::-1][:top_k]

        results = []
        for idx in top_indices:
            if scores[idx] <= 0:
                break
            eid = self._exercise_ids[idx]
            result = {
                "id": eid,
                "score": float(scores[idx]),
                **self._exercise_metadata.get(eid, {}),
            }
            results.append(result)

        return results

    def get_muscle_exercises(self, muscle: str) -> List[str]:
        """获取肌群对应的动作 ID 列表"""
        return self._muscle_to_exercises.get(muscle, [])

    def get_exercise_muscles(self, exercise_id: str) -> List[Tuple[str, float]]:
        """获取动作对应的肌群列表"""
        return self._exercise_to_muscles.get(exercise_id, [])

    def get_exercise_neighbors(self, exercise_id: str) -> List[Tuple[str, float]]:
        """获取动作的邻居（共享肌群）"""
        return self._exercise_adjacency.get(exercise_id, [])


# === 全局单例 ===

_global_cache: Optional[InMemoryHotCache] = None


def get_hot_cache() -> InMemoryHotCache:
    """获取全局 HotCache 单例"""
    global _global_cache
    if _global_cache is None:
        _global_cache = InMemoryHotCache()
    return _global_cache


async def initialize_hot_cache(qdrant_client, neo4j_client, collection: str = "exercises"):
    """初始化全局 HotCache"""
    cache = get_hot_cache()
    if not cache.ready and not cache._loading:
        await cache.initialize(qdrant_client, neo4j_client, collection)
    return cache
