# -*- coding: utf-8 -*-
"""
专业程序设计器 — 数据模型

枚举类型 + Pydantic输入/输出Schema
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal
from enum import Enum

from ....types.enums import TrainingGoal, DifficultyLevel

# =============================================================================
# 枚举类型定义
# =============================================================================

class TrainingSplit(str, Enum):
    """训练分化"""
    FULL_BODY = "full_body"
    UPPER_LOWER = "upper_lower"
    PUSH_PULL_LEGS = "push_pull_legs"
    BRO_SPLIT = "bro_split"


# =============================================================================
# 输入Schema定义
# =============================================================================

class ProfessionalProgramDesignerInput(BaseModel):
    """专业程序设计器输入Schema"""

    user_id: str = Field(..., description="用户ID")
    training_goal: TrainingGoal = Field(..., description="训练目标")
    training_split: TrainingSplit = Field(..., description="训练分化方式")
    training_days_per_week: int = Field(..., ge=1, le=7, description="每周训练天数")
    difficulty_level: DifficultyLevel = Field(..., description="难度等级")
    available_equipment: List[str] = Field(..., description="可用器械列表")
    injury_history: Optional[List[str]] = Field(None, description="损伤历史（可选）")
    target_muscle_groups: Optional[List[str]] = Field(None, description="目标肌群列表（可选）")
    session_duration_minutes: Optional[int] = Field(60, ge=30, le=180, description="单次训练时长（分钟）")
    include_warmup: bool = Field(True, description="是否包含热身")
    include_cooldown: bool = Field(True, description="是否包含放松")
    training_weeks: Optional[int] = Field(4, ge=1, le=16, description="训练周数（默认4周）")
    rest_pattern: Optional[str] = Field(None, description="休息模式（如'练三休一'、'练六休一'）")


# =============================================================================
# 输出Schema定义
# =============================================================================

class ExerciseInProgram(BaseModel):
    """
    计划中的动作（精简版）

    设计原则：
    - 只保留核心训练参数，节省LLM token
    - 动作详情通过exercise_id跳转详情页查看
    """
    exercise_id: str = Field(..., description="动作ID，用于跳转详情页")
    name_zh: str = Field(..., description="动作中文名称")
    sets: int = Field(..., description="组数")
    reps_range: tuple[int, int] = Field(..., description="次数范围，如(8,12)")
    rest_seconds: int = Field(..., description="组间休息时间（秒）")
    weight: Optional[str] = Field(None, description="个性化重量建议")


class TrainingDay(BaseModel):
    """训练日"""
    day_number: int
    day_name: str
    focus_muscle_groups: List[str]
    exercises: List[ExerciseInProgram]
    total_sets: int
    estimated_duration_minutes: int


class WeeklyProgram(BaseModel):
    """周训练计划"""
    week_number: int
    training_days: List[TrainingDay]
    rest_days: List[int]
    total_weekly_sets: int
    muscle_group_distribution: Dict[str, int]
    cycle_days: Optional[int] = None
    cycles_per_week: Optional[float] = None
    training_pattern: Optional[str] = None


class ProgramBalance(BaseModel):
    """计划平衡性分析"""
    muscle_group_coverage: Dict[str, str]
    movement_pattern_balance: Dict[str, int]
    push_pull_ratio: str
    compound_isolation_ratio: str
    balance_score: float
    recommendations: List[str]


class SafetyAssessment(BaseModel):
    """安全评估（优化版）"""
    overall_risk_level: Literal["LOW", "MODERATE", "HIGH", "CRITICAL"]
    contraindications_found: int = Field(default=0)
    safety_recommendations: List[str] = Field(default_factory=list)
    personalized_notes: List[str] = Field(default_factory=list)
    medical_consultation_needed: bool = Field(default=False)


class ProfessionalProgramDesignerOutput(BaseModel):
    """专业程序设计器输出Schema"""
    success: bool
    tool_name: str
    user_id: str
    program_overview: Dict[str, Any]
    weekly_program: WeeklyProgram
    program_balance: ProgramBalance
    safety_assessment: SafetyAssessment
    execution_guidelines: List[str]
    important_notes: List[str]
    execution_time_ms: float
    confidence_score: float
    tools_called: List[str]
