# -*- coding: utf-8 -*-
"""
健身领域权威枚举定义 — 唯一来源

所有模块必须从此文件 import 枚举，禁止在其他文件中重复定义。
枚举值对齐 Neo4j 数据源：
  - TrainingGoal → Neo4j TrainingGoal 节点
  - DifficultyLevel → Neo4j TrainingLevel 节点
  - Exercise 属性: name_en/name_zh, difficulty_en/difficulty_zh, equipment_en/equipment_zh

@version 1.0.0
@created 2026-02-24
"""

from enum import Enum


class TrainingGoal(str, Enum):
    """
    训练目标枚举（权威定义）

    对齐 Neo4j TrainingGoal 节点 + 本地化扩展。
    注意：统一使用英文值，不做中英文映射。
    """
    # Neo4j TrainingGoal 节点已有
    HYPERTROPHY = "hypertrophy"                  # 增肌
    FAT_LOSS = "fat_loss"                        # 减脂
    STRENGTH = "strength"                        # 力量
    ENDURANCE = "endurance"                      # 耐力
    BODY_SHAPING = "body_shaping"                # 塑形

    # 本地化扩展目标
    GENERAL_FITNESS = "general_fitness"          # 综合健身
    POSTURE_CORRECTION = "posture_correction"    # 体态矫正
    FUNCTIONAL = "functional"                    # 功能性训练
    POWER = "power"                              # 爆发力
    PERFORMANCE = "performance"                  # 运动表现
    REHABILITATION = "rehabilitation"            # 康复


class DifficultyLevel(str, Enum):
    """
    难度等级枚举（权威定义）

    对齐 Neo4j TrainingLevel 节点。
    """
    NOVICE = "novice"              # 零基础
    BEGINNER = "beginner"          # 初级
    INTERMEDIATE = "intermediate"  # 中级
    ADVANCED = "advanced"          # 高级


class FitnessLevel(str, Enum):
    """
    用户训练水平枚举

    值与 DifficultyLevel 相同，语义上表示"用户当前水平"而非"动作难度"。
    """
    NOVICE = "novice"
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class NutritionGoal(str, Enum):
    """
    营养目标枚举

    部分值与 TrainingGoal 对齐，用于营养工具的目标参数。
    """
    MUSCLE_GAIN = "hypertrophy"    # 与 TrainingGoal.HYPERTROPHY 同值
    WEIGHT_LOSS = "fat_loss"       # 与 TrainingGoal.FAT_LOSS 同值
    MAINTENANCE = "maintenance"    # 维持体重
    RECOMP = "recomp"              # 重组（减脂增肌）


class MembershipTier(str, Enum):
    """
    会员等级枚举

    原 config/runtime.py 中的 UserLevel（会员等级），
    重命名避免与训练水平枚举冲突。
    """
    FREE = "free"
    PAID = "paid"
    VIP = "vip"
    SYSTEM = "system"
