# -*- coding: utf-8 -*-
"""
Fitness Services Module

提供健身应用的核心服务类
"""

from .training_log_analyzer import TrainingLogAnalyzer
from .weekly_plan_generator import WeeklyPlanGenerator
from .training_plan_summarizer import TrainingPlanSummarizer
from .safety_reminder_generator import SafetyReminderGenerator
from .volume_adjuster import VolumeAdjuster
from .progressive_overload import ProgressiveOverloadCalculator
from .exercise_stability_manager import ExerciseStabilityManager
from .training_goal_recommender import (
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
from .intensity_converter import (
    IntensityConverter,
    IntensityMetric,
    IntensityValue,
    IntensityConversionResult,
    IntensityRecommendation,
    TrainingGoal,
    get_intensity_converter,
    reset_intensity_converter
)
from .credit_reporter import (
    CreditReporter,
    get_credit_reporter,
    reset_credit_reporter,
    report_credit_consumption
)

__all__ = [
    'TrainingLogAnalyzer', 
    'WeeklyPlanGenerator', 
    'TrainingPlanSummarizer',
    'SafetyReminderGenerator',
    'VolumeAdjuster',
    'ProgressiveOverloadCalculator',
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
    # 强度转换服务
    'IntensityConverter',
    'IntensityMetric',
    'IntensityValue',
    'IntensityConversionResult',
    'IntensityRecommendation',
    'TrainingGoal',
    'get_intensity_converter',
    'reset_intensity_converter',
    # 积分上报服务
    'CreditReporter',
    'get_credit_reporter',
    'reset_credit_reporter',
    'report_credit_consumption',
]
