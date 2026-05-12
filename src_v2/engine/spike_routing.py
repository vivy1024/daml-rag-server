"""
脉冲传播 — 基于确定性图谱的联想激活

与 Wave Memory 的区别：
- 图源：exercise_graph dict（专家标注的确定性关系），不是统计共现
- 关系有类型和方向：TARGETS_PRIMARY(1.0), CONTRAINDICATED_FOR(-0.8)
- 负向传播：禁忌关系产生负脉冲，抑制危险动作
- 传播深度由 EPA 的 logicDepth 动态决定

核心算法：
1. 从查询关键词匹配图谱节点（种子节点）
2. BFS 沿关系传播脉冲，每层衰减
3. 将激活节点的向量加权求和，生成 spike_boost_vector
"""

import logging
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass

import numpy as np

logger = logging.getLogger(__name__)

# 关系类型权重（正向=增强，负向=抑制）
RELATION_WEIGHTS = {
    "TARGETS_PRIMARY": 1.0,
    "TARGETS_SECONDARY": 0.7,
    "VARIATION_OF": 0.9,
    "REQUIRES": 0.5,
    "SUITABLE_FOR_LEVEL": 0.6,
    "RECOMMENDED_FOR_GOAL": 0.6,
    "CORRECTS": 0.7,
    "RELATED_TO": 0.4,
    "PART_OF": 0.3,
    # 负向关系
    "CONTRAINDICATED_FOR": -0.8,
    "AGGRAVATES": -0.7,
}


@dataclass
class SpikeResult:
    """脉冲传播结果"""
    spike_vector: np.ndarray        # 脉冲偏置向量
    activated_nodes: Dict[str, float]  # 被激活的节点及其分数
    seed_nodes: List[str]           # 种子节点
    propagation_depth: int          # 实际传播深度


class SpikeRouter:
    """脉冲传播路由器 — 确定性图谱版

    从查询关键词对应的图谱节点出发，沿确定性关系传播脉冲。
    """

    def __init__(
        self,
        graph,  # GraphStore instance
        decay: float = 0.5,
        max_depth: int = 3,
        max_activations: int = 50,
    ):
        """
        Args:
            graph: GraphStore 实例
            decay: 每层衰减系数
            max_depth: 最大传播深度
            max_activations: 最大激活节点数
        """
        self.graph = graph
        self.decay = decay
        self.max_depth = max_depth
        self.max_activations = max_activations

        # 节点名称索引（用于关键词匹配）
        self._name_index: Dict[str, str] = {}  # name_lower → node_id
        self._build_name_index()

    def _build_name_index(self):
        """构建名称 → 节点 ID 的索引"""
        if not self.graph.ready:
            return

        for node_id in self.graph._graph:
            node = self.graph._graph[node_id]
            # 中文名
            name_zh = node.get("_name_zh", "")
            if name_zh:
                self._name_index[name_zh.lower()] = node_id
            # 英文名
            name_en = node.get("_name", "")
            if name_en:
                self._name_index[name_en.lower()] = node_id

        logger.info(f"SpikeRouter: name index built ({len(self._name_index)} entries)")

    def propagate(
        self,
        keywords: List[str],
        depth: int = 2,
        exercise_vectors: Optional[np.ndarray] = None,
        exercise_ids: Optional[List[str]] = None,
    ) -> SpikeResult:
        """从关键词节点出发，沿图谱关系传播脉冲

        Args:
            keywords: 查询中提取的关键词
            depth: 传播深度（由 EPA 决定）
            exercise_vectors: 动作向量矩阵（用于生成 spike_vector）
            exercise_ids: 动作 ID 列表（与向量矩阵对应）

        Returns:
            SpikeResult
        """
        depth = min(depth, self.max_depth)

        # 1. 找到种子节点
        seed_nodes = self._find_seed_nodes(keywords)

        if not seed_nodes:
            return SpikeResult(
                spike_vector=np.zeros(1024, dtype=np.float32),
                activated_nodes={},
                seed_nodes=[],
                propagation_depth=0,
            )

        # 2. BFS 传播
        activations = self._bfs_propagate(seed_nodes, depth)

        # 3. 转换为向量偏置
        spike_vector = self._activations_to_vector(
            activations, exercise_vectors, exercise_ids
        )

        return SpikeResult(
            spike_vector=spike_vector,
            activated_nodes=activations,
            seed_nodes=[s[0] for s in seed_nodes],
            propagation_depth=depth,
        )

    def _find_seed_nodes(self, keywords: List[str]) -> List[Tuple[str, float]]:
        """从关键词匹配图谱节点

        Returns:
            [(node_id, initial_score)]
        """
        seeds = []
        seen = set()

        for keyword in keywords:
            kw_lower = keyword.lower().strip()
            if not kw_lower:
                continue

            # 精确匹配
            if kw_lower in self._name_index:
                node_id = self._name_index[kw_lower]
                if node_id not in seen:
                    seeds.append((node_id, 1.0))
                    seen.add(node_id)
                continue

            # 部分匹配（关键词是节点名的子串）
            for name, node_id in self._name_index.items():
                if node_id in seen:
                    continue
                if kw_lower in name or name in kw_lower:
                    seeds.append((node_id, 0.7))
                    seen.add(node_id)
                    if len(seeds) >= 10:  # 限制种子数
                        break

        return seeds[:10]

    def _bfs_propagate(
        self, seeds: List[Tuple[str, float]], depth: int
    ) -> Dict[str, float]:
        """BFS 脉冲传播

        Args:
            seeds: [(node_id, initial_score)]
            depth: 传播层数

        Returns:
            {node_id: activation_score}
        """
        activations: Dict[str, float] = {}

        # 初始化种子
        current_layer = []
        for node_id, score in seeds:
            activations[node_id] = score
            current_layer.append((node_id, score))

        # 逐层传播
        for d in range(depth):
            next_layer = []
            layer_decay = self.decay ** (d + 1)

            for node_id, parent_score in current_layer:
                # 获取所有邻居
                neighbors = self.graph.get_neighbors(node_id)

                for neighbor_id, rel_type, edge_weight in neighbors:
                    # 计算传播分数
                    rel_weight = RELATION_WEIGHTS.get(rel_type, 0.3)
                    propagated_score = parent_score * rel_weight * layer_decay

                    # 累加激活（允许多路径叠加）
                    if neighbor_id in activations:
                        activations[neighbor_id] += propagated_score
                    else:
                        activations[neighbor_id] = propagated_score
                        next_layer.append((neighbor_id, propagated_score))

                    # 限制总激活数
                    if len(activations) >= self.max_activations:
                        break

                if len(activations) >= self.max_activations:
                    break

            current_layer = next_layer
            if not current_layer:
                break

        return activations

    def _activations_to_vector(
        self,
        activations: Dict[str, float],
        exercise_vectors: Optional[np.ndarray],
        exercise_ids: Optional[List[str]],
    ) -> np.ndarray:
        """将激活分数转换为向量偏置

        对被激活的动作节点，用其向量加权求和。
        """
        if exercise_vectors is None or exercise_ids is None:
            return np.zeros(1024, dtype=np.float32)

        # 构建 ID → index 映射
        id_to_idx = {eid: i for i, eid in enumerate(exercise_ids)}

        # 加权求和
        weighted_sum = np.zeros(exercise_vectors.shape[1], dtype=np.float32)
        total_weight = 0.0

        for node_id, score in activations.items():
            if score <= 0:  # 跳过负向激活（禁忌）
                continue
            idx = id_to_idx.get(node_id)
            if idx is not None:
                weighted_sum += score * exercise_vectors[idx]
                total_weight += abs(score)

        # 归一化
        if total_weight > 1e-8:
            weighted_sum /= total_weight
            norm = np.linalg.norm(weighted_sum)
            if norm > 1e-8:
                weighted_sum /= norm

        return weighted_sum
