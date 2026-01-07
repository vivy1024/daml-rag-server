# -*- coding: utf-8 -*-
"""
Volume Adjuster Service

个性化容量动态调整服务，基于用户训练表现自动调整训练容量。
这是闭环学习系统的核心组件，实现"会学习、会调整"的AI私教功能。

Requirements: 7.1, 7.2, 7.3, 7.4, 7.5

作者: BUILD_BODY Team
版本: 1.0.0
日期: 2025-12-26
"""

import logging
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class AdjustmentDirection(str, Enum):
    """调整方向"""
    INCREASE = "increase"    # 上调
    DECREASE = "decrease"    # 下调
    MAINTAIN = "maintain"    # 保持


@dataclass
class VolumeAdjustmentResult:
    """容量调整结果"""
    user_id: int
    previous_multiplier: float
    new_multiplier: float
    adjustment_value: float
    direction: AdjustmentDirection
    reason: str
    avg_rpe: float
    avg_completion_rate: float
    should_deload: bool
    deload_reason: Optional[str]
    adjusted_at: str
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'user_id': self.user_id,
            'previous_multiplier': self.previous_multiplier,
            'new_multiplier': self.new_multiplier,
            'adjustment_value': self.adjustment_value,
            'direction': self.direction.value,
            'reason': self.reason,
            'avg_rpe': self.avg_rpe,
            'avg_completion_rate': self.avg_completion_rate,
            'should_deload': self.should_deload,
            'deload_reason': self.deload_reason,
            'adjusted_at': self.adjusted_at,
        }


class VolumeAdjuster:
    """
    个性化容量动态调整服务
    
    基于用户在中周期（4-6周）内的训练表现，自动调整训练容量系数。
    
    调整规则（Requirements 7.2, 7.3）：
    - RPE < 7 且 完成率 > 95%: 上调 +0.05 ~ +0.1
    - RPE > 9.5 或 完成率 < 80%: 下调 -0.1 ~ -0.15
    - 其他情况: 保持或微调
    
    边界约束（Requirements 7.5）：
    - personal_volume_multiplier 始终在 0.7 ~ 1.5 范围内
    
    Requirements: 7.1, 7.2, 7.3, 7.4, 7.5
    """
    
    # 容量系数边界
    MULTIPLIER_MIN = 0.7
    MULTIPLIER_MAX = 1.5
    
    # 调整阈值
    HIGH_COMPLETION_THRESHOLD = 0.95  # 高完成率阈值
    LOW_COMPLETION_THRESHOLD = 0.80   # 低完成率阈值
    LOW_RPE_THRESHOLD = 7.0           # 低RPE阈值（表示训练轻松）
    HIGH_RPE_THRESHOLD = 9.5          # 高RPE阈值（表示训练过重）
    
    # 调整幅度
    INCREASE_MIN = 0.05
    INCREASE_MAX = 0.10
    DECREASE_MIN = -0.15
    DECREASE_MAX = -0.10
    
    # Deload触发条件
    DELOAD_RPE_THRESHOLD = 9.0
    DELOAD_COMPLETION_THRESHOLD = 0.85
    CONSECUTIVE_WEEKS_FOR_DELOAD = 2
    
    def __init__(self, training_log_analyzer, backend_client):
        """
        初始化容量调整器
        
        Args:
            training_log_analyzer: TrainingLogAnalyzer实例，用于获取训练数据分析
            backend_client: BackendClient实例，用于更新用户档案
        """
        self.training_log_analyzer = training_log_analyzer
        self.backend_client = backend_client
        logger.info("VolumeAdjuster initialized")
    
    async def analyze_mesocycle(
        self,
        user_id: int,
        mesocycle_weeks: int = 4
    ) -> Dict[str, Any]:
        """
        分析中周期训练表现
        
        委托给TrainingLogAnalyzer进行详细分析。
        
        Args:
            user_id: 用户ID
            mesocycle_weeks: 中周期周数，默认4周（支持4-6周）
            
        Returns:
            Dict[str, Any]: 中周期分析结果
            
        Requirements: 7.1 - 分析中周期训练表现
        """
        # 限制周数在4-6周范围内
        mesocycle_weeks = max(4, min(6, mesocycle_weeks))
        
        analysis = await self.training_log_analyzer.analyze_mesocycle(
            user_id=user_id,
            mesocycle_weeks=mesocycle_weeks
        )
        
        logger.info(
            f"中周期分析完成: user_id={user_id}, weeks={mesocycle_weeks}, "
            f"sessions={analysis.total_sessions}, "
            f"avg_rpe={analysis.avg_rpe:.1f}, "
            f"avg_completion={analysis.avg_completion_rate:.2f}",
            extra={
                'user_id': user_id,
                'mesocycle_weeks': mesocycle_weeks,
                'total_sessions': analysis.total_sessions,
                'avg_rpe': analysis.avg_rpe,
                'avg_completion_rate': analysis.avg_completion_rate,
            }
        )
        
        return analysis
    
    def calculate_adjustment(
        self,
        avg_rpe: float,
        avg_completion_rate: float,
        current_multiplier: float = 1.0
    ) -> Tuple[float, AdjustmentDirection, str]:
        """
        计算容量调整值
        
        根据RPE和完成率计算应该调整的容量系数。
        
        调整规则：
        - RPE < 7 且 完成率 > 95%: +0.05 ~ +0.1（训练太轻松，可以加量）
        - RPE > 9.5 或 完成率 < 80%: -0.1 ~ -0.15（训练太重，需要减量）
        - 其他情况: 保持或微调
        
        Args:
            avg_rpe: 平均RPE值（1-10）
            avg_completion_rate: 平均完成率（0-1）
            current_multiplier: 当前容量系数
            
        Returns:
            Tuple[float, AdjustmentDirection, str]: (调整值, 调整方向, 原因)
            
        Requirements: 7.2, 7.3 - 根据RPE和完成率计算容量调整
        """
        adjustment = 0.0
        direction = AdjustmentDirection.MAINTAIN
        reason = ""
        
        # 规则1: RPE < 7 且 完成率 > 95% -> 上调容量
        # Requirements 7.2
        if avg_rpe < self.LOW_RPE_THRESHOLD and avg_completion_rate > self.HIGH_COMPLETION_THRESHOLD:
            # 根据具体数值计算调整幅度
            # RPE越低，调整越大；完成率越高，调整越大
            rpe_factor = (self.LOW_RPE_THRESHOLD - avg_rpe) / self.LOW_RPE_THRESHOLD
            completion_factor = (avg_completion_rate - self.HIGH_COMPLETION_THRESHOLD) / (1.0 - self.HIGH_COMPLETION_THRESHOLD)
            
            # 综合因子取较小值，保守调整
            combined_factor = min(rpe_factor, completion_factor)
            
            # 计算调整值：0.05 + (0.05 * factor)，范围 [0.05, 0.10]
            adjustment = self.INCREASE_MIN + (self.INCREASE_MAX - self.INCREASE_MIN) * combined_factor
            adjustment = min(adjustment, self.INCREASE_MAX)
            
            direction = AdjustmentDirection.INCREASE
            reason = f"训练表现优秀（RPE={avg_rpe:.1f}<7, 完成率={avg_completion_rate:.0%}>95%），建议增加训练容量"
            
        # 规则2: RPE > 9.5 或 完成率 < 80% -> 下调容量
        # Requirements 7.3
        elif avg_rpe > self.HIGH_RPE_THRESHOLD or avg_completion_rate < self.LOW_COMPLETION_THRESHOLD:
            # 分别计算RPE和完成率导致的调整
            rpe_adjustment = 0.0
            completion_adjustment = 0.0
            reasons = []
            
            if avg_rpe > self.HIGH_RPE_THRESHOLD:
                # RPE越高，下调越大
                rpe_factor = min((avg_rpe - self.HIGH_RPE_THRESHOLD) / 0.5, 1.0)
                rpe_adjustment = self.DECREASE_MAX + (self.DECREASE_MIN - self.DECREASE_MAX) * rpe_factor
                reasons.append(f"RPE过高({avg_rpe:.1f}>9.5)")
            
            if avg_completion_rate < self.LOW_COMPLETION_THRESHOLD:
                # 完成率越低，下调越大
                completion_factor = min((self.LOW_COMPLETION_THRESHOLD - avg_completion_rate) / 0.20, 1.0)
                completion_adjustment = self.DECREASE_MAX + (self.DECREASE_MIN - self.DECREASE_MAX) * completion_factor
                reasons.append(f"完成率过低({avg_completion_rate:.0%}<80%)")
            
            # 取更大的下调值（更保守）
            adjustment = min(rpe_adjustment, completion_adjustment)
            adjustment = max(adjustment, self.DECREASE_MIN)  # 确保不超过最大下调幅度
            
            direction = AdjustmentDirection.DECREASE
            reason = f"训练负荷过重（{'，'.join(reasons)}），建议降低训练容量"
            
        # 规则3: 其他情况 - 微调或保持
        else:
            # 检查是否有改善趋势
            if avg_rpe < 8.0 and avg_completion_rate > 0.90:
                adjustment = 0.02  # 小幅上调
                direction = AdjustmentDirection.INCREASE
                reason = f"训练表现良好（RPE={avg_rpe:.1f}, 完成率={avg_completion_rate:.0%}），小幅增加容量"
            elif avg_rpe > 8.5 or avg_completion_rate < 0.85:
                adjustment = -0.02  # 小幅下调
                direction = AdjustmentDirection.DECREASE
                reason = f"训练略显吃力（RPE={avg_rpe:.1f}, 完成率={avg_completion_rate:.0%}），小幅降低容量"
            else:
                adjustment = 0.0
                direction = AdjustmentDirection.MAINTAIN
                reason = f"训练负荷适中（RPE={avg_rpe:.1f}, 完成率={avg_completion_rate:.0%}），保持当前容量"
        
        return round(adjustment, 2), direction, reason
    
    def clamp_multiplier(self, multiplier: float) -> float:
        """
        将容量系数限制在有效范围内
        
        Args:
            multiplier: 原始容量系数
            
        Returns:
            float: 限制后的容量系数（0.7-1.5）
            
        Requirements: 7.5 - 容量系数边界约束
        """
        return max(self.MULTIPLIER_MIN, min(self.MULTIPLIER_MAX, multiplier))
    
    def should_suggest_deload(
        self,
        avg_rpe: float,
        avg_completion_rate: float,
        consecutive_high_rpe_weeks: int = 0,
        consecutive_low_completion_weeks: int = 0,
        previous_week_rpe: Optional[float] = None,
        previous_week_completion: Optional[float] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        判断是否应该建议Deload周
        
        触发条件（Requirements 9.2）：
        - 连续2周RPE > 9
        - 连续2周完成率 < 85%
        - RPE > 9.5 且 完成率 < 85%（单周严重情况）
        
        Args:
            avg_rpe: 当前周平均RPE值
            avg_completion_rate: 当前周平均完成率
            consecutive_high_rpe_weeks: 连续高RPE周数
            consecutive_low_completion_weeks: 连续低完成率周数
            previous_week_rpe: 上周平均RPE（用于连续周检测）
            previous_week_completion: 上周平均完成率（用于连续周检测）
            
        Returns:
            Tuple[bool, Optional[str]]: (是否建议Deload, 原因)
            
        Requirements: 9.1, 9.2, 9.3 - Deload周提示
        """
        reasons = []
        
        # 检查连续高RPE（Requirements 9.2）
        # 方式1：通过传入的连续周数
        if consecutive_high_rpe_weeks >= self.CONSECUTIVE_WEEKS_FOR_DELOAD:
            reasons.append(f"连续{consecutive_high_rpe_weeks}周RPE过高(>9)")
        
        # 方式2：通过上周数据检测连续两周
        if previous_week_rpe is not None:
            current_week_high_rpe = avg_rpe > self.DELOAD_RPE_THRESHOLD
            previous_week_high_rpe = previous_week_rpe > self.DELOAD_RPE_THRESHOLD
            if current_week_high_rpe and previous_week_high_rpe:
                reasons.append(f"连续2周RPE过高（本周{avg_rpe:.1f}，上周{previous_week_rpe:.1f}，阈值>9）")
        
        # 检查连续低完成率（Requirements 9.2）
        # 方式1：通过传入的连续周数
        if consecutive_low_completion_weeks >= self.CONSECUTIVE_WEEKS_FOR_DELOAD:
            reasons.append(f"连续{consecutive_low_completion_weeks}周完成率过低(<85%)")
        
        # 方式2：通过上周数据检测连续两周
        if previous_week_completion is not None:
            current_week_low_completion = avg_completion_rate < self.DELOAD_COMPLETION_THRESHOLD
            previous_week_low_completion = previous_week_completion < self.DELOAD_COMPLETION_THRESHOLD
            if current_week_low_completion and previous_week_low_completion:
                reasons.append(
                    f"连续2周完成率过低（本周{avg_completion_rate:.0%}，上周{previous_week_completion:.0%}，阈值<85%）"
                )
        
        # 检查当前周期的严重情况（单周极端情况）
        if avg_rpe > self.HIGH_RPE_THRESHOLD and avg_completion_rate < self.DELOAD_COMPLETION_THRESHOLD:
            reasons.append(f"单周极端疲劳：RPE过高({avg_rpe:.1f}>9.5)且完成率过低({avg_completion_rate:.0%}<85%)")
        
        # 检查单项严重超标
        if avg_rpe > 9.5:
            # 只有在没有其他原因时才添加，避免重复
            if not any("RPE" in r for r in reasons):
                reasons.append(f"RPE严重超标({avg_rpe:.1f}>9.5)")
        
        if avg_completion_rate < 0.75:
            # 只有在没有其他原因时才添加，避免重复
            if not any("完成率" in r for r in reasons):
                reasons.append(f"完成率严重不足({avg_completion_rate:.0%}<75%)")
        
        should_deload = len(reasons) >= 1
        deload_reason = "；".join(reasons) if reasons else None
        
        if should_deload:
            logger.info(
                f"建议进入Deload周: reasons={deload_reason}",
                extra={
                    'avg_rpe': avg_rpe,
                    'avg_completion_rate': avg_completion_rate,
                    'consecutive_high_rpe_weeks': consecutive_high_rpe_weeks,
                    'consecutive_low_completion_weeks': consecutive_low_completion_weeks,
                }
            )
        
        return should_deload, deload_reason
    
    def get_deload_recommendation(
        self,
        avg_rpe: float,
        avg_completion_rate: float,
        consecutive_high_rpe_weeks: int = 0,
        consecutive_low_completion_weeks: int = 0,
        previous_week_rpe: Optional[float] = None,
        previous_week_completion: Optional[float] = None,
        current_week_number: int = 1,
        total_weeks: int = 4
    ) -> Dict[str, Any]:
        """
        获取Deload建议详情
        
        复用现有PeriodizationModel的Deload阶段配置，生成完整的Deload建议。
        
        Args:
            avg_rpe: 当前周平均RPE值
            avg_completion_rate: 当前周平均完成率
            consecutive_high_rpe_weeks: 连续高RPE周数
            consecutive_low_completion_weeks: 连续低完成率周数
            previous_week_rpe: 上周平均RPE
            previous_week_completion: 上周平均完成率
            current_week_number: 当前周数
            total_weeks: 总周数
            
        Returns:
            Dict[str, Any]: Deload建议详情
            
        Requirements: 9.1, 9.2, 9.3 - Deload周提示和通知
        """
        should_deload, deload_reason = self.should_suggest_deload(
            avg_rpe=avg_rpe,
            avg_completion_rate=avg_completion_rate,
            consecutive_high_rpe_weeks=consecutive_high_rpe_weeks,
            consecutive_low_completion_weeks=consecutive_low_completion_weeks,
            previous_week_rpe=previous_week_rpe,
            previous_week_completion=previous_week_completion
        )
        
        # 复用PeriodizationModel的Deload阶段配置
        # 参考WeeklyPlanGenerator.PHASE_CONFIG[4]
        deload_phase_config = {
            "phase": "deload",
            "name_zh": "减量期",
            "description": "使用最小有效训练量（MEV），促进超量恢复",
            "volume_factor": 0.6,  # 容量降至60%
            "intensity_factor": 0.8,  # 强度降至80%
        }
        
        # 生成用户通知消息（Requirements 9.3）
        if should_deload:
            notification_message = self._generate_deload_notification(
                deload_reason=deload_reason,
                current_week_number=current_week_number,
                total_weeks=total_weeks,
                avg_rpe=avg_rpe,
                avg_completion_rate=avg_completion_rate
            )
        else:
            notification_message = None
        
        return {
            'should_deload': should_deload,
            'reason': deload_reason,
            'notification_message': notification_message,
            'deload_config': deload_phase_config if should_deload else None,
            'metrics': {
                'current_rpe': avg_rpe,
                'current_completion_rate': avg_completion_rate,
                'consecutive_high_rpe_weeks': consecutive_high_rpe_weeks,
                'consecutive_low_completion_weeks': consecutive_low_completion_weeks,
                'previous_week_rpe': previous_week_rpe,
                'previous_week_completion': previous_week_completion,
            },
            'thresholds': {
                'rpe_threshold': self.DELOAD_RPE_THRESHOLD,
                'completion_threshold': self.DELOAD_COMPLETION_THRESHOLD,
                'consecutive_weeks_required': self.CONSECUTIVE_WEEKS_FOR_DELOAD,
            }
        }
    
    def _generate_deload_notification(
        self,
        deload_reason: str,
        current_week_number: int,
        total_weeks: int,
        avg_rpe: float,
        avg_completion_rate: float
    ) -> str:
        """
        生成Deload周通知消息
        
        Requirements: 9.3 - 进入Deload阶段时，通知用户并解释原因
        
        Args:
            deload_reason: Deload原因
            current_week_number: 当前周数
            total_weeks: 总周数
            avg_rpe: 平均RPE
            avg_completion_rate: 平均完成率
            
        Returns:
            str: 通知消息
        """
        message = f"""🔄 **建议进入减量恢复周**

📊 **检测到的问题**：
{deload_reason}

📈 **当前训练指标**：
- 平均RPE: {avg_rpe:.1f}/10
- 完成率: {avg_completion_rate:.0%}
- 当前周期: 第{current_week_number}周/{total_weeks}周

💡 **减量周说明**：
减量周（Deload）是周期化训练的重要组成部分，目的是：
1. 消除累积的疲劳
2. 促进肌肉和神经系统恢复
3. 为下一个训练周期做准备

📋 **减量周调整**：
- 训练容量降至60%（组数减半）
- 训练强度降至80%（重量适当降低）
- 保持训练频率不变

⚠️ **注意事项**：
- 减量周不是休息周，仍需保持训练
- 专注于动作质量和技术细节
- 充分休息和营养补充

完成减量周后，您将以更好的状态进入下一个训练周期！"""
        
        return message

    
    async def apply_adjustment(
        self,
        user_id: int,
        adjustment: float,
        current_multiplier: float,
        reason: str
    ) -> float:
        """
        应用容量调整到用户档案
        
        通过BackendClient更新用户的personal_volume_multiplier字段。
        
        Args:
            user_id: 用户ID
            adjustment: 调整值
            current_multiplier: 当前容量系数
            reason: 调整原因
            
        Returns:
            float: 调整后的容量系数
            
        Requirements: 7.4 - 记录调整时间和原因，并通知用户
        """
        # 计算新的容量系数
        new_multiplier = self.clamp_multiplier(current_multiplier + adjustment)
        
        try:
            # 通过BackendClient更新用户档案
            result = await self.backend_client.update_volume_multiplier(
                user_id=user_id,
                new_multiplier=new_multiplier,
                adjustment=adjustment,
                reason=reason
            )
            
            logger.info(
                f"容量调整已应用: user_id={user_id}, "
                f"{current_multiplier:.2f} -> {new_multiplier:.2f} "
                f"(adjustment={adjustment:+.2f})",
                extra={
                    'user_id': user_id,
                    'previous_multiplier': current_multiplier,
                    'new_multiplier': new_multiplier,
                    'adjustment': adjustment,
                    'reason': reason,
                }
            )
            
            return new_multiplier
            
        except Exception as e:
            logger.error(
                f"容量调整应用失败: user_id={user_id}, error={e}",
                extra={'user_id': user_id, 'error': str(e)}
            )
            # 返回原始值，不做调整
            return current_multiplier
    
    async def adjust_volume(
        self,
        user_id: int,
        mesocycle_weeks: int = 4
    ) -> VolumeAdjustmentResult:
        """
        执行完整的容量调整流程
        
        1. 分析中周期训练表现
        2. 计算调整值
        3. 应用调整到用户档案
        4. 返回调整结果
        
        Args:
            user_id: 用户ID
            mesocycle_weeks: 中周期周数，默认4周
            
        Returns:
            VolumeAdjustmentResult: 容量调整结果
            
        Requirements: 7.1, 7.2, 7.3, 7.4
        """
        # 1. 获取当前用户档案
        try:
            profile = await self.backend_client.get_user_profile(user_id)
            training_system = profile.get('training_system', {})
            current_multiplier = float(training_system.get('personal_volume_multiplier', 1.0))
            current_multiplier = self.clamp_multiplier(current_multiplier)
        except Exception as e:
            logger.warning(f"获取用户档案失败，使用默认值: user_id={user_id}, error={e}")
            current_multiplier = 1.0
        
        # 2. 分析中周期训练表现
        analysis = await self.analyze_mesocycle(user_id, mesocycle_weeks)
        
        # 检查是否有足够的训练数据
        if analysis.total_sessions < 3:
            logger.info(
                f"训练数据不足，跳过容量调整: user_id={user_id}, sessions={analysis.total_sessions}",
                extra={'user_id': user_id, 'total_sessions': analysis.total_sessions}
            )
            return VolumeAdjustmentResult(
                user_id=user_id,
                previous_multiplier=current_multiplier,
                new_multiplier=current_multiplier,
                adjustment_value=0.0,
                direction=AdjustmentDirection.MAINTAIN,
                reason="训练数据不足（少于3次训练），暂不调整容量",
                avg_rpe=analysis.avg_rpe,
                avg_completion_rate=analysis.avg_completion_rate,
                should_deload=False,
                deload_reason=None,
                adjusted_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            )
        
        # 3. 计算调整值
        adjustment, direction, reason = self.calculate_adjustment(
            avg_rpe=analysis.avg_rpe,
            avg_completion_rate=analysis.avg_completion_rate,
            current_multiplier=current_multiplier
        )
        
        # 4. 检查是否需要Deload
        should_deload, deload_reason = self.should_suggest_deload(
            avg_rpe=analysis.avg_rpe,
            avg_completion_rate=analysis.avg_completion_rate
        )
        
        # 5. 应用调整（如果有变化）
        if adjustment != 0.0:
            new_multiplier = await self.apply_adjustment(
                user_id=user_id,
                adjustment=adjustment,
                current_multiplier=current_multiplier,
                reason=reason
            )
        else:
            new_multiplier = current_multiplier
        
        # 6. 构建结果
        result = VolumeAdjustmentResult(
            user_id=user_id,
            previous_multiplier=current_multiplier,
            new_multiplier=new_multiplier,
            adjustment_value=adjustment,
            direction=direction,
            reason=reason,
            avg_rpe=analysis.avg_rpe,
            avg_completion_rate=analysis.avg_completion_rate,
            should_deload=should_deload,
            deload_reason=deload_reason,
            adjusted_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        )
        
        logger.info(
            f"容量调整完成: user_id={user_id}, "
            f"direction={direction.value}, "
            f"adjustment={adjustment:+.2f}, "
            f"should_deload={should_deload}",
            extra={
                'user_id': user_id,
                'result': result.to_dict(),
            }
        )
        
        return result
    
    async def get_adjustment_recommendation(
        self,
        user_id: int,
        mesocycle_weeks: int = 4
    ) -> Dict[str, Any]:
        """
        获取容量调整建议（不实际应用）
        
        用于预览调整效果，让用户确认后再应用。
        
        Args:
            user_id: 用户ID
            mesocycle_weeks: 中周期周数
            
        Returns:
            Dict[str, Any]: 调整建议
        """
        # 获取当前用户档案
        try:
            profile = await self.backend_client.get_user_profile(user_id)
            training_system = profile.get('training_system', {})
            current_multiplier = float(training_system.get('personal_volume_multiplier', 1.0))
            current_multiplier = self.clamp_multiplier(current_multiplier)
        except Exception as e:
            logger.warning(f"获取用户档案失败，使用默认值: user_id={user_id}, error={e}")
            current_multiplier = 1.0
        
        # 分析中周期训练表现
        analysis = await self.analyze_mesocycle(user_id, mesocycle_weeks)
        
        # 计算调整值
        adjustment, direction, reason = self.calculate_adjustment(
            avg_rpe=analysis.avg_rpe,
            avg_completion_rate=analysis.avg_completion_rate,
            current_multiplier=current_multiplier
        )
        
        # 检查是否需要Deload
        should_deload, deload_reason = self.should_suggest_deload(
            avg_rpe=analysis.avg_rpe,
            avg_completion_rate=analysis.avg_completion_rate
        )
        
        # 计算预期的新容量系数
        expected_new_multiplier = self.clamp_multiplier(current_multiplier + adjustment)
        
        return {
            'user_id': user_id,
            'current_multiplier': current_multiplier,
            'expected_new_multiplier': expected_new_multiplier,
            'adjustment': adjustment,
            'direction': direction.value,
            'reason': reason,
            'analysis': {
                'mesocycle_weeks': mesocycle_weeks,
                'total_sessions': analysis.total_sessions,
                'avg_rpe': analysis.avg_rpe,
                'avg_completion_rate': analysis.avg_completion_rate,
            },
            'deload_recommendation': {
                'should_deload': should_deload,
                'reason': deload_reason,
            },
            'preview_only': True,
        }
