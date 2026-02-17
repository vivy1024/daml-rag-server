# -*- coding: utf-8 -*-
"""
MCP工具参数Pydantic模型 - MCP Tool Parameter Models

Phase 3 Task 2: 为核心MCP工具定义Pydantic v2参数模型，
提供类型安全的参数验证、别名映射和自动类型转换。

覆盖工具类别：
- 运动搜索（intelligent_exercise_selector）
- 训练计划（professional_program_designer）
- 营养计划（meal_plan_designer / tdee_calculator）
- 安全检查（contraindications_checker）
- 用户档案（get_user_profile）

版本: v1.0.0
日期: 2026-02-17
"""

import logging
from typing import Optional, List, Literal
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)

# ============================================================
# 枚举常量（与 parameter_converter.py 保持一致）
# ============================================================

TrainingGoalLiteral = Literal[
    "hypertrophy", "strength", "endurance", "general_fitness",
    "weight_loss", "power", "maintenance", "recomp",
    "fat_loss", "posture_correction", "functional"
]

FitnessLevelLiteral = Literal[
    "novice", "beginner", "intermediate", "advanced", "expert"
]

SessionFocusLiteral = Literal[
    "compound", "isolation", "balanced"
]

ActivityLevelLiteral = Literal[
    "sedentary", "lightly_active", "moderately_active",
    "very_active", "extremely_active"
]

SplitTypeLiteral = Literal[
    "full_body", "upper_lower", "push_pull_legs", "body_part_split"
]

GenderLiteral = Literal["male", "female"]

# ============================================================
# 别名映射表（中文简称 → 标准名称）
# ============================================================

MUSCLE_GROUP_ALIASES = {
    # 简称 → 标准名
    "胸": "胸大肌", "背": "背阔肌", "肩": "三角肌",
    "腿": "股四头肌", "臂": "肱二头肌", "腹": "腹直肌",
    "臀": "臀大肌", "核心": "核心肌群",
    # 英文别名
    "chest": "胸大肌", "back": "背阔肌", "shoulder": "三角肌",
    "legs": "股四头肌", "arms": "肱二头肌", "abs": "腹直肌",
    "glutes": "臀大肌", "core": "核心肌群",
}

EQUIPMENT_ALIASES = {
    "杠铃": "barbell", "哑铃": "dumbbell", "器械": "machine",
    "自重": "bodyweight", "壶铃": "kettlebell", "弹力带": "resistance_band",
    "绳索": "cable",
}


def _resolve_muscle_alias(value: str) -> str:
    """解析肌肉群别名"""
    return MUSCLE_GROUP_ALIASES.get(value, value)


def _resolve_equipment_alias(value: str) -> str:
    """解析器械别名"""
    return EQUIPMENT_ALIASES.get(value, value)


def _coerce_int(v, field_name: str) -> Optional[int]:
    """安全地将值转换为int"""
    if v is None:
        return None
    if isinstance(v, int):
        return v
    if isinstance(v, float):
        return int(v)
    if isinstance(v, str):
        try:
            return int(float(v))
        except (ValueError, TypeError):
            logger.warning(f"无法将 {field_name}='{v}' 转换为int，使用None")
            return None
    return None


def _coerce_float(v, field_name: str) -> Optional[float]:
    """安全地将值转换为float"""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        try:
            return float(v)
        except (ValueError, TypeError):
            logger.warning(f"无法将 {field_name}='{v}' 转换为float，使用None")
            return None
    return None


# ============================================================
# 1. 运动搜索参数 - intelligent_exercise_selector
# ============================================================

class ExerciseSearchParams(BaseModel):
    """intelligent_exercise_selector 工具参数"""

    muscle_group: str = Field(description="目标肌肉群")
    training_goal: Optional[TrainingGoalLiteral] = Field(
        default=None, description="训练目标"
    )
    fitness_level: Optional[FitnessLevelLiteral] = Field(
        default=None, description="健身水平"
    )
    equipment: Optional[str] = Field(
        default=None, description="可用器械"
    )
    limit: Optional[int] = Field(
        default=10, ge=1, le=50, description="返回数量"
    )

    @field_validator("muscle_group", mode="before")
    @classmethod
    def resolve_muscle_group(cls, v):
        if isinstance(v, str):
            return _resolve_muscle_alias(v.strip())
        return v

    @field_validator("equipment", mode="before")
    @classmethod
    def resolve_equipment(cls, v):
        if isinstance(v, str):
            return _resolve_equipment_alias(v.strip())
        return v

    @field_validator("limit", mode="before")
    @classmethod
    def coerce_limit(cls, v):
        return _coerce_int(v, "limit")

    @field_validator("training_goal", mode="before")
    @classmethod
    def normalize_training_goal(cls, v):
        if isinstance(v, str):
            v = v.strip().lower()
        return v if v else None

    @field_validator("fitness_level", mode="before")
    @classmethod
    def normalize_fitness_level(cls, v):
        if isinstance(v, str):
            v = v.strip().lower()
        return v if v else None


# ============================================================
# 2. 训练计划参数 - professional_program_designer
# ============================================================

class TrainingPlanParams(BaseModel):
    """professional_program_designer 工具参数"""

    user_profile: Optional[str] = Field(
        default=None, description="用户档案JSON字符串"
    )
    training_goal: Optional[TrainingGoalLiteral] = Field(
        default="general_fitness", description="训练目标"
    )
    fitness_level: Optional[FitnessLevelLiteral] = Field(
        default="beginner", description="健身水平"
    )
    days_per_week: Optional[int] = Field(
        default=3, ge=1, le=7, description="每周训练天数"
    )
    session_duration: Optional[int] = Field(
        default=60, ge=15, le=180, description="每次训练时长(分钟)"
    )
    split_type: Optional[SplitTypeLiteral] = Field(
        default=None, description="训练分化类型"
    )
    available_equipment: Optional[List[str]] = Field(
        default=None, description="可用器械列表"
    )

    @field_validator("days_per_week", mode="before")
    @classmethod
    def coerce_days(cls, v):
        result = _coerce_int(v, "days_per_week")
        if result is not None:
            return max(1, min(7, result))
        return 3

    @field_validator("session_duration", mode="before")
    @classmethod
    def coerce_duration(cls, v):
        result = _coerce_int(v, "session_duration")
        if result is not None:
            return max(15, min(180, result))
        return 60

    @field_validator("training_goal", mode="before")
    @classmethod
    def normalize_goal(cls, v):
        if isinstance(v, str):
            v = v.strip().lower()
        return v if v else "general_fitness"

    @field_validator("fitness_level", mode="before")
    @classmethod
    def normalize_level(cls, v):
        if isinstance(v, str):
            v = v.strip().lower()
        return v if v else "beginner"

    @field_validator("available_equipment", mode="before")
    @classmethod
    def resolve_equipment_list(cls, v):
        if v is None:
            return None
        if isinstance(v, str):
            # "杠铃,哑铃" → ["barbell", "dumbbell"]
            items = [s.strip() for s in v.split(",") if s.strip()]
            return [_resolve_equipment_alias(item) for item in items]
        if isinstance(v, list):
            return [_resolve_equipment_alias(str(item)) for item in v]
        return v


# ============================================================
# 3. 营养计划参数 - meal_plan_designer / tdee_calculator
# ============================================================

class NutritionPlanParams(BaseModel):
    """meal_plan_designer / tdee_calculator 工具参数"""

    weight: Optional[float] = Field(
        default=None, gt=0, le=500, description="体重(kg)"
    )
    height: Optional[float] = Field(
        default=None, gt=0, le=300, description="身高(cm)"
    )
    age: Optional[int] = Field(
        default=None, ge=10, le=120, description="年龄"
    )
    gender: Optional[GenderLiteral] = Field(
        default=None, description="性别"
    )
    activity_level: Optional[ActivityLevelLiteral] = Field(
        default=None, description="活动水平"
    )
    training_goal: Optional[TrainingGoalLiteral] = Field(
        default=None, description="训练目标"
    )
    dietary_restrictions: Optional[List[str]] = Field(
        default=None, description="饮食限制"
    )
    meals_per_day: Optional[int] = Field(
        default=3, ge=1, le=8, description="每日餐数"
    )

    @field_validator("weight", mode="before")
    @classmethod
    def coerce_weight(cls, v):
        return _coerce_float(v, "weight")

    @field_validator("height", mode="before")
    @classmethod
    def coerce_height(cls, v):
        return _coerce_float(v, "height")

    @field_validator("age", mode="before")
    @classmethod
    def coerce_age(cls, v):
        return _coerce_int(v, "age")

    @field_validator("meals_per_day", mode="before")
    @classmethod
    def coerce_meals(cls, v):
        return _coerce_int(v, "meals_per_day")

    @field_validator("gender", mode="before")
    @classmethod
    def normalize_gender(cls, v):
        if isinstance(v, str):
            v = v.strip().lower()
            gender_map = {"男": "male", "女": "female", "m": "male", "f": "female"}
            return gender_map.get(v, v)
        return v


# ============================================================
# 4. 安全检查参数 - contraindications_checker
# ============================================================

class SafetyCheckParams(BaseModel):
    """contraindications_checker 工具参数"""

    exercise_name: str = Field(description="动作名称")
    health_conditions: Optional[List[str]] = Field(
        default=None, description="健康状况列表"
    )
    injuries: Optional[List[str]] = Field(
        default=None, description="伤病列表"
    )
    fitness_level: Optional[FitnessLevelLiteral] = Field(
        default=None, description="健身水平"
    )

    @field_validator("exercise_name", mode="before")
    @classmethod
    def clean_exercise_name(cls, v):
        if isinstance(v, str):
            return v.strip()
        return str(v) if v else ""

    @field_validator("health_conditions", mode="before")
    @classmethod
    def normalize_conditions(cls, v):
        if v is None:
            return None
        if isinstance(v, str):
            return [s.strip() for s in v.split(",") if s.strip()]
        return v

    @field_validator("injuries", mode="before")
    @classmethod
    def normalize_injuries(cls, v):
        if v is None:
            return None
        if isinstance(v, str):
            return [s.strip() for s in v.split(",") if s.strip()]
        return v


# ============================================================
# 5. 用户档案参数 - get_user_profile
# ============================================================

class UserProfileParams(BaseModel):
    """get_user_profile 工具参数"""

    user_id: str = Field(description="用户ID")

    @field_validator("user_id", mode="before")
    @classmethod
    def coerce_user_id(cls, v):
        """确保user_id是字符串"""
        if v is None:
            return ""
        return str(v).strip()


# ============================================================
# 6. 体态评估参数 - postural_assessor
# ============================================================

class PosturalAssessorParams(BaseModel):
    """postural_assessor 工具参数"""

    user_id: str = Field(description="用户ID")
    postural_issues: Optional[List[str]] = Field(
        default=None, description="体态问题列表"
    )
    include_exercises: Optional[bool] = Field(
        default=True, description="是否包含矫正动作"
    )
    max_exercises_per_issue: Optional[int] = Field(
        default=5, ge=1, le=20, description="每个问题最大动作数"
    )

    @field_validator("user_id", mode="before")
    @classmethod
    def coerce_user_id(cls, v):
        """确保user_id是字符串"""
        if v is None:
            return ""
        return str(v).strip()

    @field_validator("postural_issues", mode="before")
    @classmethod
    def normalize_postural_issues(cls, v):
        """支持逗号分隔字符串"""
        if v is None:
            return None
        if isinstance(v, str):
            return [s.strip() for s in v.split(",") if s.strip()]
        return v

    @field_validator("max_exercises_per_issue", mode="before")
    @classmethod
    def coerce_max_exercises(cls, v):
        """类型转换"""
        return _coerce_int(v, "max_exercises_per_issue")


# ============================================================
# 7. 伤病风险评估参数 - injury_risk_assessor
# ============================================================

class InjuryRiskAssessorParams(BaseModel):
    """injury_risk_assessor 工具参数"""

    user_id: str = Field(description="用户ID")
    exercise_name: Optional[str] = Field(
        default=None, description="动作名称"
    )
    health_conditions: Optional[List[str]] = Field(
        default=None, description="健康状况"
    )
    training_history: Optional[str] = Field(
        default=None, description="训练历史摘要"
    )

    @field_validator("user_id", mode="before")
    @classmethod
    def coerce_user_id(cls, v):
        """确保user_id是字符串"""
        if v is None:
            return ""
        return str(v).strip()

    @field_validator("exercise_name", mode="before")
    @classmethod
    def clean_exercise_name(cls, v):
        """清理动作名称"""
        if isinstance(v, str):
            return v.strip()
        return str(v) if v else None

    @field_validator("health_conditions", mode="before")
    @classmethod
    def normalize_health_conditions(cls, v):
        """支持逗号分隔字符串"""
        if v is None:
            return None
        if isinstance(v, str):
            return [s.strip() for s in v.split(",") if s.strip()]
        return v


# ============================================================
# 8. 动作模式平衡参数 - movement_pattern_balancer
# ============================================================

class MovementPatternBalancerParams(BaseModel):
    """movement_pattern_balancer 工具参数"""

    user_id: str = Field(description="用户ID")
    current_exercises: Optional[List[str]] = Field(
        default=None, description="当前训练动作列表"
    )
    training_goal: Optional[str] = Field(
        default=None, description="训练目标"
    )
    days_per_week: Optional[int] = Field(
        default=None, ge=1, le=7, description="每周训练天数"
    )

    @field_validator("user_id", mode="before")
    @classmethod
    def coerce_user_id(cls, v):
        """确保user_id是字符串"""
        if v is None:
            return ""
        return str(v).strip()

    @field_validator("current_exercises", mode="before")
    @classmethod
    def normalize_current_exercises(cls, v):
        """支持逗号分隔字符串"""
        if v is None:
            return None
        if isinstance(v, str):
            return [s.strip() for s in v.split(",") if s.strip()]
        return v

    @field_validator("days_per_week", mode="before")
    @classmethod
    def coerce_days(cls, v):
        """类型转换"""
        return _coerce_int(v, "days_per_week")


# ============================================================
# 工具名 → Pydantic模型 映射表
# ============================================================

TOOL_PARAM_MODELS = {
    # 运动搜索
    "intelligent_exercise_selector": ExerciseSearchParams,
    "intelligent-exercise-selector": ExerciseSearchParams,
    "exercise_alternative_finder": ExerciseSearchParams,
    "exercise-alternative-finder": ExerciseSearchParams,
    # 训练计划
    "professional_program_designer": TrainingPlanParams,
    "professional-program-designer": TrainingPlanParams,
    "periodized_program_designer": TrainingPlanParams,
    "periodized-program-designer": TrainingPlanParams,
    "training_split_designer": TrainingPlanParams,
    "training-split-designer": TrainingPlanParams,
    # 营养
    "meal_plan_designer": NutritionPlanParams,
    "meal-plan-designer": NutritionPlanParams,
    "tdee_calculator": NutritionPlanParams,
    "tdee-calculator": NutritionPlanParams,
    "nutrition_intake_analyzer": NutritionPlanParams,
    "nutrition-intake-analyzer": NutritionPlanParams,
    "exercise_nutrition_optimization": NutritionPlanParams,
    "exercise-nutrition-optimization": NutritionPlanParams,
    # 安全检查
    "contraindications_checker": SafetyCheckParams,
    "contraindications-checker": SafetyCheckParams,
    "safe_exercise_modifier": SafetyCheckParams,
    "safe-exercise-modifier": SafetyCheckParams,
    # 用户档案
    "get_user_profile": UserProfileParams,
    "get-user-profile": UserProfileParams,
    # 体态评估
    "postural_assessor": PosturalAssessorParams,
    "postural-assessor": PosturalAssessorParams,
    # 伤病风险（使用专用模型）
    "injury_risk_assessor": InjuryRiskAssessorParams,
    "injury-risk-assessor": InjuryRiskAssessorParams,
    # 动作模式平衡
    "movement_pattern_balancer": MovementPatternBalancerParams,
    "movement-pattern-balancer": MovementPatternBalancerParams,
}


def get_param_model(tool_name: str) -> Optional[type]:
    """根据工具名获取对应的Pydantic参数模型"""
    return TOOL_PARAM_MODELS.get(tool_name)
