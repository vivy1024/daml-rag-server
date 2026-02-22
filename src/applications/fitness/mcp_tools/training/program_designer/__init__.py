# -*- coding: utf-8 -*-
"""
专业程序设计器 — 子模块

拆分结构:
- models.py: 枚举 + Pydantic schemas
- volume_mixin.py: 训练量计算 + 周期化 + 减量日
- program_generator_mixin.py: 周计划生成 + 训练日创建 + 热身/放松
- program_analysis_mixin.py: 平衡分析 + 安全评估 + 执行建议
"""
from .models import (
    TrainingGoal,
    TrainingSplit,
    DifficultyLevel,
    ProfessionalProgramDesignerInput,
    ExerciseInProgram,
    TrainingDay,
    WeeklyProgram,
    ProgramBalance,
    SafetyAssessment,
    ProfessionalProgramDesignerOutput,
)
