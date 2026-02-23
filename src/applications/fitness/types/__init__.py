# -*- coding: utf-8 -*-
"""
Fitness Application Types - 健身应用类型定义

统一的类型定义模块，包含：
- Few-Shot系统类型
- 其他共享类型

@version 1.0.0
@created 2025-12-31
"""

from .enums import (
    TrainingGoal,
    DifficultyLevel,
    FitnessLevel,
    NutritionGoal,
    MembershipTier,
)

from .fewshot_types import (
    TrainingEffectLabel,
    TRAINING_EFFECT_CONFIG,
    ThreeTrackScores,
    FewShotMetadata,
    UnifiedFewShotExample,
    FewShotRetrieveRequest,
    FewShotRetrievalStats,
    FewShotRetrieveResponse,
    FewShotPoolStats,
    FewShotEligibilityResult,
    get_training_effect_from_score,
    get_training_effect_config,
    check_basic_fewshot_eligibility,
    convert_legacy_fewshot_example
)

__all__ = [
    # 权威枚举
    "TrainingGoal",
    "DifficultyLevel",
    "FitnessLevel",
    "NutritionGoal",
    "MembershipTier",
    # Few-Shot类型
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
    # Few-Shot工具函数
    "get_training_effect_from_score",
    "get_training_effect_config",
    "check_basic_fewshot_eligibility",
    "convert_legacy_fewshot_example"
]
