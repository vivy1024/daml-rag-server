# -*- coding: utf-8 -*-
"""
MCP工具Schema注册表 - MCP Tool Schema Registry

定义所有16个MCP工具的完整参数Schema，用于参数验证。

核心功能：
1. 定义TOOL_SCHEMAS字典（16个MCP工具的完整Schema）
2. 实现get_schema方法获取工具Schema
3. 实现get_required_params方法获取必需参数列表
4. 实现get_param_type方法获取参数类型

版本: v1.0.0
日期: 2025-12-29
Requirements: 8.1, 8.5
"""

import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


# =============================================================================
# 参数类型定义
# =============================================================================

class ParamType:
    """参数类型常量"""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    LIST = "list"
    DICT = "dict"
    ENUM = "enum"


# =============================================================================
# MCP工具Schema定义
# =============================================================================

TOOL_SCHEMAS: Dict[str, Dict[str, Any]] = {
    # =========================================================================
    # 用户档案工具
    # =========================================================================
    "get_user_profile": {
        "name": "get_user_profile",
        "description": "获取用户档案",
        "category": "user",
        "parameters": {
            "user_id": {
                "type": ParamType.STRING,
                "required": True,
                "description": "用户ID"
            }
        }
    },
    
    # =========================================================================
    # 动作相关工具
    # =========================================================================
    "intelligent_exercise_selector": {
        "name": "intelligent_exercise_selector",
        "description": "智能动作选择器 - 基于三层检索引擎的个性化动作推荐",
        "category": "exercise",
        "parameters": {
            "user_id": {
                "type": ParamType.STRING,
                "required": True,
                "description": "用户ID，用于获取个人化条件"
            },
            "muscle_group": {
                "type": ParamType.STRING,
                "required": True,
                "description": "目标肌群（如：胸、背、腿、肩、手臂、核心、臀部、小腿）"
            },
            "training_goal": {
                "type": ParamType.ENUM,
                "required": True,
                "description": "训练目标",
                "enum_values": ["strength", "hypertrophy", "endurance", "general_fitness", "fat_loss", "posture_correction", "functional"]
            },
            "difficulty_level": {
                "type": ParamType.ENUM,
                "required": True,
                "description": "难度等级",
                "enum_values": ["beginner", "intermediate", "advanced"]
            },
            "available_equipment": {
                "type": ParamType.LIST,
                "required": True,
                "description": "可用器械列表"
            },
            "injury_history": {
                "type": ParamType.LIST,
                "required": False,
                "description": "损伤历史（可选）",
                "default": None
            },
            "exercise_preferences": {
                "type": ParamType.LIST,
                "required": False,
                "description": "运动偏好（可选）",
                "default": None
            },
            "disliked_exercises": {
                "type": ParamType.LIST,
                "required": False,
                "description": "不喜欢的动作（可选）",
                "default": None
            },
            "session_focus": {
                "type": ParamType.ENUM,
                "required": False,
                "description": "训练重点（可选）",
                "enum_values": ["compound", "isolation", "balanced"],
                "default": None
            },
            "safety_priority": {
                "type": ParamType.BOOLEAN,
                "required": False,
                "description": "是否优先考虑安全性",
                "default": True
            }
        }
    },
    
    "exercise_alternative_finder": {
        "name": "exercise_alternative_finder",
        "description": "动作替代查找器 - 查找替代动作",
        "category": "exercise",
        "parameters": {
            "user_id": {
                "type": ParamType.STRING,
                "required": True,
                "description": "用户ID"
            },
            "original_exercise_id": {
                "type": ParamType.STRING,
                "required": True,
                "description": "原始动作ID"
            },
            "reason": {
                "type": ParamType.ENUM,
                "required": True,
                "description": "替代原因",
                "enum_values": ["injury", "equipment_unavailable", "difficulty_too_high", "preference_change", "variety"]
            },
            "constraints": {
                "type": ParamType.DICT,
                "required": False,
                "description": "约束条件",
                "default": {}
            }
        }
    },
    
    # =========================================================================
    # 安全相关工具
    # =========================================================================
    "contraindications_checker": {
        "name": "contraindications_checker",
        "description": "禁忌症检查器 - 基于用户档案和Neo4j数据的医学安全检查",
        "category": "safety",
        "parameters": {
            "user_id": {
                "type": ParamType.STRING,
                "required": True,
                "description": "用户ID，用于获取健康状况"
            },
            "exercise_ids": {
                "type": ParamType.LIST,
                "required": True,
                "description": "要检查的动作ID列表"
            },
            "health_conditions": {
                "type": ParamType.LIST,
                "required": False,
                "description": "额外健康状况（可选）",
                "default": None
            },
            "include_recommendations": {
                "type": ParamType.BOOLEAN,
                "required": False,
                "description": "是否包含安全建议",
                "default": True
            },
            "strict_mode": {
                "type": ParamType.BOOLEAN,
                "required": False,
                "description": "严格模式：更保守的安全阈值",
                "default": False
            }
        }
    },
    
    "safe_exercise_modifier": {
        "name": "safe_exercise_modifier",
        "description": "安全动作修饰器 - 提供动作的安全修改建议",
        "category": "safety",
        "parameters": {
            "user_id": {
                "type": ParamType.STRING,
                "required": True,
                "description": "用户ID，用于获取个人化安全参数"
            },
            "exercise_id": {
                "type": ParamType.STRING,
                "required": True,
                "description": "动作ID"
            },
            "modification_purpose": {
                "type": ParamType.ENUM,
                "required": True,
                "description": "修改目的",
                "enum_values": ["injury_prevention", "beginner_friendly", "rehabilitation", "age_appropriate", "equipment_limited"]
            },
            "user_injuries": {
                "type": ParamType.LIST,
                "required": False,
                "description": "用户损伤列表",
                "default": []
            },
            "safety_requirements": {
                "type": ParamType.LIST,
                "required": False,
                "description": "安全要求",
                "default": []
            },
            "available_equipment": {
                "type": ParamType.LIST,
                "required": False,
                "description": "可用器械",
                "default": []
            },
            "modification_preference": {
                "type": ParamType.STRING,
                "required": False,
                "description": "修改偏好",
                "default": "moderate"
            }
        }
    },
    
    "injury_risk_assessor": {
        "name": "injury_risk_assessor",
        "description": "损伤风险评估器 - 评估训练计划的损伤风险",
        "category": "safety",
        "parameters": {
            "user_id": {
                "type": ParamType.STRING,
                "required": True,
                "description": "用户ID，用于获取个人风险档案"
            },
            "planned_exercises": {
                "type": ParamType.LIST,
                "required": True,
                "description": "计划执行的动作列表"
            },
            "training_intensity": {
                "type": ParamType.ENUM,
                "required": True,
                "description": "训练强度",
                "enum_values": ["low", "moderate", "high", "very_high"]
            },
            "session_duration_minutes": {
                "type": ParamType.INTEGER,
                "required": True,
                "description": "训练时长（分钟）"
            },
            "include_prevention_plan": {
                "type": ParamType.BOOLEAN,
                "required": False,
                "description": "是否包含预防计划",
                "default": True
            },
            "risk_tolerance_level": {
                "type": ParamType.STRING,
                "required": False,
                "description": "风险容忍度",
                "default": "moderate"
            },
            "previous_injuries": {
                "type": ParamType.LIST,
                "required": False,
                "description": "既往损伤",
                "default": []
            },
            "current_pain_areas": {
                "type": ParamType.LIST,
                "required": False,
                "description": "当前疼痛部位",
                "default": []
            }
        }
    },

    # =========================================================================
    # 训练计划相关工具
    # =========================================================================
    "professional_program_designer": {
        "name": "professional_program_designer",
        "description": "专业程序设计器 - 综合多个工具结果生成完整训练计划",
        "category": "training",
        "parameters": {
            "user_id": {
                "type": ParamType.STRING,
                "required": True,
                "description": "用户ID"
            },
            "training_goal": {
                "type": ParamType.ENUM,
                "required": True,
                "description": "训练目标",
                "enum_values": ["strength", "hypertrophy", "endurance", "general_fitness", "fat_loss", "posture_correction", "functional"]
            },
            "training_split": {
                "type": ParamType.ENUM,
                "required": True,
                "description": "训练分化方式",
                "enum_values": ["full_body", "upper_lower", "push_pull_legs", "bro_split"]
            },
            "training_days_per_week": {
                "type": ParamType.INTEGER,
                "required": True,
                "description": "每周训练天数"
            },
            "difficulty_level": {
                "type": ParamType.ENUM,
                "required": True,
                "description": "难度等级",
                "enum_values": ["beginner", "intermediate", "advanced"]
            },
            "available_equipment": {
                "type": ParamType.LIST,
                "required": True,
                "description": "可用器械列表"
            },
            "injury_history": {
                "type": ParamType.LIST,
                "required": False,
                "description": "损伤历史（可选）",
                "default": None
            },
            "target_muscle_groups": {
                "type": ParamType.LIST,
                "required": False,
                "description": "目标肌群列表（可选）",
                "default": None
            },
            "session_duration_minutes": {
                "type": ParamType.INTEGER,
                "required": False,
                "description": "单次训练时长（分钟）",
                "default": 60
            }
        }
    },
    
    "periodized_program_designer": {
        "name": "periodized_program_designer",
        "description": "周期化程序设计器 - 生成周期化训练计划",
        "category": "training",
        "parameters": {
            "user_id": {
                "type": ParamType.STRING,
                "required": True,
                "description": "用户ID"
            },
            "training_goal": {
                "type": ParamType.ENUM,
                "required": True,
                "description": "训练目标",
                "enum_values": ["strength", "hypertrophy", "endurance", "general_fitness", "fat_loss", "posture_correction", "functional"]
            },
            "difficulty_level": {
                "type": ParamType.ENUM,
                "required": True,
                "description": "难度等级",
                "enum_values": ["beginner", "intermediate", "advanced"]
            },
            "program_duration_weeks": {
                "type": ParamType.INTEGER,
                "required": True,
                "description": "计划周数"
            },
            "training_days_per_week": {
                "type": ParamType.INTEGER,
                "required": True,
                "description": "每周训练天数"
            },
            "available_equipment": {
                "type": ParamType.LIST,
                "required": True,
                "description": "可用器械列表"
            },
            "injury_history": {
                "type": ParamType.LIST,
                "required": False,
                "description": "损伤历史",
                "default": None
            },
            "target_muscle_groups": {
                "type": ParamType.LIST,
                "required": False,
                "description": "目标肌群",
                "default": None
            },
            "periodization_model": {
                "type": ParamType.STRING,
                "required": False,
                "description": "周期化模型",
                "default": "linear"
            },
            "include_deload_weeks": {
                "type": ParamType.BOOLEAN,
                "required": False,
                "description": "是否包含减载周",
                "default": True
            },
            "auto_progression": {
                "type": ParamType.BOOLEAN,
                "required": False,
                "description": "是否自动进阶",
                "default": True
            }
        }
    },
    
    "training_split_designer": {
        "name": "training_split_designer",
        "description": "训练分化设计器 - 设计训练分化方案",
        "category": "training",
        "parameters": {
            "user_id": {
                "type": ParamType.STRING,
                "required": True,
                "description": "用户ID"
            },
            "training_level": {
                "type": ParamType.ENUM,
                "required": True,
                "description": "训练水平",
                "enum_values": ["beginner", "intermediate", "advanced"]
            },
            "primary_goal": {
                "type": ParamType.ENUM,
                "required": True,
                "description": "主要目标",
                "enum_values": ["strength", "hypertrophy", "endurance", "general_fitness", "fat_loss", "posture_correction", "functional"]
            },
            "training_days_per_week": {
                "type": ParamType.INTEGER,
                "required": True,
                "description": "每周训练天数"
            },
            "session_duration_minutes": {
                "type": ParamType.INTEGER,
                "required": True,
                "description": "单次训练时长（分钟）"
            },
            "available_equipment": {
                "type": ParamType.LIST,
                "required": True,
                "description": "可用器械列表"
            },
            "muscle_group_focus": {
                "type": ParamType.LIST,
                "required": False,
                "description": "重点肌群",
                "default": None
            },
            "injury_history": {
                "type": ParamType.LIST,
                "required": False,
                "description": "损伤历史",
                "default": None
            },
            "include_cardio": {
                "type": ParamType.BOOLEAN,
                "required": False,
                "description": "是否包含有氧",
                "default": True
            },
            "rest_day_preference": {
                "type": ParamType.STRING,
                "required": False,
                "description": "休息日偏好",
                "default": "spread_out"
            }
        }
    },
    
    "muscle_group_volume_calculator": {
        "name": "muscle_group_volume_calculator",
        "description": "肌群训练量计算器 - 计算最佳训练量",
        "category": "training",
        "parameters": {
            "user_id": {
                "type": ParamType.STRING,
                "required": True,
                "description": "用户ID，用于获取训练水平和恢复能力"
            },
            "muscle_group": {
                "type": ParamType.STRING,
                "required": True,
                "description": "目标肌群"
            },
            "training_goal": {
                "type": ParamType.ENUM,
                "required": True,
                "description": "训练目标",
                "enum_values": ["strength", "hypertrophy", "endurance", "general"]
            },
            "training_frequency_per_week": {
                "type": ParamType.INTEGER,
                "required": True,
                "description": "每周训练频率"
            },
            "current_weekly_sets": {
                "type": ParamType.INTEGER,
                "required": False,
                "description": "当前每周组数",
                "default": None
            },
            "recovery_capacity": {
                "type": ParamType.ENUM,
                "required": False,
                "description": "恢复能力",
                "enum_values": ["low", "moderate", "high"],
                "default": "moderate"
            }
        }
    },
    
    "movement_pattern_balancer": {
        "name": "movement_pattern_balancer",
        "description": "动作模式平衡器 - 平衡训练计划中的动作模式",
        "category": "training",
        "parameters": {
            "user_id": {
                "type": ParamType.STRING,
                "required": True,
                "description": "用户ID"
            },
            "current_program": {
                "type": ParamType.LIST,
                "required": True,
                "description": "当前训练计划中的动作列表"
            },
            "target_muscle_groups": {
                "type": ParamType.LIST,
                "required": True,
                "description": "目标肌群列表"
            }
        }
    },
    
    "intelligent_weight_calculator": {
        "name": "intelligent_weight_calculator",
        "description": "智能负重计算器 - 计算推荐训练重量",
        "category": "training",
        "parameters": {
            "user_id": {
                "type": ParamType.STRING,
                "required": True,
                "description": "用户ID"
            },
            "exercise_id": {
                "type": ParamType.STRING,
                "required": True,
                "description": "动作ID"
            },
            "training_goal": {
                "type": ParamType.ENUM,
                "required": False,
                "description": "训练目标",
                "enum_values": ["strength", "hypertrophy", "endurance"],
                "default": "hypertrophy"
            },
            "target_reps": {
                "type": ParamType.INTEGER,
                "required": False,
                "description": "目标次数",
                "default": None
            },
            "target_rir": {
                "type": ParamType.INTEGER,
                "required": False,
                "description": "目标RIR（储备次数）",
                "default": None
            },
            "one_rm": {
                "type": ParamType.FLOAT,
                "required": False,
                "description": "1RM重量",
                "default": None
            },
            "recent_performance": {
                "type": ParamType.DICT,
                "required": False,
                "description": "最近表现数据",
                "default": None
            }
        }
    },
    
    # =========================================================================
    # 营养相关工具
    # =========================================================================
    "tdee_calculator": {
        "name": "tdee_calculator",
        "description": "TDEE计算器 - 计算每日总能量消耗",
        "category": "nutrition",
        "parameters": {
            "user_id": {
                "type": ParamType.STRING,
                "required": True,
                "description": "用户ID，用于获取用户档案"
            },
            "training_frequency_per_week": {
                "type": ParamType.INTEGER,
                "required": True,
                "description": "每周训练频率"
            },
            "training_intensity": {
                "type": ParamType.ENUM,
                "required": True,
                "description": "训练强度",
                "enum_values": ["low", "moderate", "high", "very_high"]
            },
            "daily_activity_level": {
                "type": ParamType.ENUM,
                "required": True,
                "description": "日常活动水平",
                "enum_values": ["sedentary", "lightly_active", "moderately_active", "very_active", "extremely_active"]
            },
            "fitness_goal": {
                "type": ParamType.ENUM,
                "required": True,
                "description": "健身目标",
                "enum_values": ["weight_loss", "maintenance", "muscle_gain", "recomp"]
            },
            "age": {
                "type": ParamType.INTEGER,
                "required": False,
                "description": "年龄",
                "default": None
            },
            "gender": {
                "type": ParamType.STRING,
                "required": False,
                "description": "性别",
                "default": None
            },
            "weight_kg": {
                "type": ParamType.FLOAT,
                "required": False,
                "description": "体重（公斤）",
                "default": None
            },
            "height_cm": {
                "type": ParamType.FLOAT,
                "required": False,
                "description": "身高（厘米）",
                "default": None
            }
        }
    },
    
    "meal_plan_designer": {
        "name": "meal_plan_designer",
        "description": "膳食计划设计器 - 设计个性化膳食计划",
        "category": "nutrition",
        "parameters": {
            "user_id": {
                "type": ParamType.STRING,
                "required": True,
                "description": "用户ID"
            },
            "target_calories": {
                "type": ParamType.INTEGER,
                "required": True,
                "description": "目标卡路里"
            },
            "target_protein_grams": {
                "type": ParamType.FLOAT,
                "required": True,
                "description": "目标蛋白质（克）"
            },
            "target_carbs_grams": {
                "type": ParamType.FLOAT,
                "required": True,
                "description": "目标碳水化合物（克）"
            },
            "target_fat_grams": {
                "type": ParamType.FLOAT,
                "required": True,
                "description": "目标脂肪（克）"
            },
            "dietary_preference": {
                "type": ParamType.STRING,
                "required": False,
                "description": "饮食偏好",
                "default": "balanced"
            },
            "meals_per_day": {
                "type": ParamType.INTEGER,
                "required": False,
                "description": "每日餐数",
                "default": 4
            },
            "training_days_per_week": {
                "type": ParamType.INTEGER,
                "required": False,
                "description": "每周训练天数",
                "default": 3
            },
            "fitness_goal": {
                "type": ParamType.STRING,
                "required": False,
                "description": "健身目标",
                "default": "maintenance"
            }
        }
    },
    
    "nutrition_intake_analyzer": {
        "name": "nutrition_intake_analyzer",
        "description": "营养摄入分析器 - 分析每日营养摄入",
        "category": "nutrition",
        "parameters": {
            "user_id": {
                "type": ParamType.STRING,
                "required": True,
                "description": "用户ID"
            },
            "daily_food_intake": {
                "type": ParamType.LIST,
                "required": True,
                "description": "每日食物摄入列表"
            },
            "target_calories": {
                "type": ParamType.INTEGER,
                "required": False,
                "description": "目标卡路里",
                "default": None
            },
            "target_protein_grams": {
                "type": ParamType.FLOAT,
                "required": False,
                "description": "目标蛋白质（克）",
                "default": None
            },
            "target_carbs_grams": {
                "type": ParamType.FLOAT,
                "required": False,
                "description": "目标碳水化合物（克）",
                "default": None
            },
            "target_fat_grams": {
                "type": ParamType.FLOAT,
                "required": False,
                "description": "目标脂肪（克）",
                "default": None
            },
            "include_micronutrients": {
                "type": ParamType.BOOLEAN,
                "required": False,
                "description": "是否包含微量营养素分析",
                "default": False
            },
            "fitness_goal": {
                "type": ParamType.STRING,
                "required": False,
                "description": "健身目标",
                "default": "maintenance"
            }
        }
    },
    
    "exercise_nutrition_optimization": {
        "name": "exercise_nutrition_optimization",
        "description": "运动营养优化器 - 优化运动前后营养",
        "category": "nutrition",
        "parameters": {
            "user_id": {
                "type": ParamType.STRING,
                "required": True,
                "description": "用户ID"
            },
            "training_type": {
                "type": ParamType.ENUM,
                "required": True,
                "description": "训练类型",
                "enum_values": ["strength", "hypertrophy", "endurance", "hiit", "mixed"]
            },
            "training_duration_minutes": {
                "type": ParamType.INTEGER,
                "required": True,
                "description": "训练时长（分钟）"
            },
            "training_intensity": {
                "type": ParamType.ENUM,
                "required": True,
                "description": "训练强度",
                "enum_values": ["low", "moderate", "high", "very_high"]
            },
            "training_time": {
                "type": ParamType.STRING,
                "required": True,
                "description": "训练时间（如morning, afternoon, evening）"
            },
            "weight_kg": {
                "type": ParamType.FLOAT,
                "required": True,
                "description": "体重（公斤）"
            },
            "fitness_goal": {
                "type": ParamType.ENUM,
                "required": True,
                "description": "健身目标",
                "enum_values": ["weight_loss", "maintenance", "muscle_gain", "recomp"]
            },
            "daily_protein_target": {
                "type": ParamType.FLOAT,
                "required": True,
                "description": "每日蛋白质目标（克）"
            },
            "daily_carbs_target": {
                "type": ParamType.FLOAT,
                "required": True,
                "description": "每日碳水目标（克）"
            },
            "current_supplements": {
                "type": ParamType.LIST,
                "required": False,
                "description": "当前补剂列表",
                "default": None
            }
        }
    },
    
    # =========================================================================
    # 其他工具
    # =========================================================================
    "training_analytics_dashboard": {
        "name": "training_analytics_dashboard",
        "description": "训练分析仪表板 - 分析训练数据和进度",
        "category": "analytics",
        "parameters": {
            "user_id": {
                "type": ParamType.STRING,
                "required": True,
                "description": "用户ID"
            },
            "time_period": {
                "type": ParamType.STRING,
                "required": False,
                "description": "时间周期",
                "default": "month"
            },
            "focus_areas": {
                "type": ParamType.LIST,
                "required": False,
                "description": "关注领域",
                "default": None
            },
            "include_comparisons": {
                "type": ParamType.BOOLEAN,
                "required": False,
                "description": "是否包含对比",
                "default": True
            },
            "include_recommendations": {
                "type": ParamType.BOOLEAN,
                "required": False,
                "description": "是否包含建议",
                "default": True
            }
        }
    }
}


# =============================================================================
# Schema注册表类
# =============================================================================

class MCPToolSchemaRegistry:
    """
    MCP工具Schema注册表
    
    提供工具Schema的查询和验证功能。
    Requirements: 8.1, 8.5
    """
    
    def __init__(self):
        """初始化Schema注册表"""
        self.schemas = TOOL_SCHEMAS
        self.logger = logger
        self.logger.info(f"✅ MCPToolSchemaRegistry初始化完成，已注册 {len(self.schemas)} 个工具Schema")
    
    def get_schema(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """
        获取工具Schema
        
        Args:
            tool_name: 工具名称
            
        Returns:
            工具Schema字典，如果不存在返回None
        """
        schema = self.schemas.get(tool_name)
        if schema:
            self.logger.debug(f"📋 获取Schema: {tool_name}")
        else:
            self.logger.warning(f"⚠️ Schema不存在: {tool_name}")
        return schema
    
    def get_required_params(self, tool_name: str) -> List[str]:
        """
        获取工具的必需参数列表
        
        Args:
            tool_name: 工具名称
            
        Returns:
            必需参数名称列表
        """
        schema = self.get_schema(tool_name)
        if not schema:
            return []
        
        required_params = []
        parameters = schema.get("parameters", {})
        for param_name, param_config in parameters.items():
            if param_config.get("required", False):
                required_params.append(param_name)
        
        return required_params
    
    def get_optional_params(self, tool_name: str) -> List[str]:
        """
        获取工具的可选参数列表
        
        Args:
            tool_name: 工具名称
            
        Returns:
            可选参数名称列表
        """
        schema = self.get_schema(tool_name)
        if not schema:
            return []
        
        optional_params = []
        parameters = schema.get("parameters", {})
        for param_name, param_config in parameters.items():
            if not param_config.get("required", False):
                optional_params.append(param_name)
        
        return optional_params
    
    def get_param_type(self, tool_name: str, param_name: str) -> Optional[str]:
        """
        获取参数类型
        
        Args:
            tool_name: 工具名称
            param_name: 参数名称
            
        Returns:
            参数类型字符串，如果不存在返回None
        """
        schema = self.get_schema(tool_name)
        if not schema:
            return None
        
        parameters = schema.get("parameters", {})
        param_config = parameters.get(param_name)
        if not param_config:
            return None
        
        return param_config.get("type")
    
    def get_param_config(self, tool_name: str, param_name: str) -> Optional[Dict[str, Any]]:
        """
        获取参数完整配置
        
        Args:
            tool_name: 工具名称
            param_name: 参数名称
            
        Returns:
            参数配置字典，如果不存在返回None
        """
        schema = self.get_schema(tool_name)
        if not schema:
            return None
        
        parameters = schema.get("parameters", {})
        return parameters.get(param_name)
    
    def has_schema(self, tool_name: str) -> bool:
        """
        检查工具是否有Schema
        
        Args:
            tool_name: 工具名称
            
        Returns:
            是否存在Schema
        """
        return tool_name in self.schemas
    
    def get_all_tool_names(self) -> List[str]:
        """
        获取所有已注册的工具名称
        
        Returns:
            工具名称列表
        """
        return list(self.schemas.keys())
    
    def get_tools_by_category(self, category: str) -> List[str]:
        """
        按类别获取工具列表
        
        Args:
            category: 工具类别
            
        Returns:
            该类别下的工具名称列表
        """
        tools = []
        for tool_name, schema in self.schemas.items():
            if schema.get("category") == category:
                tools.append(tool_name)
        return tools
    
    def validate_params_against_schema(
        self,
        tool_name: str,
        params: Dict[str, Any]
    ) -> tuple[bool, List[str]]:
        """
        根据Schema验证参数
        
        Args:
            tool_name: 工具名称
            params: 参数字典
            
        Returns:
            (是否有效, 错误列表)
        """
        errors = []
        schema = self.get_schema(tool_name)
        
        if not schema:
            return True, []  # 没有Schema时跳过验证
        
        parameters = schema.get("parameters", {})
        
        # 检查必需参数
        for param_name, param_config in parameters.items():
            if param_config.get("required", False):
                if param_name not in params or params[param_name] is None:
                    errors.append(f"缺少必需参数: {param_name}")
        
        # 检查参数类型
        for param_name, param_value in params.items():
            if param_name in parameters and param_value is not None:
                param_config = parameters[param_name]
                expected_type = param_config.get("type")
                
                if not self._check_type(param_value, expected_type, param_config):
                    actual_type = type(param_value).__name__
                    errors.append(f"参数 '{param_name}' 类型不匹配: 期望 {expected_type}，实际 {actual_type}")
        
        return len(errors) == 0, errors
    
    def _check_type(self, value: Any, expected_type: str, param_config: Dict[str, Any]) -> bool:
        """检查值是否符合期望类型"""
        if value is None:
            return True
        
        type_checks = {
            ParamType.STRING: lambda v: isinstance(v, str),
            ParamType.INTEGER: lambda v: isinstance(v, int) and not isinstance(v, bool),
            ParamType.FLOAT: lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
            ParamType.BOOLEAN: lambda v: isinstance(v, bool),
            ParamType.LIST: lambda v: isinstance(v, list),
            ParamType.DICT: lambda v: isinstance(v, dict),
            ParamType.ENUM: lambda v: isinstance(v, str) and (
                "enum_values" not in param_config or v in param_config.get("enum_values", [])
            )
        }
        
        check_func = type_checks.get(expected_type)
        if check_func:
            return check_func(value)
        
        return True  # 未知类型默认通过


# 全局单例
_schema_registry_instance: Optional[MCPToolSchemaRegistry] = None


def get_schema_registry() -> MCPToolSchemaRegistry:
    """获取Schema注册表单例"""
    global _schema_registry_instance
    if _schema_registry_instance is None:
        _schema_registry_instance = MCPToolSchemaRegistry()
    return _schema_registry_instance
