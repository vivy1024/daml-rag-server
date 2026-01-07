# -*- coding: utf-8 -*-
"""
Few-Shot System Types - Few-Shot系统统一类型定义

统一前后端的Few-Shot数据结构，确保系统能够正确地进行推理时学习。

核心功能：
1. 统一的Few-Shot示例数据结构
2. 三轨评分筛选支持
3. 训练效果标签支持
4. 用户反馈文本存储

@author BUILD_BODY Team
@version 1.0.0
@created 2025-12-31
@requirements 4.1, 4.3, 4.4, 4.5
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


# ========== 训练效果标签 ==========
class TrainingEffectLabel(str, Enum):
    """
    训练效果标签枚举
    @requirements 4.4
    """
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"


# 训练效果标签配置
TRAINING_EFFECT_CONFIG: Dict[str, Dict[str, Any]] = {
    "excellent": {
        "label": "优秀",
        "description": "训练效果显著，完全达到预期目标",
        "color": "#52c41a",
        "min_score": 4.5
    },
    "good": {
        "label": "良好",
        "description": "训练效果良好，基本达到预期目标",
        "color": "#1890ff",
        "min_score": 4.0
    },
    "fair": {
        "label": "一般",
        "description": "训练效果一般，部分达到预期目标",
        "color": "#faad14",
        "min_score": 3.0
    },
    "poor": {
        "label": "较差",
        "description": "训练效果不佳，未达到预期目标",
        "color": "#ff4d4f",
        "min_score": 0
    }
}


# ========== 三轨评分详情 ==========
@dataclass
class ThreeTrackScores:
    """三轨评分详情"""
    user_experience_avg: Optional[float] = None    # 用户体验平均分
    personalization_avg: Optional[float] = None    # 个性化感知平均分
    expert_avg: Optional[float] = None             # 专家评分平均分（可选）
    safety_score: Optional[float] = None           # 安全性评分（可选）
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "user_experience_avg": self.user_experience_avg,
            "personalization_avg": self.personalization_avg,
            "expert_avg": self.expert_avg,
            "safety_score": self.safety_score
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ThreeTrackScores":
        """从字典创建实例"""
        return cls(
            user_experience_avg=data.get("user_experience_avg"),
            personalization_avg=data.get("personalization_avg"),
            expert_avg=data.get("expert_avg"),
            safety_score=data.get("safety_score")
        )


# ========== Few-Shot元数据 ==========
@dataclass
class FewShotMetadata:
    """Few-Shot元数据"""
    # 训练相关
    training_goal: Optional[str] = None           # 训练目标（增肌/减脂/力量等）
    training_level: Optional[str] = None          # 训练水平（初级/中级/高级）
    
    # 用户档案相关
    profile_utilization_rate: Optional[float] = None  # 档案利用率 (0-100)
    personalization_grade: Optional[str] = None       # 个性化等级 (S/A/B/C/D)
    
    # 查询相关
    query_complexity: Optional[bool] = None       # 查询复杂度
    query_category: Optional[str] = None          # 查询类别
    
    # 扩展字段
    extra: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = {
            "training_goal": self.training_goal,
            "training_level": self.training_level,
            "profile_utilization_rate": self.profile_utilization_rate,
            "personalization_grade": self.personalization_grade,
            "query_complexity": self.query_complexity,
            "query_category": self.query_category
        }
        result.update(self.extra)
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FewShotMetadata":
        """从字典创建实例"""
        known_keys = {
            "training_goal", "training_level", "profile_utilization_rate",
            "personalization_grade", "query_complexity", "query_category"
        }
        extra = {k: v for k, v in data.items() if k not in known_keys}
        
        return cls(
            training_goal=data.get("training_goal"),
            training_level=data.get("training_level"),
            profile_utilization_rate=data.get("profile_utilization_rate"),
            personalization_grade=data.get("personalization_grade"),
            query_complexity=data.get("query_complexity"),
            query_category=data.get("query_category"),
            extra=extra
        )


# ========== Few-Shot示例数据结构 ==========
@dataclass
class UnifiedFewShotExample:
    """
    统一的Few-Shot示例数据结构
    
    与前端TypeScript定义保持一致，确保前后端数据结构统一。
    
    @requirements 4.1
    """
    # 基础信息
    id: str                                       # 唯一标识
    query: str                                    # 用户问题
    response: str                                 # 系统回复
    session_id: str                               # 会话ID
    user_id: Optional[str] = None                 # 用户ID（可选）
    
    # 工具和模型信息
    tools_used: List[str] = field(default_factory=list)  # 使用的工具列表
    model_used: str = ""                          # 使用的模型
    
    # 三轨评分 @requirements 4.3
    user_rating: float = 0.0                      # 用户评分 (1-5)
    quality_score: float = 0.0                    # 质量评分 (0-5)
    similarity: float = 0.0                       # 相似度 (0-1)
    
    # 三轨评分详情
    three_track_scores: Optional[ThreeTrackScores] = None
    
    # 训练效果标签 @requirements 4.4
    training_effect: Optional[str] = None
    
    # 用户反馈 @requirements 4.5
    user_feedback: Optional[str] = None
    
    # 元数据
    metadata: FewShotMetadata = field(default_factory=FewShotMetadata)
    
    # 时间戳
    timestamp: datetime = field(default_factory=datetime.now)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    # Few-Shot资格
    fewshot_eligible: bool = False
    
    # 向量信息（可选）
    embedding: Optional[List[float]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式（与前端兼容）"""
        return {
            "id": self.id,
            "query": self.query,
            "response": self.response,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "tools_used": self.tools_used,
            "model_used": self.model_used,
            "user_rating": self.user_rating,
            "quality_score": self.quality_score,
            "similarity": self.similarity,
            "three_track_scores": self.three_track_scores.to_dict() if self.three_track_scores else None,
            "training_effect": self.training_effect,
            "user_feedback": self.user_feedback,
            "metadata": self.metadata.to_dict() if isinstance(self.metadata, FewShotMetadata) else self.metadata,
            "timestamp": self.timestamp.isoformat() if isinstance(self.timestamp, datetime) else self.timestamp,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "fewshot_eligible": self.fewshot_eligible,
            "embedding": self.embedding
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UnifiedFewShotExample":
        """从字典创建实例"""
        # 处理时间戳
        timestamp = data.get("timestamp")
        if isinstance(timestamp, str):
            try:
                timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            except:
                timestamp = datetime.now()
        elif not isinstance(timestamp, datetime):
            timestamp = datetime.now()
        
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            except:
                created_at = None
        
        updated_at = data.get("updated_at")
        if isinstance(updated_at, str):
            try:
                updated_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
            except:
                updated_at = None
        
        # 处理三轨评分
        three_track_scores = data.get("three_track_scores")
        if isinstance(three_track_scores, dict):
            three_track_scores = ThreeTrackScores.from_dict(three_track_scores)
        
        # 处理元数据
        metadata = data.get("metadata", {})
        if isinstance(metadata, dict):
            metadata = FewShotMetadata.from_dict(metadata)
        
        return cls(
            id=str(data.get("id", data.get("session_id", ""))),
            query=str(data.get("query", data.get("user_query", ""))),
            response=str(data.get("response", data.get("llm_response", ""))),
            session_id=str(data.get("session_id", "")),
            user_id=str(data.get("user_id")) if data.get("user_id") else None,
            tools_used=data.get("tools_used", []) or [],
            model_used=str(data.get("model_used", "")),
            user_rating=float(data.get("user_rating", data.get("reward", 0))),
            quality_score=float(data.get("quality_score", 0)),
            similarity=float(data.get("similarity", 0)),
            three_track_scores=three_track_scores,
            training_effect=data.get("training_effect"),
            user_feedback=data.get("user_feedback"),
            metadata=metadata,
            timestamp=timestamp,
            created_at=created_at,
            updated_at=updated_at,
            fewshot_eligible=bool(data.get("fewshot_eligible", False)),
            embedding=data.get("embedding")
        )


# ========== Few-Shot检索相关 ==========
@dataclass
class FewShotRetrieveRequest:
    """Few-Shot检索请求"""
    query: str                                    # 查询文本
    user_id: Optional[str] = None                 # 用户ID
    training_goal: Optional[str] = None           # 训练目标过滤
    min_quality_score: float = 4.0                # 最低质量评分
    training_effect_filter: Optional[str] = None  # 训练效果过滤
    top_k: int = 5                                # 返回数量
    only_fewshot_eligible: bool = True            # 只返回符合Few-Shot条件的


@dataclass
class FewShotRetrievalStats:
    """Few-Shot检索统计"""
    query_complexity: Optional[bool] = None
    similarity_threshold: float = 0.0
    total_candidates: int = 0
    quality_filtered: int = 0
    similarity_filtered: int = 0
    diversity_filtered: int = 0
    final_examples: int = 0
    execution_time_ms: float = 0.0
    avg_quality: float = 0.0
    avg_similarity: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "query_complexity": self.query_complexity,
            "similarity_threshold": self.similarity_threshold,
            "total_candidates": self.total_candidates,
            "quality_filtered": self.quality_filtered,
            "similarity_filtered": self.similarity_filtered,
            "diversity_filtered": self.diversity_filtered,
            "final_examples": self.final_examples,
            "execution_time_ms": self.execution_time_ms,
            "avg_quality": self.avg_quality,
            "avg_similarity": self.avg_similarity
        }


@dataclass
class FewShotRetrieveResponse:
    """Few-Shot检索响应"""
    success: bool
    examples: List[UnifiedFewShotExample] = field(default_factory=list)
    total_found: int = 0
    retrieval_stats: FewShotRetrievalStats = field(default_factory=FewShotRetrievalStats)
    filters_applied: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "success": self.success,
            "examples": [ex.to_dict() for ex in self.examples],
            "total_found": self.total_found,
            "retrieval_stats": self.retrieval_stats.to_dict(),
            "filters_applied": self.filters_applied,
            "error": self.error
        }


# ========== Few-Shot池统计 ==========
@dataclass
class FewShotPoolStats:
    """Few-Shot池统计"""
    total_sessions: int = 0
    rated_sessions: int = 0
    eligible_sessions: int = 0
    eligibility_rate: float = 0.0
    grade_distribution: Dict[str, int] = field(default_factory=dict)
    safety_veto_count: int = 0
    thresholds: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "total_sessions": self.total_sessions,
            "rated_sessions": self.rated_sessions,
            "eligible_sessions": self.eligible_sessions,
            "eligibility_rate": self.eligibility_rate,
            "grade_distribution": self.grade_distribution,
            "safety_veto_count": self.safety_veto_count,
            "thresholds": self.thresholds
        }


# ========== Few-Shot准入检查 ==========
@dataclass
class FewShotEligibilityResult:
    """Few-Shot准入检查结果"""
    eligible: bool = False
    reason: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "eligible": self.eligible,
            "reason": self.reason,
            "details": self.details
        }


# ========== 工具函数 ==========
def get_training_effect_from_score(score: float) -> str:
    """
    根据质量评分获取训练效果标签
    
    Args:
        score: 质量评分 (0-5)
    
    Returns:
        训练效果标签
    """
    if score >= TRAINING_EFFECT_CONFIG["excellent"]["min_score"]:
        return TrainingEffectLabel.EXCELLENT.value
    if score >= TRAINING_EFFECT_CONFIG["good"]["min_score"]:
        return TrainingEffectLabel.GOOD.value
    if score >= TRAINING_EFFECT_CONFIG["fair"]["min_score"]:
        return TrainingEffectLabel.FAIR.value
    return TrainingEffectLabel.POOR.value


def get_training_effect_config(effect: str) -> Dict[str, Any]:
    """
    获取训练效果标签配置
    
    Args:
        effect: 训练效果标签
    
    Returns:
        配置字典
    """
    return TRAINING_EFFECT_CONFIG.get(effect, TRAINING_EFFECT_CONFIG["fair"])


def check_basic_fewshot_eligibility(example: Dict[str, Any]) -> bool:
    """
    检查是否符合Few-Shot基本条件
    
    Args:
        example: Few-Shot示例数据
    
    Returns:
        是否符合条件
    """
    MIN_QUALITY_SCORE = 4.0
    MIN_USER_RATING = 4.0
    SAFETY_VETO_THRESHOLD = 3
    
    quality_score = example.get("quality_score", 0)
    user_rating = example.get("user_rating", 0)
    
    if quality_score < MIN_QUALITY_SCORE:
        return False
    
    if user_rating < MIN_USER_RATING:
        return False
    
    # 检查三轨评分（如果有）
    three_track_scores = example.get("three_track_scores")
    if three_track_scores:
        user_experience_avg = three_track_scores.get("user_experience_avg")
        personalization_avg = three_track_scores.get("personalization_avg")
        safety_score = three_track_scores.get("safety_score")
        
        # 用户体验评分检查
        if user_experience_avg is not None and user_experience_avg < MIN_QUALITY_SCORE:
            return False
        
        # 个性化感知评分检查
        if personalization_avg is not None and personalization_avg < MIN_QUALITY_SCORE:
            return False
        
        # 安全性一票否决
        if safety_score is not None and safety_score < SAFETY_VETO_THRESHOLD:
            return False
    
    return True


def convert_legacy_fewshot_example(legacy_example: Any) -> UnifiedFewShotExample:
    """
    将旧版FewShotExample转换为统一格式
    
    Args:
        legacy_example: 旧版FewShotExample对象
    
    Returns:
        UnifiedFewShotExample对象
    """
    # 处理dataclass或dict
    if hasattr(legacy_example, "__dict__"):
        data = {
            "id": getattr(legacy_example, "session_id", ""),
            "query": getattr(legacy_example, "query", ""),
            "response": getattr(legacy_example, "response", ""),
            "session_id": getattr(legacy_example, "session_id", ""),
            "tools_used": getattr(legacy_example, "tools_used", []),
            "model_used": getattr(legacy_example, "model_used", ""),
            "user_rating": getattr(legacy_example, "user_rating", 0),
            "quality_score": getattr(legacy_example, "quality_score", 0),
            "similarity": getattr(legacy_example, "similarity", 0),
            "training_effect": getattr(legacy_example, "training_effect", None),
            "user_feedback": getattr(legacy_example, "user_feedback", None),
            "metadata": getattr(legacy_example, "metadata", {}),
            "timestamp": getattr(legacy_example, "timestamp", datetime.now()),
            "fewshot_eligible": True  # 旧版默认符合条件
        }
    else:
        data = dict(legacy_example)
    
    return UnifiedFewShotExample.from_dict(data)


# 导出
__all__ = [
    "TrainingEffectLabel",
    "TRAINING_EFFECT_CONFIG",
    "ThreeTrackScores",
    "FewShotMetadata",
    "UnifiedFewShotExample",
    "FewShotRetrieveRequest",
    "FewShotRetrievalStats",
    "FewShotRetrieveResponse",
    "FewShotPoolStats",
    "FewShotEligibilityResult",
    "get_training_effect_from_score",
    "get_training_effect_config",
    "check_basic_fewshot_eligibility",
    "convert_legacy_fewshot_example"
]
