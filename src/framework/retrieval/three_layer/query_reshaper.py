# -*- coding: utf-8 -*-
"""
QueryReshaper — 查询向量重塑

用用户档案信息偏置查询向量方向，使检索结果天然倾向于用户适合的动作。

核心公式：
  q' = normalize(α * q + (1-α) * bias_vector)

bias_vector 由用户档案（训练水平、目标、器械、伤病）加权组合锚点向量构建。

版本: 1.0.0
日期: 2026-05-11
"""

import os
import logging
from typing import Dict, List, Any, Optional

import numpy as np

logger = logging.getLogger(__name__)


class QueryReshaper:
    """查询向量重塑器"""

    def __init__(self, embedding_fn=None):
        """
        Args:
            embedding_fn: 文本 → 向量的函数 (text: str) → np.ndarray
                         如果不提供，则使用延迟初始化
        """
        self._embedding_fn = embedding_fn
        self._anchors: Dict[str, np.ndarray] = {}
        self._ready = False
        self._alpha = float(os.getenv("QUERY_RESHAPER_ALPHA", "0.85"))
        self._enabled = os.getenv("ENABLE_QUERY_RESHAPING", "true").lower() == "true"
        self._min_profile_fields = int(os.getenv("QUERY_RESHAPER_MIN_FIELDS", "2"))

    @property
    def ready(self) -> bool:
        return self._ready and self._enabled

    # === 锚点定义 ===

    ANCHOR_TEXTS = {
        # 训练水平
        "beginner": "适合新手的简单安全基础动作 低难度 器械辅助",
        "intermediate": "中级训练者的复合动作 自由重量 渐进超负荷",
        "advanced": "高级训练者的高强度动作 大重量 高级技术",
        "elite": "精英运动员的专项训练 极限强度 竞技水平",

        # 训练目标
        "muscle_gain": "增肌肌肥大训练 中等重量 高容量 8到12次",
        "fat_loss": "减脂燃脂训练 高强度间歇 有氧 代谢训练",
        "strength": "力量训练 大重量 低次数 1到5次 复合动作",
        "endurance": "耐力训练 轻重量 高次数 有氧能力",
        "body_recomp": "身体重组 增肌减脂 中等强度 蛋白质",
        "general_fitness": "综合体能 全面发展 功能性训练",

        # 器械偏好
        "bodyweight": "徒手自重训练 无器械 家庭训练 俯卧撑 引体向上",
        "barbell": "杠铃自由重量训练 深蹲 硬拉 卧推 划船",
        "dumbbell": "哑铃训练 单侧训练 稳定性 灵活",
        "machine": "固定器械训练 安全 孤立 新手友好",
        "cable": "绳索训练 持续张力 多角度",

        # 伤病回避（负方向使用）
        "avoid_knee": "避免膝关节压力 不做深蹲跳跃 保护膝盖",
        "avoid_back": "避免腰椎负荷 不做硬拉 保护腰部脊柱",
        "avoid_shoulder": "避免肩关节过度外展 不做颈后推举 保护肩膀",
        "avoid_wrist": "避免手腕压力 不做前臂支撑 保护手腕",
    }

    # === 初始化 ===

    async def initialize(self, embedding_fn=None):
        """预计算所有锚点向量"""
        if embedding_fn:
            self._embedding_fn = embedding_fn

        if not self._embedding_fn:
            logger.warning("[QueryReshaper] No embedding function provided, cannot initialize")
            return

        logger.info(f"[QueryReshaper] Precomputing {len(self.ANCHOR_TEXTS)} anchor vectors...")

        for key, text in self.ANCHOR_TEXTS.items():
            try:
                vec = self._embedding_fn(text)
                if isinstance(vec, list):
                    vec = np.array(vec, dtype=np.float32)
                # 归一化
                norm = np.linalg.norm(vec)
                if norm > 0:
                    vec = vec / norm
                self._anchors[key] = vec
            except Exception as e:
                logger.warning(f"[QueryReshaper] Failed to embed anchor '{key}': {e}")

        self._ready = len(self._anchors) > 0
        logger.info(f"[QueryReshaper] ✅ Initialized with {len(self._anchors)} anchors")

    # === 核心方法 ===

    def reshape(
        self,
        query_vector: np.ndarray,
        user_profile: Optional[Dict[str, Any]] = None,
        alpha: Optional[float] = None,
    ) -> np.ndarray:
        """
        重塑查询向量
        
        Args:
            query_vector: 原始查询 embedding
            user_profile: 用户档案
            alpha: 覆盖默认 alpha（可选）
        
        Returns:
            重塑后的查询向量（归一化）
        """
        if not self._ready or not self._enabled:
            return query_vector

        if user_profile is None:
            return query_vector

        # 检查档案完整度
        filled_fields = self._count_profile_fields(user_profile)
        if filled_fields < self._min_profile_fields:
            return query_vector

        # 构建偏置向量
        bias = self._build_bias_vector(user_profile)
        if bias is None:
            return query_vector

        # 融合
        a = alpha if alpha is not None else self._alpha
        qv = np.array(query_vector, dtype=np.float32)

        reshaped = a * qv + (1 - a) * bias

        # 归一化
        norm = np.linalg.norm(reshaped)
        if norm > 0:
            reshaped = reshaped / norm

        return reshaped

    # === 偏置向量构建 ===

    def _build_bias_vector(self, profile: Dict[str, Any]) -> Optional[np.ndarray]:
        """从用户档案构建偏置向量"""
        vectors: List[np.ndarray] = []
        weights: List[float] = []

        # 1. 训练水平（权重 0.25）
        level = profile.get("training_level") or profile.get("level", "")
        level_key = level.lower() if level else ""
        if level_key in self._anchors:
            vectors.append(self._anchors[level_key])
            weights.append(0.25)

        # 2. 训练目标（权重 0.30）
        goals = profile.get("goals") or profile.get("primary_goals") or []
        if isinstance(goals, str):
            goals = [goals]
        goal_weight = 0.30 / max(len(goals[:2]), 1)
        for goal in goals[:2]:
            goal_key = goal.lower().replace(" ", "_")
            if goal_key in self._anchors:
                vectors.append(self._anchors[goal_key])
                weights.append(goal_weight)

        # 3. 器械偏好（权重 0.20）
        equipment = profile.get("available_equipment") or profile.get("equipment") or []
        if isinstance(equipment, str):
            equipment = [equipment]
        if equipment:
            for eq in equipment[:2]:
                eq_key = eq.lower().replace(" ", "_")
                if eq_key in self._anchors:
                    vectors.append(self._anchors[eq_key])
                    weights.append(0.20 / len(equipment[:2]))
                    break
        elif not equipment:
            # 无器械 → 偏向徒手
            if "bodyweight" in self._anchors:
                vectors.append(self._anchors["bodyweight"])
                weights.append(0.10)

        # 4. 伤病回避（权重 0.25，负方向）
        injuries = profile.get("injuries") or []
        if injuries:
            injury_weight = 0.25 / len(injuries[:3])
            for injury in injuries[:3]:
                area = ""
                if isinstance(injury, dict):
                    area = (injury.get("area") or "").lower()
                elif isinstance(injury, str):
                    area = injury.lower()

                avoid_key = None
                if "膝" in area or "knee" in area:
                    avoid_key = "avoid_knee"
                elif "腰" in area or "back" in area or "脊" in area:
                    avoid_key = "avoid_back"
                elif "肩" in area or "shoulder" in area:
                    avoid_key = "avoid_shoulder"
                elif "腕" in area or "wrist" in area:
                    avoid_key = "avoid_wrist"

                if avoid_key and avoid_key in self._anchors:
                    # 负方向：远离危险动作空间
                    vectors.append(-self._anchors[avoid_key])
                    weights.append(injury_weight)

        if not vectors:
            return None

        # 加权平均
        total_weight = sum(weights)
        bias = sum(v * w for v, w in zip(vectors, weights)) / total_weight

        # 归一化
        norm = np.linalg.norm(bias)
        if norm > 0:
            bias = bias / norm

        return bias

    # === 辅助 ===

    def _count_profile_fields(self, profile: Dict[str, Any]) -> int:
        """计算档案中有效字段数"""
        count = 0
        if profile.get("training_level") or profile.get("level"):
            count += 1
        if profile.get("goals") or profile.get("primary_goals"):
            count += 1
        if profile.get("available_equipment") or profile.get("equipment"):
            count += 1
        if profile.get("injuries"):
            count += 1
        if profile.get("body_metrics") or profile.get("weight"):
            count += 1
        return count


# === 全局单例 ===

_global_reshaper: Optional[QueryReshaper] = None


def get_query_reshaper() -> QueryReshaper:
    """获取全局 QueryReshaper 单例"""
    global _global_reshaper
    if _global_reshaper is None:
        _global_reshaper = QueryReshaper()
    return _global_reshaper
