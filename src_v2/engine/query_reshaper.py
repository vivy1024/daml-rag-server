"""
QueryReshaper — 用户档案偏置

根据用户档案（训练水平/目标/伤病/器械）生成偏置向量，
使查询结果自动偏向适合该用户的动作。
"""

import logging
from typing import Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)

# 锚点类型定义
ANCHOR_TYPES = {
    "fitness_level": ["novice", "beginner", "intermediate", "advanced"],
    "primary_goal": [
        "hypertrophy", "fat_loss", "strength", "endurance",
        "body_shaping", "general_fitness", "functional", "rehabilitation",
    ],
}


class QueryReshaper:
    """用户档案偏置生成器

    使用预计算的锚点向量，根据用户档案生成 profile_bias 向量。
    """

    def __init__(self, anchors: Optional[np.ndarray] = None, anchor_labels: List[str] = None):
        """
        Args:
            anchors: 预计算的锚点向量矩阵 (N × dim)
            anchor_labels: 锚点标签列表（与 anchors 行对应）
        """
        self.anchors = anchors
        self.anchor_labels = anchor_labels or []
        self._label_to_idx = {label: i for i, label in enumerate(self.anchor_labels)}

    def compute_bias(self, user_profile: Dict) -> Optional[np.ndarray]:
        """根据用户档案计算偏置向量

        Args:
            user_profile: 用户档案 dict，包含 fitness_level, primary_goal 等

        Returns:
            偏置向量（单位向量），或 None（无法计算时）
        """
        if self.anchors is None or len(self.anchors) == 0:
            return None

        weights = []
        indices = []

        # 训练水平
        level = user_profile.get("fitness_level")
        if level and level in self._label_to_idx:
            indices.append(self._label_to_idx[level])
            weights.append(1.0)

        # 训练目标
        goal = user_profile.get("primary_goal")
        if goal and goal in self._label_to_idx:
            indices.append(self._label_to_idx[goal])
            weights.append(0.8)

        if not indices:
            return None

        # 加权组合锚点向量
        bias = np.zeros(self.anchors.shape[1], dtype=np.float32)
        total_weight = 0.0

        for idx, w in zip(indices, weights):
            if idx < len(self.anchors):
                bias += w * self.anchors[idx]
                total_weight += w

        if total_weight > 1e-8:
            bias /= total_weight

        # 归一化
        norm = np.linalg.norm(bias)
        if norm > 1e-8:
            bias /= norm
            return bias

        return None
