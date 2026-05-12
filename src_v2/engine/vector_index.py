"""
向量索引 — hnswlib 封装

从 Wave Memory 移植，适配健身场景。
支持从 .npy 文件加载预计算向量。
"""

import os
import threading
from typing import List, Tuple, Optional

import numpy as np

try:
    import hnswlib
    HAS_HNSWLIB = True
except ImportError:
    hnswlib = None
    HAS_HNSWLIB = False


class VectorIndex:
    """基于 hnswlib 的 HNSW 向量索引

    如果 hnswlib 不可用，fallback 到 numpy brute-force（小规模数据仍然很快）。
    """

    def __init__(self, dimension: int, max_elements: int = 100000):
        self.dimension = dimension
        self.max_elements = max_elements
        self._lock = threading.Lock()
        self._index = None
        self._vectors: Optional[np.ndarray] = None
        self._use_hnswlib = HAS_HNSWLIB
        self._count = 0

    def load_from_npy(self, npy_path: str):
        """从 .npy 文件加载向量并构建索引"""
        vectors = np.load(npy_path).astype(np.float32)
        self._vectors = vectors
        self._count = len(vectors)
        self.dimension = vectors.shape[1]

        if self._use_hnswlib:
            self._index = hnswlib.Index(space="cosine", dim=self.dimension)
            self._index.init_index(
                max_elements=max(self._count + 1000, self.max_elements),
                ef_construction=200,
                M=16,
            )
            self._index.set_ef(50)
            ids = np.arange(self._count, dtype=np.int64)
            self._index.add_items(vectors, ids)
        # else: 使用 numpy brute-force

    def search(self, query: np.ndarray, k: int = 10) -> List[Tuple[int, float]]:
        """搜索最近邻

        Returns:
            [(index, similarity_score), ...] — score 越高越相似（cosine similarity）
        """
        if self._count == 0:
            return []

        k = min(k, self._count)
        query = query.astype(np.float32).reshape(1, -1)

        with self._lock:
            if self._use_hnswlib and self._index is not None:
                labels, distances = self._index.knn_query(query, k=k)
                # hnswlib cosine distance = 1 - cosine_similarity
                results = [
                    (int(labels[0][i]), 1.0 - float(distances[0][i]))
                    for i in range(len(labels[0]))
                ]
            else:
                # Numpy brute-force cosine similarity
                # 归一化查询向量
                query_norm = query / (np.linalg.norm(query) + 1e-10)
                # 归一化所有向量
                norms = np.linalg.norm(self._vectors, axis=1, keepdims=True) + 1e-10
                normalized = self._vectors / norms
                # 计算余弦相似度
                similarities = (normalized @ query_norm.T).flatten()
                # 取 top-k
                top_indices = np.argsort(similarities)[::-1][:k]
                results = [
                    (int(idx), float(similarities[idx]))
                    for idx in top_indices
                ]

        return results

    def get_vector(self, index: int) -> Optional[np.ndarray]:
        """获取指定索引的向量"""
        if self._vectors is not None and 0 <= index < self._count:
            return self._vectors[index]
        return None

    def get_all_vectors(self) -> Optional[np.ndarray]:
        """获取所有向量矩阵"""
        return self._vectors

    @property
    def count(self) -> int:
        return self._count
