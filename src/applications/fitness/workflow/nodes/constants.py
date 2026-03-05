# -*- coding: utf-8 -*-
"""工作流节点常量"""

# MCP工具类型列表（15个Python MCP工具）
MCP_TASK_TYPES = [
    # 训练计划相关（5个）
    "intelligent_exercise_selector",
    "professional_program_designer",
    "periodized_program_designer",
    "training_split_designer",
    "intelligent_weight_calculator",
    # 安全与康复相关（5个）
    "contraindications_checker",
    "injury_risk_assessor",
    "exercise_alternative_finder",
    "safe_exercise_modifier",
    "movement_pattern_balancer",
    # 训练量与恢复相关（2个）
    "muscle_group_volume_calculator",
    "tdee_calculator",
    # 营养相关（3个）
    "nutrition_intake_analyzer",
    "meal_plan_designer",
    "exercise_nutrition_optimization"
]

# 工作流程步骤列表（不是MCP工具）
WORKFLOW_STEPS = [
    "get_user_profile",
    "get_user_membership",
    "semantic_search",
    "three_layer_retrieval",
    "assess_fitness_level",
    "analyze_nutrition_needs",
    "search_foods"
]
