# -*- coding: utf-8 -*-
"""
Weekly Plan Generator Service

分训练周期动态计划生成服务，实现分训练周期输出训练计划。
核心功能：
- 只输出第1训练周期完整计划
- 基于用户反馈生成下一训练周期计划
- 应用个性化容量系数
- 生成周期说明文案

Requirements: 10.1, 10.2, 10.3, 10.4 - 分训练周期动态生成

作者: BUILD_BODY Team
版本: 1.0.0
日期: 2025-12-26
"""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class PeriodizationPhase(str, Enum):
    """周期化阶段"""
    ACCUMULATION = "accumulation"  # 积累期（第1-2训练周期）
    INTENSIFICATION = "intensification"  # 冲刺期（第3训练周期）
    DELOAD = "deload"  # 减量期（第4训练周期）


@dataclass
class WeeklyPlanMetadata:
    """训练周期计划元数据"""
    week_number: int
    total_weeks: int
    phase: PeriodizationPhase
    phase_name_zh: str
    phase_description: str
    volume_multiplier: float
    is_first_week: bool
    is_deload_week: bool
    generated_at: str


@dataclass
class WeeklyPlanExercise:
    """训练周期计划中的动作"""
    exercise_id: str
    name_zh: str
    name_en: str
    sets: int
    reps_range: tuple
    rest_seconds: int
    weight_suggestion: Optional[str] = None
    safety_marker: bool = False
    safety_notes: List[str] = field(default_factory=list)
    primary_muscles: List[str] = field(default_factory=list)


@dataclass
class WeeklyPlanDay:
    """训练周期计划中的训练日"""
    day_number: int
    day_name: str
    focus_muscle_groups: List[str]
    exercises: List[WeeklyPlanExercise]
    total_sets: int
    estimated_duration_minutes: int
    notes: List[str] = field(default_factory=list)
    is_deload_day: bool = False


@dataclass
class WeeklyPlan:
    """训练周期计划"""
    metadata: WeeklyPlanMetadata
    training_days: List[WeeklyPlanDay]
    rest_days: List[int]
    total_weekly_sets: int
    cycle_explanation: str
    next_week_preview: Optional[str] = None


class WeeklyPlanGenerator:
    """
    分训练周期动态计划生成服务

    核心功能：
    - generate_first_week: 生成第1训练周期计划
    - generate_next_week: 基于反馈生成下一训练周期计划
    - apply_volume_multiplier: 应用个性化容量系数
    - insert_deload_week: 生成Deload训练周期计划
    - apply_progressive_overload: 应用渐进过载计算

    Requirements: 10.1, 10.2, 10.3, 10.4 - 分训练周期动态生成
    Requirements: 8.1, 8.2, 8.3, 8.4 - 渐进过载自动化
    """
    
    # 周期化阶段配置
    PHASE_CONFIG = {
        1: {
            "phase": PeriodizationPhase.ACCUMULATION,
            "name_zh": "积累期",
            "description": "使用最大适应训练量（MAV），诱导肌肥大适应",
            "volume_factor": 1.0  # 使用MAV
        },
        2: {
            "phase": PeriodizationPhase.ACCUMULATION,
            "name_zh": "积累期",
            "description": "继续使用最大适应训练量（MAV），巩固训练适应",
            "volume_factor": 1.0  # 使用MAV
        },
        3: {
            "phase": PeriodizationPhase.INTENSIFICATION,
            "name_zh": "冲刺期",
            "description": "使用最大可恢复训练量（MRV），达到训练峰值",
            "volume_factor": 1.2  # 使用MRV（增加20%）
        },
        4: {
            "phase": PeriodizationPhase.DELOAD,
            "name_zh": "减量期",
            "description": "使用最小有效训练量（MEV），促进超量恢复",
            "volume_factor": 0.6  # 使用MEV（减少40%）
        }
    }
    
    # 周期说明文案模板
    # 术语规范：
    # - "训练周期" = 训练计划中的周期单位（如第1训练周期、第2训练周期）
    # - "星期" = 日历上的星期几（如星期一、星期二）
    CYCLE_EXPLANATION_TEMPLATES = {
        "first_week": """📅 这是{total_weeks}个训练周期计划的第1训练周期

🎯 **本训练周期阶段**：{phase_name}
📝 **阶段说明**：{phase_description}

💡 **周期化训练说明**：
- 第1-2训练周期（积累期）：建立训练基础，使用最大适应训练量
- 第3训练周期（冲刺期）：达到训练峰值，使用最大可恢复训练量
- 第4训练周期（减量期）：促进恢复，使用最小有效训练量

📊 后续每个训练周期根据您的完成反馈自动调整并推送下一训练周期计划。""",
        
        "subsequent_week": """📅 这是{total_weeks}个训练周期计划的第{week_number}训练周期

🎯 **本训练周期阶段**：{phase_name}
📝 **阶段说明**：{phase_description}

📊 **上一训练周期反馈分析**：
- 完成率：{completion_rate:.0%}
- 平均RPE：{avg_rpe:.1f}
- 调整建议：{adjustment_note}

{next_week_preview}""",
        
        "deload_week": """📅 这是{total_weeks}个训练周期计划的第{week_number}训练周期（减量训练周期）

🔄 **减量训练周期说明**：
本训练周期为减量恢复期，训练量降至正常的60%，强度保持在80%。

💡 **减量训练周期目的**：
- 促进中枢神经系统恢复
- 消除累积疲劳
- 为下一周期做准备

⚠️ **重要提醒**：
- 不要跳过减量训练周期
- 不要增加训练量
- 专注于动作质量和肌肉感受"""
    }
    
    def __init__(
        self,
        training_log_analyzer=None,
        backend_client=None,
        user_profile_integrator=None,
        progressive_overload_calculator=None
    ):
        """
        初始化分训练周期计划生成器
        
        Args:
            training_log_analyzer: 训练日志分析器（可选）
            backend_client: 后端客户端（可选）
            user_profile_integrator: 用户档案整合器（可选）
            progressive_overload_calculator: 渐进过载计算器（可选）
        """
        self.training_log_analyzer = training_log_analyzer
        self.backend_client = backend_client
        self.user_profile_integrator = user_profile_integrator
        self.progressive_overload_calculator = progressive_overload_calculator
        logger.info("WeeklyPlanGenerator initialized")
    
    def _get_volume_multiplier(self, user_profile: Optional[Dict[str, Any]]) -> float:
        """
        从用户档案获取容量系数（支持新旧格式）
        
        Args:
            user_profile: 用户档案
            
        Returns:
            float: 容量系数（0.7-1.5）
        """
        if not user_profile:
            return 1.0
        
        # 优先从training_system获取（新格式）
        training_system = user_profile.get('training_system', {})
        if training_system and 'personal_volume_multiplier' in training_system:
            multiplier = training_system.get('personal_volume_multiplier', 1.0)
        else:
            # 降级到旧格式
            multiplier = user_profile.get('personal_volume_multiplier', 1.0)
        
        # 边界检查
        return max(0.7, min(1.5, float(multiplier)))
    
    def generate_first_week(
        self,
        full_program: Dict[str, Any],
        user_profile: Optional[Dict[str, Any]] = None,
        total_weeks: int = 4
    ) -> WeeklyPlan:
        """
        生成第1训练周期计划

        从完整的多训练周期计划中提取第1训练周期，并添加周期说明文案。

        Args:
            full_program: 完整的训练计划（来自professional_program_designer）
            user_profile: 用户档案（可选）
            total_weeks: 总训练周期数，默认4个训练周期

        Returns:
            WeeklyPlan: 第1训练周期计划

        Requirements: 10.1 - 只输出第1训练周期完整计划
        """
        logger.info(f"生成第1训练周期计划: total_weeks={total_weeks}")

        # 获取第1训练周期的阶段配置
        phase_config = self.PHASE_CONFIG[1]
        
        # 获取个性化容量系数（使用辅助方法）
        volume_multiplier = self._get_volume_multiplier(user_profile)
        
        # 创建元数据
        metadata = WeeklyPlanMetadata(
            week_number=1,
            total_weeks=total_weeks,
            phase=phase_config["phase"],
            phase_name_zh=phase_config["name_zh"],
            phase_description=phase_config["description"],
            volume_multiplier=volume_multiplier,
            is_first_week=True,
            is_deload_week=False,
            generated_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )
        
        # 提取第1训练周期的训练日
        training_days = self._extract_week_training_days(
            full_program,
            week_number=1,
            volume_multiplier=volume_multiplier
        )
        
        # 计算休息日
        training_day_numbers = [day.day_number for day in training_days]
        rest_days = [i for i in range(1, 8) if i not in training_day_numbers]
        
        # 计算总训练量
        total_weekly_sets = sum(day.total_sets for day in training_days)
        
        # 生成周期说明文案
        cycle_explanation = self._generate_cycle_explanation(
            week_number=1,
            total_weeks=total_weeks,
            phase_name=phase_config["name_zh"],
            phase_description=phase_config["description"],
            is_first_week=True
        )
        
        # 生成下一训练周期预览
        next_week_preview = self._generate_next_week_preview(
            current_week=1,
            total_weeks=total_weeks
        )
        
        weekly_plan = WeeklyPlan(
            metadata=metadata,
            training_days=training_days,
            rest_days=rest_days,
            total_weekly_sets=total_weekly_sets,
            cycle_explanation=cycle_explanation,
            next_week_preview=next_week_preview
        )
        
        logger.info(
            f"第1训练周期计划生成完成: "
            f"training_days={len(training_days)}, "
            f"total_sets={total_weekly_sets}, "
            f"phase={phase_config['name_zh']}"
        )
        
        return weekly_plan
    
    async def generate_next_week(
        self,
        user_id: int,
        current_week: int,
        total_weeks: int,
        last_week_feedback: Dict[str, Any],
        base_program: Dict[str, Any],
        user_profile: Optional[Dict[str, Any]] = None
    ) -> WeeklyPlan:
        """
        基于反馈生成下一训练周期计划

        分析上一训练周期的训练反馈，动态调整下一训练周期计划。

        Args:
            user_id: 用户ID
            current_week: 当前训练周期数（即将生成的训练周期）
            total_weeks: 总训练周期数
            last_week_feedback: 上一训练周期训练反馈
            base_program: 基础训练计划
            user_profile: 用户档案（可选）

        Returns:
            WeeklyPlan: 下一训练周期训练计划

        Requirements: 10.3, 10.4 - 基于反馈动态调整
        """
        logger.info(
            f"生成第{current_week}训练周期计划: "
            f"user_id={user_id}, total_weeks={total_weeks}"
        )
        
        # 获取当前周的阶段配置（循环使用4周周期）
        cycle_week = ((current_week - 1) % 4) + 1
        phase_config = self.PHASE_CONFIG[cycle_week]
        
        # 分析上一训练周期反馈
        completion_rate = last_week_feedback.get('completion_rate', 0.0)
        avg_rpe = last_week_feedback.get('avg_rpe', 7.0)
        
        # 计算容量调整
        volume_adjustment = self._calculate_volume_adjustment(
            completion_rate=completion_rate,
            avg_rpe=avg_rpe
        )
        
        # 获取个性化容量系数（使用辅助方法）
        base_multiplier = self._get_volume_multiplier(user_profile)
        
        # 应用阶段容量因子和调整
        volume_multiplier = base_multiplier * phase_config["volume_factor"]
        volume_multiplier = max(0.7, min(1.5, volume_multiplier + volume_adjustment))
        
        # 检查是否需要强制Deload
        force_deload = self._should_force_deload(
            completion_rate=completion_rate,
            avg_rpe=avg_rpe,
            last_week_feedback=last_week_feedback
        )
        
        is_deload_week = phase_config["phase"] == PeriodizationPhase.DELOAD or force_deload
        
        # 创建元数据
        metadata = WeeklyPlanMetadata(
            week_number=current_week,
            total_weeks=total_weeks,
            phase=PeriodizationPhase.DELOAD if force_deload else phase_config["phase"],
            phase_name_zh="减量期（强制）" if force_deload else phase_config["name_zh"],
            phase_description="检测到疲劳累积，建议进入减量恢复" if force_deload else phase_config["description"],
            volume_multiplier=volume_multiplier,
            is_first_week=False,
            is_deload_week=is_deload_week,
            generated_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )
        
        # 提取训练日并应用调整
        training_days = self._extract_week_training_days(
            base_program,
            week_number=current_week,
            volume_multiplier=volume_multiplier,
            is_deload=is_deload_week
        )
        
        # 计算休息日
        training_day_numbers = [day.day_number for day in training_days]
        rest_days = [i for i in range(1, 8) if i not in training_day_numbers]
        
        # 计算总训练量
        total_weekly_sets = sum(day.total_sets for day in training_days)
        
        # 生成调整说明
        adjustment_note = self._generate_adjustment_note(
            completion_rate=completion_rate,
            avg_rpe=avg_rpe,
            volume_adjustment=volume_adjustment,
            force_deload=force_deload
        )
        
        # 生成周期说明文案
        cycle_explanation = self._generate_cycle_explanation(
            week_number=current_week,
            total_weeks=total_weeks,
            phase_name=metadata.phase_name_zh,
            phase_description=metadata.phase_description,
            is_first_week=False,
            completion_rate=completion_rate,
            avg_rpe=avg_rpe,
            adjustment_note=adjustment_note,
            is_deload=is_deload_week
        )
        
        # 生成下一训练周期预览
        next_week_preview = self._generate_next_week_preview(
            current_week=current_week,
            total_weeks=total_weeks
        )
        
        weekly_plan = WeeklyPlan(
            metadata=metadata,
            training_days=training_days,
            rest_days=rest_days,
            total_weekly_sets=total_weekly_sets,
            cycle_explanation=cycle_explanation,
            next_week_preview=next_week_preview
        )
        
        logger.info(
            f"第{current_week}训练周期计划生成完成: "
            f"training_days={len(training_days)}, "
            f"total_sets={total_weekly_sets}, "
            f"phase={metadata.phase_name_zh}, "
            f"volume_multiplier={volume_multiplier:.2f}"
        )
        
        return weekly_plan

    
    def apply_volume_multiplier(
        self,
        base_plan: Dict[str, Any],
        multiplier: float
    ) -> Dict[str, Any]:
        """
        应用个性化容量系数
        
        Args:
            base_plan: 基础训练计划
            multiplier: 容量系数（0.7-1.5）
            
        Returns:
            Dict: 调整后的训练计划
        """
        # 确保系数在有效范围内
        multiplier = max(0.7, min(1.5, multiplier))
        
        adjusted_plan = base_plan.copy()
        
        # 调整每个训练日的组数
        if "training_days" in adjusted_plan:
            for day in adjusted_plan["training_days"]:
                if "exercises" in day:
                    for exercise in day["exercises"]:
                        original_sets = exercise.get("sets", 3)
                        adjusted_sets = max(1, int(original_sets * multiplier))
                        exercise["sets"] = adjusted_sets
                
                # 重新计算总组数
                day["total_sets"] = sum(
                    ex.get("sets", 0) for ex in day.get("exercises", [])
                )
        
        # 更新总训练量
        if "training_days" in adjusted_plan:
            adjusted_plan["total_weekly_sets"] = sum(
                day.get("total_sets", 0) for day in adjusted_plan["training_days"]
            )
        
        logger.info(f"应用容量系数: multiplier={multiplier:.2f}")
        
        return adjusted_plan
    
    def insert_deload_week(
        self,
        base_program: Dict[str, Any],
        week_number: int,
        total_weeks: int,
        user_profile: Optional[Dict[str, Any]] = None
    ) -> WeeklyPlan:
        """
        生成Deload训练周期计划

        Args:
            base_program: 基础训练计划
            week_number: 训练周期数
            total_weeks: 总训练周期数
            user_profile: 用户档案（可选）

        Returns:
            WeeklyPlan: Deload训练周期计划
        """
        logger.info(f"生成Deload训练周期计划: week_number={week_number}")

        # Deload训练周期配置
        phase_config = self.PHASE_CONFIG[4]  # 使用第4训练周期（减量期）配置
        
        # 获取基础容量系数（使用辅助方法）
        base_multiplier = self._get_volume_multiplier(user_profile)
        
        # Deload训练周期容量系数（60%）
        volume_multiplier = base_multiplier * 0.6
        
        # 创建元数据
        metadata = WeeklyPlanMetadata(
            week_number=week_number,
            total_weeks=total_weeks,
            phase=PeriodizationPhase.DELOAD,
            phase_name_zh="减量期",
            phase_description="使用最小有效训练量（MEV），促进超量恢复",
            volume_multiplier=volume_multiplier,
            is_first_week=False,
            is_deload_week=True,
            generated_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )
        
        # 提取训练日并应用Deload调整
        training_days = self._extract_week_training_days(
            base_program,
            week_number=week_number,
            volume_multiplier=volume_multiplier,
            is_deload=True
        )
        
        # 计算休息日
        training_day_numbers = [day.day_number for day in training_days]
        rest_days = [i for i in range(1, 8) if i not in training_day_numbers]
        
        # 计算总训练量
        total_weekly_sets = sum(day.total_sets for day in training_days)
        
        # 生成Deload训练周期说明
        cycle_explanation = self.CYCLE_EXPLANATION_TEMPLATES["deload_week"].format(
            total_weeks=total_weeks,
            week_number=week_number
        )
        
        weekly_plan = WeeklyPlan(
            metadata=metadata,
            training_days=training_days,
            rest_days=rest_days,
            total_weekly_sets=total_weekly_sets,
            cycle_explanation=cycle_explanation,
            next_week_preview=None
        )
        
        logger.info(
            f"Deload训练周期计划生成完成: "
            f"training_days={len(training_days)}, "
            f"total_sets={total_weekly_sets}"
        )
        
        return weekly_plan
    
    def _extract_week_training_days(
        self,
        full_program: Dict[str, Any],
        week_number: int,
        volume_multiplier: float = 1.0,
        is_deload: bool = False
    ) -> List[WeeklyPlanDay]:
        """
        从完整计划中提取指定训练周期的训练日

        Args:
            full_program: 完整训练计划
            week_number: 训练周期数
            volume_multiplier: 容量系数
            is_deload: 是否为Deload训练周期

        Returns:
            List[WeeklyPlanDay]: 训练日列表
        """
        training_days = []

        # 尝试从weekly_programs中获取指定训练周期
        weekly_programs = full_program.get("weekly_programs", [])
        weekly_program = full_program.get("weekly_program", {})
        
        # 如果有多训练周期计划，获取指定训练周期
        if weekly_programs and len(weekly_programs) >= week_number:
            source_program = weekly_programs[week_number - 1]
        else:
            # 否则使用第一个训练周期作为模板
            source_program = weekly_program if weekly_program else full_program
        
        source_days = source_program.get("training_days", [])
        
        for day_data in source_days:
            exercises = []
            total_sets = 0
            
            for ex_data in day_data.get("exercises", []):
                # 计算调整后的组数
                original_sets = ex_data.get("sets", 3)
                adjusted_sets = max(1, int(original_sets * volume_multiplier))
                
                # 如果是Deload训练周期，进一步减少组数
                if is_deload:
                    adjusted_sets = max(1, adjusted_sets // 2)
                
                exercise = WeeklyPlanExercise(
                    exercise_id=ex_data.get("exercise_id", ""),
                    name_zh=ex_data.get("name_zh", ""),
                    name_en=ex_data.get("name_en", ""),
                    sets=adjusted_sets,
                    reps_range=ex_data.get("reps_range", (8, 12)),
                    rest_seconds=ex_data.get("rest_seconds", 90),
                    weight_suggestion=ex_data.get("weight_suggestion"),
                    safety_marker=ex_data.get("safety_level", "") in ["HIGH", "CRITICAL"],
                    safety_notes=ex_data.get("safety_notes", []),
                    primary_muscles=ex_data.get("primary_muscles", [])
                )
                
                exercises.append(exercise)
                total_sets += adjusted_sets
            
            # 估算训练时长
            estimated_duration = self._estimate_duration(exercises, is_deload)
            
            # 生成训练日备注
            notes = day_data.get("notes", [])
            if is_deload:
                notes = [
                    "🔄 减量日：训练量减半，强度80%",
                    "💡 专注于动作质量和肌肉感受",
                    "⚠️ 不要追求极限重量"
                ]
            
            training_day = WeeklyPlanDay(
                day_number=day_data.get("day_number", 1),
                day_name=day_data.get("day_name", "训练日"),
                focus_muscle_groups=day_data.get("focus_muscle_groups", []),
                exercises=exercises,
                total_sets=total_sets,
                estimated_duration_minutes=estimated_duration,
                notes=notes,
                is_deload_day=is_deload
            )
            
            training_days.append(training_day)
        
        return training_days
    
    def _estimate_duration(
        self,
        exercises: List[WeeklyPlanExercise],
        is_deload: bool = False
    ) -> int:
        """估算训练时长（分钟）"""
        total_minutes = 10  # 热身时间
        
        for ex in exercises:
            # 每组约30秒 + 休息时间
            exercise_time = ex.sets * (30 + ex.rest_seconds) / 60
            total_minutes += exercise_time
        
        total_minutes += 10  # 放松时间
        
        # Deload训练周期时间减半
        if is_deload:
            total_minutes = max(30, total_minutes * 0.6)
        
        return int(total_minutes)
    
    def _calculate_volume_adjustment(
        self,
        completion_rate: float,
        avg_rpe: float
    ) -> float:
        """
        计算容量调整值
        
        Requirements: 7.2, 7.3 - 根据RPE和完成率计算容量调整
        
        调整规则：
        - RPE < 7 且 完成率 > 95%: +0.05 ~ +0.1
        - RPE > 9.5 或 完成率 < 80%: -0.1 ~ -0.15
        - 其他情况: 保持不变或微调
        """
        adjustment = 0.0
        
        # 规则1: RPE < 7 且 完成率 > 95% -> 上调容量
        if avg_rpe < 7.0 and completion_rate > 0.95:
            rpe_factor = (7.0 - avg_rpe) / 7.0
            completion_factor = (completion_rate - 0.95) / 0.05
            adjustment = 0.05 + 0.05 * min(rpe_factor, completion_factor)
            adjustment = min(adjustment, 0.1)
            
        # 规则2: RPE > 9.5 或 完成率 < 80% -> 下调容量
        elif avg_rpe > 9.5 or completion_rate < 0.80:
            if avg_rpe > 9.5:
                rpe_factor = (avg_rpe - 9.5) / 0.5
                adjustment = -0.1 - 0.05 * min(rpe_factor, 1.0)
            if completion_rate < 0.80:
                completion_factor = (0.80 - completion_rate) / 0.20
                completion_adj = -0.1 - 0.05 * min(completion_factor, 1.0)
                adjustment = min(adjustment, completion_adj)
            adjustment = max(adjustment, -0.15)
        
        return round(adjustment, 2)
    
    def _should_force_deload(
        self,
        completion_rate: float,
        avg_rpe: float,
        last_week_feedback: Dict[str, Any]
    ) -> bool:
        """
        判断是否需要强制Deload
        
        Requirements: 9.2 - 连续2个训练周期RPE>9或完成率<85%时提示Deload
        """
        # 检查当前训练周期指标
        current_week_needs_deload = avg_rpe > 9.0 or completion_rate < 0.85

        # 检查是否连续两个训练周期
        previous_week_rpe = last_week_feedback.get('previous_avg_rpe', 7.0)
        previous_week_completion = last_week_feedback.get('previous_completion_rate', 0.9)
        previous_week_needs_deload = previous_week_rpe > 9.0 or previous_week_completion < 0.85

        # 连续两个训练周期需要Deload
        if current_week_needs_deload and previous_week_needs_deload:
            logger.warning(
                f"检测到连续两个训练周期疲劳累积: "
                f"current_rpe={avg_rpe:.1f}, current_completion={completion_rate:.0%}, "
                f"previous_rpe={previous_week_rpe:.1f}, previous_completion={previous_week_completion:.0%}"
            )
            return True

        # 单个训练周期极端情况
        if avg_rpe > 9.5 and completion_rate < 0.80:
            logger.warning(
                f"检测到单个训练周期极端疲劳: "
                f"rpe={avg_rpe:.1f}, completion={completion_rate:.0%}"
            )
            return True
        
        return False
    
    def _generate_cycle_explanation(
        self,
        week_number: int,
        total_weeks: int,
        phase_name: str,
        phase_description: str,
        is_first_week: bool = False,
        completion_rate: float = 0.0,
        avg_rpe: float = 0.0,
        adjustment_note: str = "",
        is_deload: bool = False
    ) -> str:
        """
        生成周期说明文案
        
        Requirements: 10.2 - 附上周期说明文案
        """
        if is_deload:
            return self.CYCLE_EXPLANATION_TEMPLATES["deload_week"].format(
                total_weeks=total_weeks,
                week_number=week_number
            )
        
        if is_first_week:
            return self.CYCLE_EXPLANATION_TEMPLATES["first_week"].format(
                total_weeks=total_weeks,
                phase_name=phase_name,
                phase_description=phase_description
            )
        
        next_week_preview = self._generate_next_week_preview(week_number, total_weeks)
        
        return self.CYCLE_EXPLANATION_TEMPLATES["subsequent_week"].format(
            total_weeks=total_weeks,
            week_number=week_number,
            phase_name=phase_name,
            phase_description=phase_description,
            completion_rate=completion_rate,
            avg_rpe=avg_rpe,
            adjustment_note=adjustment_note,
            next_week_preview=next_week_preview
        )
    
    def _generate_next_week_preview(
        self,
        current_week: int,
        total_weeks: int
    ) -> str:
        """生成下一训练周期预览"""
        if current_week >= total_weeks:
            return "🎉 恭喜完成本训练计划！建议休息1-2天后开始新周期。"
        
        next_week = current_week + 1
        next_cycle_week = ((next_week - 1) % 4) + 1
        next_phase_config = self.PHASE_CONFIG[next_cycle_week]
        
        return f"📅 下一训练周期预览：第{next_week}训练周期（{next_phase_config['name_zh']}）"
    
    def _generate_adjustment_note(
        self,
        completion_rate: float,
        avg_rpe: float,
        volume_adjustment: float,
        force_deload: bool
    ) -> str:
        """生成调整说明"""
        if force_deload:
            return "⚠️ 检测到疲劳累积，本训练周期进入强制减量恢复"
        
        if volume_adjustment > 0:
            return f"✅ 上一训练周期表现优秀，本训练周期训练量上调{volume_adjustment*100:.0f}%"
        elif volume_adjustment < 0:
            return f"📉 上一训练周期训练强度较大，本训练周期训练量下调{abs(volume_adjustment)*100:.0f}%"
        else:
            return "➡️ 保持当前训练量"
    
    def convert_to_output_format(
        self,
        weekly_plan: WeeklyPlan
    ) -> Dict[str, Any]:
        """
        将WeeklyPlan转换为输出格式
        
        Args:
            weekly_plan: 训练周期计划
            
        Returns:
            Dict: 输出格式的训练计划
        """
        training_days_output = []
        
        for day in weekly_plan.training_days:
            exercises_output = []
            for ex in day.exercises:
                exercise_output = {
                    "exercise_id": ex.exercise_id,
                    "name_zh": ex.name_zh,
                    "name_en": ex.name_en,
                    "sets": ex.sets,
                    "reps_range": ex.reps_range,
                    "rest_seconds": ex.rest_seconds,
                    "weight_suggestion": ex.weight_suggestion,
                    "primary_muscles": ex.primary_muscles
                }
                
                # 添加安全标记
                if ex.safety_marker:
                    exercise_output["safety_marker"] = "⚠️"
                    exercise_output["safety_notes"] = ex.safety_notes
                
                exercises_output.append(exercise_output)
            
            day_output = {
                "day_number": day.day_number,
                "day_name": day.day_name,
                "focus_muscle_groups": day.focus_muscle_groups,
                "exercises": exercises_output,
                "total_sets": day.total_sets,
                "estimated_duration_minutes": day.estimated_duration_minutes,
                "notes": day.notes
            }
            
            if day.is_deload_day:
                day_output["is_deload_day"] = True
            
            training_days_output.append(day_output)
        
        return {
            "week_number": weekly_plan.metadata.week_number,
            "total_weeks": weekly_plan.metadata.total_weeks,
            "phase": weekly_plan.metadata.phase_name_zh,
            "phase_description": weekly_plan.metadata.phase_description,
            "volume_multiplier": weekly_plan.metadata.volume_multiplier,
            "is_deload_week": weekly_plan.metadata.is_deload_week,
            "training_days": training_days_output,
            "rest_days": weekly_plan.rest_days,
            "total_weekly_sets": weekly_plan.total_weekly_sets,
            "cycle_explanation": weekly_plan.cycle_explanation,
            "next_week_preview": weekly_plan.next_week_preview,
            "generated_at": weekly_plan.metadata.generated_at
        }

    
    async def apply_progressive_overload(
        self,
        weekly_plan: WeeklyPlan,
        user_id: int,
        last_week_weights: Dict[str, float],
        last_week_completion: Dict[str, bool],
        user_profile: Optional[Dict[str, Any]] = None
    ) -> WeeklyPlan:
        """
        应用渐进过载计算到训练周期计划

        为每个动作计算下一训练周期建议重量，并添加重量变化标注。

        Args:
            weekly_plan: 训练周期计划
            user_id: 用户ID
            last_week_weights: 上一训练周期各动作使用的重量 {exercise_id: weight}
            last_week_completion: 上一训练周期各动作是否完成所有目标次数 {exercise_id: bool}
            user_profile: 用户档案（可选）

        Returns:
            WeeklyPlan: 应用渐进过载后的训练周期计划

        Requirements: 8.1, 8.2, 8.3, 8.4 - 渐进过载自动化
        """
        if not self.progressive_overload_calculator:
            logger.warning("渐进过载计算器未初始化，跳过渐进过载计算")
            return weekly_plan
        
        # 获取用户容量系数
        volume_multiplier = self._get_volume_multiplier(user_profile)
        
        # 收集所有需要提醒购买小片的动作
        micro_plate_suggestions = []
        
        # 遍历所有训练日和动作
        for day in weekly_plan.training_days:
            for exercise in day.exercises:
                exercise_id = exercise.exercise_id
                
                # 获取上一训练周期数据
                last_weight = last_week_weights.get(exercise_id, 0.0)
                completed_all_reps = last_week_completion.get(exercise_id, True)
                
                if last_weight <= 0:
                    # 没有上一训练周期数据，跳过
                    continue
                
                # 计算渐进过载
                result = self.progressive_overload_calculator.calculate_overload(
                    exercise_id=exercise_id,
                    exercise_name=exercise.name_zh or exercise.name_en,
                    last_weight=last_weight,
                    completed_all_reps=completed_all_reps,
                    muscle_group=exercise.primary_muscles[0] if exercise.primary_muscles else "",
                    current_weekly_sets=exercise.sets,
                    user_volume_multiplier=volume_multiplier
                )
                
                # 更新重量建议
                if result.next_weight > 0:
                    exercise.weight_suggestion = f"{result.next_weight}kg ({result.annotation})"
                
                # 收集小片建议
                if result.micro_plate_suggestion:
                    micro_plate_suggestions.append({
                        'exercise': exercise.name_zh or exercise.name_en,
                        'message': result.micro_plate_message
                    })
                
                # 如果检测到退步，添加到备注
                if result.regression_detected:
                    day.notes.append(result.regression_message)
                
                # 如果接近MAV，添加警告
                if result.mav_warning:
                    day.notes.append(result.mav_message)
        
        # 如果有小片建议，添加到训练周期计划说明中
        if micro_plate_suggestions:
            micro_plate_note = "\n\n💡 **小片购买建议**：\n"
            micro_plate_note += "以下孤立动作建议使用1.25kg小片实现更精细的渐进过载：\n"
            for suggestion in micro_plate_suggestions[:3]:  # 最多显示3个
                micro_plate_note += f"- {suggestion['exercise']}\n"
            micro_plate_note += "\n1.25kg小片约20-30元/对，可在淘宝/京东购买。"
            
            weekly_plan.cycle_explanation += micro_plate_note
        
        logger.info(
            f"渐进过载计算完成: user_id={user_id}, "
            f"exercises_processed={sum(len(day.exercises) for day in weekly_plan.training_days)}"
        )
        
        return weekly_plan
    
    def generate_weight_annotations(
        self,
        exercises: List[Dict[str, Any]],
        last_week_weights: Dict[str, float]
    ) -> Dict[str, str]:
        """
        为动作列表生成重量变化标注
        
        Args:
            exercises: 动作列表
            last_week_weights: 上一训练周期各动作使用的重量
            
        Returns:
            Dict[str, str]: {exercise_id: annotation}
            
        Requirements: 8.4 - 在动作旁标注重量变化
        """
        annotations = {}
        
        if not self.progressive_overload_calculator:
            return annotations
        
        for exercise in exercises:
            exercise_id = exercise.get('exercise_id', '')
            next_weight = exercise.get('weight_suggestion', 0.0)
            last_weight = last_week_weights.get(exercise_id, 0.0)
            
            if last_weight > 0 and next_weight > 0:
                annotation = self.progressive_overload_calculator.get_weight_annotation(
                    last_weight=last_weight,
                    next_weight=next_weight
                )
                annotations[exercise_id] = annotation
        
        return annotations
