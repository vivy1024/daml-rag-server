# -*- coding: utf-8 -*-
"""
Fitness Services Module

提供健身应用的核心服务类
"""

from .training_log_analyzer import TrainingLogAnalyzer
from .weekly_plan_generator import WeeklyPlanGenerator
from .training_plan_summarizer import TrainingPlanSummarizer  # TODO: legacy，核心功能已被 tool_result_summarizer 替代
from .safety_reminder_generator import SafetyReminderGenerator  # TODO: 待接入工作流（步骤10 LLM输出后处理）
from .volume_adjuster import VolumeAdjuster  # TODO: 待接入工作流（periodized_program_designer）
from .exercise_stability_manager import ExerciseStabilityManager  # TODO: 待接入工作流（professional_program_designer）
from .training_goal_recommender import (  # TODO: 待接入工作流（greeting模板）
    TrainingGoalRecommender,
    get_training_goal_recommender,
    UserType
)
from .equipment_alias_mapper import (
    EquipmentAliasMapper,
    get_equipment_alias_mapper,
    reset_equipment_alias_mapper
)
from .user_profile_integrator import UserProfileIntegrator
from .three_track_rating import (
    ThreeTrackRatingService,
    ThreeTrackRatingResult,
    PersonalizationScores,
    PersonalizationGrade,
    create_three_track_rating_service
)
from .credit_reporter import (
    CreditReporter,
    get_credit_reporter,
    reset_credit_reporter,
    report_credit_consumption
)

# 已删除（计算逻辑统一到 PHP Calculator Service）:
# - intensity_converter.py (834行) → PHP IntensityConverter
# - progressive_overload.py (619行) → PHP WeightRecommender

__all__ = [
    'TrainingLogAnalyzer',
    'WeeklyPlanGenerator',
    'TrainingPlanSummarizer',
    'SafetyReminderGenerator',
    'VolumeAdjuster',
    'ExerciseStabilityManager',
    'TrainingGoalRecommender',
    'get_training_goal_recommender',
    'UserType',
    'EquipmentAliasMapper',
    'get_equipment_alias_mapper',
    'reset_equipment_alias_mapper',
    'UserProfileIntegrator',
    # 三轨评分服务
    'ThreeTrackRatingService',
    'ThreeTrackRatingResult',
    'PersonalizationScores',
    'PersonalizationGrade',
    'create_three_track_rating_service',
    # 积分上报服务
    'CreditReporter',
    'get_credit_reporter',
    'reset_credit_reporter',
    'report_credit_consumption',
]
