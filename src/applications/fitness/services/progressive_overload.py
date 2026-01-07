# -*- coding: utf-8 -*-
"""
Progressive Overload Calculator Service

渐进过载自动计算服务，实现科学的重量递增策略。
核心功能：
- 计算下周建议重量
- 检测重量退步
- 提醒用户购买1.25kg小片（用于孤立动作）
- 检查是否接近用户MAV（最大适应训练量）

Requirements: 8.1, 8.2, 8.3, 8.4 - 渐进过载自动化

作者: BUILD_BODY Team
版本: 1.0.0
日期: 2025-12-26
"""

import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class ExerciseType(str, Enum):
    """动作类型"""
    COMPOUND = "compound"      # 复合动作：深蹲、卧推、硬拉
    ISOLATION = "isolation"    # 孤立动作：弯举、飞鸟、侧平举


class OverloadDecision(str, Enum):
    """过载决策"""
    INCREASE = "increase"      # 增加重量
    MAINTAIN = "maintain"      # 保持重量
    DECREASE = "decrease"      # 降低重量
    TECHNIQUE_CHECK = "technique_check"  # 技术排查


@dataclass
class OverloadResult:
    """渐进过载计算结果"""
    exercise_id: str
    exercise_name: str
    exercise_type: ExerciseType
    last_weight: float
    next_weight: float
    weight_change: float
    decision: OverloadDecision
    annotation: str
    reason: str
    micro_plate_suggestion: bool = False
    micro_plate_message: Optional[str] = None
    regression_detected: bool = False
    regression_message: Optional[str] = None
    mav_warning: bool = False
    mav_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {
            'exercise_id': self.exercise_id,
            'exercise_name': self.exercise_name,
            'exercise_type': self.exercise_type.value,
            'last_weight': self.last_weight,
            'next_weight': self.next_weight,
            'weight_change': self.weight_change,
            'decision': self.decision.value,
            'annotation': self.annotation,
            'reason': self.reason,
        }
        
        if self.micro_plate_suggestion:
            result['micro_plate_suggestion'] = True
            result['micro_plate_message'] = self.micro_plate_message
        
        if self.regression_detected:
            result['regression_detected'] = True
            result['regression_message'] = self.regression_message
        
        if self.mav_warning:
            result['mav_warning'] = True
            result['mav_message'] = self.mav_message
        
        return result


@dataclass
class MAVCheckResult:
    """MAV检查结果"""
    muscle_group: str
    current_weekly_sets: int
    mav_sets: int
    is_approaching_mav: bool
    is_exceeding_mav: bool
    message: str


class ProgressiveOverloadCalculator:
    """
    渐进过载自动计算服务（简化版）
    
    核心功能：
    - calculate_next_weight: 计算下周建议重量
    - detect_regression: 检测重量退步
    - suggest_micro_plates: 提醒用户购买1.25kg小片
    - check_mav_limit: 检查是否接近用户MAV
    
    设计原则：
    - 简单逻辑：完成所有目标次数 → +2.5kg（复合）或 +1.25kg（孤立）
    - 保守调整：未完成 → 保持重量
    - 安全优先：检测退步时提示技术排查
    
    Requirements: 8.1, 8.2, 8.3, 8.4 - 渐进过载自动化
    """
    
    # 不同动作类型的加重幅度（kg）
    WEIGHT_INCREMENT = {
        ExerciseType.COMPOUND: 2.5,    # 复合动作：深蹲、卧推、硬拉
        ExerciseType.ISOLATION: 1.25   # 孤立动作：弯举、飞鸟、侧平举
    }
    
    # 退步检测阈值
    REGRESSION_THRESHOLD = 0.10  # 重量下降超过10%视为退步
    
    # 微调阈值（未完成时的微降幅度）
    MICRO_DECREASE_PERCENT = 0.05  # 最多降低5%
    
    # 常见复合动作列表（用于自动识别动作类型）
    COMPOUND_EXERCISES = {
        'squat', 'deadlift', 'bench_press', 'overhead_press', 'barbell_row',
        'pull_up', 'chin_up', 'dip', 'lunge', 'leg_press', 'hip_thrust',
        '深蹲', '硬拉', '卧推', '推举', '划船', '引体向上', '双杠臂屈伸', '弓步', '腿举', '臀推'
    }
    
    # 常见孤立动作列表
    ISOLATION_EXERCISES = {
        'bicep_curl', 'tricep_extension', 'lateral_raise', 'front_raise',
        'leg_curl', 'leg_extension', 'calf_raise', 'fly', 'cable_crossover',
        '弯举', '臂屈伸', '侧平举', '前平举', '腿弯举', '腿屈伸', '提踵', '飞鸟', '夹胸'
    }
    
    # 各肌群的MAV参考值（每周组数）
    # 基于Renaissance Periodization的研究数据
    MAV_REFERENCE = {
        'chest': {'mav': 20, 'mrv': 22},
        'back': {'mav': 20, 'mrv': 25},
        'shoulders': {'mav': 16, 'mrv': 22},
        'biceps': {'mav': 14, 'mrv': 20},
        'triceps': {'mav': 14, 'mrv': 18},
        'quads': {'mav': 18, 'mrv': 20},
        'hamstrings': {'mav': 16, 'mrv': 20},
        'glutes': {'mav': 16, 'mrv': 20},
        'calves': {'mav': 16, 'mrv': 20},
        'abs': {'mav': 16, 'mrv': 25},
        # 中文映射
        '胸': {'mav': 20, 'mrv': 22},
        '背': {'mav': 20, 'mrv': 25},
        '肩': {'mav': 16, 'mrv': 22},
        '二头': {'mav': 14, 'mrv': 20},
        '三头': {'mav': 14, 'mrv': 18},
        '股四头': {'mav': 18, 'mrv': 20},
        '腘绳肌': {'mav': 16, 'mrv': 20},
        '臀': {'mav': 16, 'mrv': 20},
        '小腿': {'mav': 16, 'mrv': 20},
        '腹': {'mav': 16, 'mrv': 25},
    }
    
    def __init__(self, backend_client=None, training_log_analyzer=None):
        """
        初始化渐进过载计算器
        
        Args:
            backend_client: 后端客户端（可选，用于获取用户数据）
            training_log_analyzer: 训练日志分析器（可选，用于获取历史数据）
        """
        self.backend_client = backend_client
        self.training_log_analyzer = training_log_analyzer
        logger.info("ProgressiveOverloadCalculator initialized")
    
    def _identify_exercise_type(
        self,
        exercise_id: str,
        exercise_name: str = "",
        explicit_type: Optional[ExerciseType] = None
    ) -> ExerciseType:
        """
        识别动作类型
        
        Args:
            exercise_id: 动作ID
            exercise_name: 动作名称
            explicit_type: 显式指定的类型（优先使用）
            
        Returns:
            ExerciseType: 动作类型
        """
        if explicit_type:
            return explicit_type
        
        # 检查ID和名称是否匹配复合动作
        check_str = f"{exercise_id} {exercise_name}".lower()
        
        for compound in self.COMPOUND_EXERCISES:
            if compound.lower() in check_str:
                return ExerciseType.COMPOUND
        
        for isolation in self.ISOLATION_EXERCISES:
            if isolation.lower() in check_str:
                return ExerciseType.ISOLATION
        
        # 默认为复合动作（更保守的加重策略）
        return ExerciseType.COMPOUND
    
    def calculate_next_weight(
        self,
        last_weight: float,
        completed_all_reps: bool,
        exercise_type: ExerciseType = ExerciseType.COMPOUND,
        exercise_id: str = "",
        exercise_name: str = ""
    ) -> Tuple[float, OverloadDecision, str]:
        """
        计算下周建议重量
        
        简单逻辑：
        - 完成所有目标次数 → 增加重量（复合+2.5kg，孤立+1.25kg）
        - 未完成目标次数 → 保持重量
        
        Args:
            last_weight: 上周使用的重量（kg）
            completed_all_reps: 是否完成所有目标次数
            exercise_type: 动作类型
            exercise_id: 动作ID（用于日志）
            exercise_name: 动作名称（用于日志）
            
        Returns:
            Tuple[float, OverloadDecision, str]: (下周重量, 决策, 原因)
            
        Requirements: 8.1, 8.2 - 渐进过载正向/保守调整
        """
        if completed_all_reps:
            # 完成所有目标次数 → 增加重量
            increment = self.WEIGHT_INCREMENT.get(exercise_type, 2.5)
            next_weight = last_weight + increment
            decision = OverloadDecision.INCREASE
            reason = f"完成所有目标次数，建议增加{increment}kg"
            
            logger.info(
                f"渐进过载计算: {exercise_name or exercise_id} "
                f"{last_weight}kg → {next_weight}kg (+{increment}kg)",
                extra={
                    'exercise_id': exercise_id,
                    'last_weight': last_weight,
                    'next_weight': next_weight,
                    'decision': decision.value,
                }
            )
        else:
            # 未完成目标次数 → 保持重量
            next_weight = last_weight
            decision = OverloadDecision.MAINTAIN
            reason = "未完成所有目标次数，建议保持当前重量，专注于完成目标次数"
            
            logger.info(
                f"渐进过载计算: {exercise_name or exercise_id} "
                f"{last_weight}kg → {next_weight}kg (保持)",
                extra={
                    'exercise_id': exercise_id,
                    'last_weight': last_weight,
                    'next_weight': next_weight,
                    'decision': decision.value,
                }
            )
        
        return next_weight, decision, reason
    
    def detect_regression(
        self,
        current_weight: float,
        personal_best: float,
        exercise_id: str = "",
        exercise_name: str = ""
    ) -> Tuple[bool, Optional[str]]:
        """
        检测重量退步
        
        当前重量比个人最佳下降超过10%时，触发技术排查提示。
        
        Args:
            current_weight: 当前使用的重量（kg）
            personal_best: 个人最佳记录（kg）
            exercise_id: 动作ID
            exercise_name: 动作名称
            
        Returns:
            Tuple[bool, Optional[str]]: (是否检测到退步, 提示信息)
            
        Requirements: 8.3 - 检测重量下降超过10%
        """
        if personal_best <= 0:
            return False, None
        
        regression_percent = (personal_best - current_weight) / personal_best
        
        if regression_percent > self.REGRESSION_THRESHOLD:
            message = (
                f"⚠️ 检测到{exercise_name or exercise_id}重量下降"
                f"（当前{current_weight}kg vs 最佳{personal_best}kg，下降{regression_percent:.0%}）\n"
                f"建议：\n"
                f"1. 检查动作技术是否正确\n"
                f"2. 确认是否有疲劳累积\n"
                f"3. 考虑是否需要更换动作变体"
            )
            
            logger.warning(
                f"检测到重量退步: {exercise_name or exercise_id} "
                f"current={current_weight}kg, pb={personal_best}kg, "
                f"regression={regression_percent:.0%}",
                extra={
                    'exercise_id': exercise_id,
                    'current_weight': current_weight,
                    'personal_best': personal_best,
                    'regression_percent': regression_percent,
                }
            )
            
            return True, message
        
        return False, None
    
    def suggest_micro_plates(
        self,
        exercise_type: ExerciseType,
        exercise_name: str = ""
    ) -> Tuple[bool, Optional[str]]:
        """
        提醒用户购买1.25kg小片
        
        对于孤立动作，2.5kg的增幅太大，建议使用1.25kg小片实现更精细的渐进。
        
        Args:
            exercise_type: 动作类型
            exercise_name: 动作名称
            
        Returns:
            Tuple[bool, Optional[str]]: (是否建议购买小片, 提示信息)
        """
        if exercise_type == ExerciseType.ISOLATION:
            message = (
                f"💡 小片建议：{exercise_name}是孤立动作，"
                f"2.5kg的增幅可能太大。\n"
                f"建议购买1.25kg小片（约20-30元/对），"
                f"实现更精细的渐进过载，避免因增幅过大导致动作变形。"
            )
            return True, message
        
        return False, None
    
    def check_mav_limit(
        self,
        muscle_group: str,
        current_weekly_sets: int,
        user_volume_multiplier: float = 1.0
    ) -> MAVCheckResult:
        """
        检查是否接近用户MAV（最大适应训练量）
        
        渐进过载不仅是增加重量，还需要考虑总训练量是否超出恢复能力。
        
        Args:
            muscle_group: 肌群名称
            current_weekly_sets: 当前每周训练组数
            user_volume_multiplier: 用户个性化容量系数（0.7-1.5）
            
        Returns:
            MAVCheckResult: MAV检查结果
        """
        # 获取该肌群的MAV参考值
        mav_data = self.MAV_REFERENCE.get(
            muscle_group.lower(),
            {'mav': 16, 'mrv': 20}  # 默认值
        )
        
        # 根据用户容量系数调整MAV
        adjusted_mav = int(mav_data['mav'] * user_volume_multiplier)
        adjusted_mrv = int(mav_data['mrv'] * user_volume_multiplier)
        
        # 检查是否接近或超过MAV
        is_approaching = current_weekly_sets >= adjusted_mav * 0.9
        is_exceeding = current_weekly_sets > adjusted_mav
        
        if is_exceeding:
            message = (
                f"⚠️ {muscle_group}训练量已超过MAV"
                f"（当前{current_weekly_sets}组 > MAV {adjusted_mav}组）\n"
                f"建议：减少训练组数或安排Deload周，避免超出恢复能力"
            )
        elif is_approaching:
            message = (
                f"📊 {muscle_group}训练量接近MAV"
                f"（当前{current_weekly_sets}组，MAV {adjusted_mav}组）\n"
                f"提示：可以继续增加重量，但不建议再增加组数"
            )
        else:
            message = (
                f"✅ {muscle_group}训练量在合理范围内"
                f"（当前{current_weekly_sets}组，MAV {adjusted_mav}组）"
            )
        
        return MAVCheckResult(
            muscle_group=muscle_group,
            current_weekly_sets=current_weekly_sets,
            mav_sets=adjusted_mav,
            is_approaching_mav=is_approaching,
            is_exceeding_mav=is_exceeding,
            message=message
        )
    
    def get_weight_annotation(
        self,
        last_weight: float,
        next_weight: float
    ) -> str:
        """
        生成重量变化标注
        
        用于在训练计划中显示"比上周+Xkg"或"保持上周重量"。
        
        Args:
            last_weight: 上周重量
            next_weight: 下周建议重量
            
        Returns:
            str: 重量变化标注
            
        Requirements: 8.4 - 在动作旁标注重量变化
        """
        diff = next_weight - last_weight
        
        if diff > 0:
            return f"+{diff:.1f}kg"
        elif diff < 0:
            return f"{diff:.1f}kg"
        else:
            return "保持"
    
    def calculate_overload(
        self,
        exercise_id: str,
        exercise_name: str,
        last_weight: float,
        completed_all_reps: bool,
        personal_best: float = 0.0,
        exercise_type: Optional[ExerciseType] = None,
        muscle_group: str = "",
        current_weekly_sets: int = 0,
        user_volume_multiplier: float = 1.0
    ) -> OverloadResult:
        """
        执行完整的渐进过载计算
        
        整合所有功能：计算下周重量、检测退步、提醒小片、检查MAV。
        
        Args:
            exercise_id: 动作ID
            exercise_name: 动作名称
            last_weight: 上周使用的重量
            completed_all_reps: 是否完成所有目标次数
            personal_best: 个人最佳记录（可选）
            exercise_type: 动作类型（可选，自动识别）
            muscle_group: 主要肌群（可选，用于MAV检查）
            current_weekly_sets: 当前每周训练组数（可选）
            user_volume_multiplier: 用户容量系数（可选）
            
        Returns:
            OverloadResult: 渐进过载计算结果
        """
        # 1. 识别动作类型
        ex_type = self._identify_exercise_type(
            exercise_id, exercise_name, exercise_type
        )
        
        # 2. 计算下周重量
        next_weight, decision, reason = self.calculate_next_weight(
            last_weight=last_weight,
            completed_all_reps=completed_all_reps,
            exercise_type=ex_type,
            exercise_id=exercise_id,
            exercise_name=exercise_name
        )
        
        # 3. 检测退步
        regression_detected, regression_message = self.detect_regression(
            current_weight=last_weight,
            personal_best=personal_best,
            exercise_id=exercise_id,
            exercise_name=exercise_name
        )
        
        # 如果检测到退步，调整决策
        if regression_detected:
            decision = OverloadDecision.TECHNIQUE_CHECK
            reason = "检测到重量退步，建议进行技术排查"
        
        # 4. 提醒小片
        micro_plate_suggestion, micro_plate_message = self.suggest_micro_plates(
            exercise_type=ex_type,
            exercise_name=exercise_name
        )
        
        # 5. 检查MAV（如果提供了肌群信息）
        mav_warning = False
        mav_message = None
        if muscle_group and current_weekly_sets > 0:
            mav_result = self.check_mav_limit(
                muscle_group=muscle_group,
                current_weekly_sets=current_weekly_sets,
                user_volume_multiplier=user_volume_multiplier
            )
            mav_warning = mav_result.is_approaching_mav or mav_result.is_exceeding_mav
            mav_message = mav_result.message if mav_warning else None
        
        # 6. 生成标注
        annotation = self.get_weight_annotation(last_weight, next_weight)
        
        # 7. 构建结果
        result = OverloadResult(
            exercise_id=exercise_id,
            exercise_name=exercise_name,
            exercise_type=ex_type,
            last_weight=last_weight,
            next_weight=next_weight,
            weight_change=next_weight - last_weight,
            decision=decision,
            annotation=annotation,
            reason=reason,
            micro_plate_suggestion=micro_plate_suggestion,
            micro_plate_message=micro_plate_message,
            regression_detected=regression_detected,
            regression_message=regression_message,
            mav_warning=mav_warning,
            mav_message=mav_message
        )
        
        logger.info(
            f"渐进过载计算完成: {exercise_name} "
            f"{last_weight}kg → {next_weight}kg ({annotation})",
            extra={'result': result.to_dict()}
        )
        
        return result
    
    async def calculate_overload_for_plan(
        self,
        user_id: int,
        exercises: List[Dict[str, Any]],
        user_profile: Optional[Dict[str, Any]] = None
    ) -> List[OverloadResult]:
        """
        为训练计划中的所有动作计算渐进过载
        
        Args:
            user_id: 用户ID
            exercises: 动作列表
            user_profile: 用户档案（可选）
            
        Returns:
            List[OverloadResult]: 所有动作的渐进过载结果
        """
        results = []
        
        # 获取用户容量系数
        volume_multiplier = 1.0
        if user_profile:
            training_system = user_profile.get('training_system', {})
            volume_multiplier = float(
                training_system.get('personal_volume_multiplier', 1.0)
            )
        
        # 获取用户的个人最佳记录（如果有backend_client）
        personal_bests = {}
        if self.backend_client:
            try:
                pb_data = await self.backend_client.get_personal_bests(user_id)
                personal_bests = {
                    pb['exercise_id']: pb['best_weight']
                    for pb in pb_data
                }
            except Exception as e:
                logger.warning(f"获取个人最佳记录失败: {e}")
        
        for exercise in exercises:
            exercise_id = exercise.get('exercise_id', '')
            exercise_name = exercise.get('name_zh', exercise.get('name_en', ''))
            last_weight = exercise.get('last_weight', 0.0)
            completed_all_reps = exercise.get('completed_all_reps', True)
            muscle_group = exercise.get('primary_muscle', '')
            current_sets = exercise.get('sets', 0)
            
            # 获取个人最佳
            personal_best = personal_bests.get(exercise_id, 0.0)
            
            result = self.calculate_overload(
                exercise_id=exercise_id,
                exercise_name=exercise_name,
                last_weight=last_weight,
                completed_all_reps=completed_all_reps,
                personal_best=personal_best,
                muscle_group=muscle_group,
                current_weekly_sets=current_sets,
                user_volume_multiplier=volume_multiplier
            )
            
            results.append(result)
        
        return results
