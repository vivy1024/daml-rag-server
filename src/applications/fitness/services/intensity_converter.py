# -*- coding: utf-8 -*-
"""
Intensity Converter Service

训练强度指标转换服务，支持RPE、%1RM、RIR三种强度指标的相互转换。
基于运动科学研究数据，提供专业的强度指标转换和推荐功能。

核心功能：
- RPE (Rating of Perceived Exertion) 主观疲劳度量表 (1-10)
- %1RM (Percentage of 1 Rep Max) 最大重量百分比
- RIR (Reps in Reserve) 储备次数 (0-5)
- 三种指标间的相互转换
- 基于用户偏好的强度推荐

Requirements: 10.1, 10.2, 10.3, 10.4, 10.5 - 训练强度指标扩展

作者: BUILD_BODY Team
版本: 1.0.0
日期: 2026-01-06
"""

import logging
from typing import Dict, Any, Optional, List, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class IntensityMetric(str, Enum):
    """强度指标类型"""
    RPE = "rpe"           # Rating of Perceived Exertion (1-10)
    PERCENT_1RM = "percent_1rm"  # Percentage of 1 Rep Max (0-100)
    RIR = "rir"           # Reps in Reserve (0-5)


from ..types.enums import TrainingGoal


@dataclass
class IntensityValue:
    """强度值数据类"""
    metric: IntensityMetric
    value: float
    description: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'metric': self.metric.value,
            'value': self.value,
            'description': self.description,
        }


@dataclass
class IntensityConversionResult:
    """强度转换结果"""
    source: IntensityValue
    target: IntensityValue
    tolerance: float  # 转换容差
    notes: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'source': self.source.to_dict(),
            'target': self.target.to_dict(),
            'tolerance': self.tolerance,
            'notes': self.notes,
        }


@dataclass
class IntensityRecommendation:
    """强度推荐结果"""
    goal: TrainingGoal
    rpe: IntensityValue
    percent_1rm: IntensityValue
    rir: IntensityValue
    rep_range: Tuple[int, int]
    set_range: Tuple[int, int]
    rest_seconds: Tuple[int, int]
    notes: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'goal': self.goal.value,
            'rpe': self.rpe.to_dict(),
            'percent_1rm': self.percent_1rm.to_dict(),
            'rir': self.rir.to_dict(),
            'rep_range': list(self.rep_range),
            'set_range': list(self.set_range),
            'rest_seconds': list(self.rest_seconds),
            'notes': self.notes,
        }


class IntensityConverter:
    """
    训练强度指标转换服务
    
    支持三种强度指标的相互转换：
    - RPE (Rating of Perceived Exertion): 主观疲劳度量表，1-10分
    - %1RM (Percentage of 1 Rep Max): 最大重量百分比，0-100%
    - RIR (Reps in Reserve): 储备次数，0-5次
    
    转换关系基于运动科学研究数据：
    - RPE 10 ≈ 0 RIR ≈ 100% 1RM (力竭)
    - RPE 9 ≈ 1 RIR ≈ 92-95% 1RM
    - RPE 8 ≈ 2 RIR ≈ 85-90% 1RM
    - RPE 7 ≈ 3 RIR ≈ 80-85% 1RM
    - RPE 6 ≈ 4 RIR ≈ 75-80% 1RM
    - RPE 5 ≈ 5+ RIR ≈ 70-75% 1RM
    
    Requirements: 10.1, 10.2, 10.3, 10.4, 10.5
    """
    
    # RPE到RIR的映射表（精确映射）
    # RPE 10 = 0 RIR, RPE 9 = 1 RIR, etc.
    RPE_TO_RIR_MAP: Dict[float, float] = {
        10.0: 0.0,
        9.5: 0.5,
        9.0: 1.0,
        8.5: 1.5,
        8.0: 2.0,
        7.5: 2.5,
        7.0: 3.0,
        6.5: 3.5,
        6.0: 4.0,
        5.5: 4.5,
        5.0: 5.0,
    }
    
    # RPE到%1RM的映射表（基于研究数据）
    # 注意：这是近似值，实际会因个体差异和动作类型而变化
    RPE_TO_PERCENT_1RM_MAP: Dict[float, Tuple[float, float]] = {
        10.0: (100.0, 100.0),  # 力竭
        9.5: (97.0, 100.0),
        9.0: (92.0, 97.0),
        8.5: (89.0, 92.0),
        8.0: (85.0, 89.0),
        7.5: (82.0, 85.0),
        7.0: (78.0, 82.0),
        6.5: (75.0, 78.0),
        6.0: (72.0, 75.0),
        5.5: (68.0, 72.0),
        5.0: (65.0, 68.0),
        4.5: (62.0, 65.0),
        4.0: (58.0, 62.0),
        3.5: (55.0, 58.0),
        3.0: (50.0, 55.0),
    }
    
    # 训练目标对应的强度推荐
    GOAL_INTENSITY_RECOMMENDATIONS: Dict[TrainingGoal, Dict[str, Any]] = {
        TrainingGoal.STRENGTH: {
            'rpe_range': (8.0, 9.5),
            'percent_1rm_range': (85.0, 95.0),
            'rir_range': (0.5, 2.0),
            'rep_range': (1, 5),
            'set_range': (4, 6),
            'rest_seconds': (180, 300),
            'description': '力量训练：高强度、低次数、长休息',
        },
        TrainingGoal.HYPERTROPHY: {
            'rpe_range': (7.0, 9.0),
            'percent_1rm_range': (65.0, 85.0),
            'rir_range': (1.0, 3.0),
            'rep_range': (6, 12),
            'set_range': (3, 5),
            'rest_seconds': (60, 120),
            'description': '增肌训练：中等强度、中等次数、适中休息',
        },
        TrainingGoal.ENDURANCE: {
            'rpe_range': (5.0, 7.0),
            'percent_1rm_range': (50.0, 70.0),
            'rir_range': (3.0, 5.0),
            'rep_range': (12, 20),
            'set_range': (2, 4),
            'rest_seconds': (30, 60),
            'description': '耐力训练：低强度、高次数、短休息',
        },
        TrainingGoal.POWER: {
            'rpe_range': (7.0, 8.5),
            'percent_1rm_range': (50.0, 75.0),
            'rir_range': (1.5, 3.0),
            'rep_range': (3, 6),
            'set_range': (3, 5),
            'rest_seconds': (120, 180),
            'description': '爆发力训练：中等强度、低次数、充分休息',
        },
    }
    
    # RPE描述映射
    RPE_DESCRIPTIONS: Dict[int, str] = {
        10: "力竭 - 无法再完成一次",
        9: "非常困难 - 可能还能做1次",
        8: "困难 - 可能还能做2次",
        7: "有挑战 - 可能还能做3次",
        6: "中等 - 可能还能做4次",
        5: "轻松 - 可能还能做5次以上",
        4: "很轻松 - 热身强度",
        3: "非常轻松 - 恢复强度",
    }
    
    # 转换容差
    RPE_TOLERANCE = 0.5
    PERCENT_1RM_TOLERANCE = 2.0
    RIR_TOLERANCE = 0.5
    
    def __init__(self):
        """初始化强度转换器"""
        logger.info("IntensityConverter initialized")
    
    def _validate_rpe(self, rpe: float) -> float:
        """
        验证并规范化RPE值
        
        Args:
            rpe: RPE值
            
        Returns:
            float: 规范化后的RPE值（1-10）
            
        Raises:
            ValueError: 如果RPE值超出有效范围
        """
        if rpe < 1.0 or rpe > 10.0:
            raise ValueError(f"RPE值必须在1-10之间，当前值: {rpe}")
        return round(rpe * 2) / 2  # 四舍五入到0.5
    
    def _validate_percent_1rm(self, percent: float) -> float:
        """
        验证并规范化%1RM值
        
        Args:
            percent: %1RM值
            
        Returns:
            float: 规范化后的%1RM值（0-100）
            
        Raises:
            ValueError: 如果%1RM值超出有效范围
        """
        if percent < 0.0 or percent > 100.0:
            raise ValueError(f"%1RM值必须在0-100之间，当前值: {percent}")
        return round(percent, 1)
    
    def _validate_rir(self, rir: float) -> float:
        """
        验证并规范化RIR值
        
        Args:
            rir: RIR值
            
        Returns:
            float: 规范化后的RIR值（0-5+）
            
        Raises:
            ValueError: 如果RIR值为负数
        """
        if rir < 0.0:
            raise ValueError(f"RIR值不能为负数，当前值: {rir}")
        return min(round(rir * 2) / 2, 5.0)  # 四舍五入到0.5，最大5
    
    def _get_rpe_description(self, rpe: float) -> str:
        """获取RPE描述"""
        rpe_int = int(round(rpe))
        return self.RPE_DESCRIPTIONS.get(rpe_int, f"RPE {rpe}")
    
    def rpe_to_rir(self, rpe: float) -> IntensityConversionResult:
        """
        将RPE转换为RIR
        
        转换公式: RIR = 10 - RPE
        
        Args:
            rpe: RPE值（1-10）
            
        Returns:
            IntensityConversionResult: 转换结果
            
        Requirements: 10.5 - 强度指标转换
        """
        rpe = self._validate_rpe(rpe)
        rir = 10.0 - rpe
        rir = self._validate_rir(rir)
        
        source = IntensityValue(
            metric=IntensityMetric.RPE,
            value=rpe,
            description=self._get_rpe_description(rpe)
        )
        
        target = IntensityValue(
            metric=IntensityMetric.RIR,
            value=rir,
            description=f"储备{rir}次" if rir > 0 else "力竭"
        )
        
        logger.debug(f"RPE {rpe} -> RIR {rir}")
        
        return IntensityConversionResult(
            source=source,
            target=target,
            tolerance=self.RIR_TOLERANCE,
            notes=f"RPE {rpe} 约等于 RIR {rir}"
        )
    
    def rir_to_rpe(self, rir: float) -> IntensityConversionResult:
        """
        将RIR转换为RPE
        
        转换公式: RPE = 10 - RIR
        
        Args:
            rir: RIR值（0-5+）
            
        Returns:
            IntensityConversionResult: 转换结果
            
        Requirements: 10.5 - 强度指标转换
        """
        rir = self._validate_rir(rir)
        rpe = 10.0 - rir
        rpe = self._validate_rpe(rpe)
        
        source = IntensityValue(
            metric=IntensityMetric.RIR,
            value=rir,
            description=f"储备{rir}次" if rir > 0 else "力竭"
        )
        
        target = IntensityValue(
            metric=IntensityMetric.RPE,
            value=rpe,
            description=self._get_rpe_description(rpe)
        )
        
        logger.debug(f"RIR {rir} -> RPE {rpe}")
        
        return IntensityConversionResult(
            source=source,
            target=target,
            tolerance=self.RPE_TOLERANCE,
            notes=f"RIR {rir} 约等于 RPE {rpe}"
        )
    
    def rpe_to_percent_1rm(self, rpe: float) -> IntensityConversionResult:
        """
        将RPE转换为%1RM
        
        基于研究数据的近似转换，返回范围的中值。
        
        Args:
            rpe: RPE值（1-10）
            
        Returns:
            IntensityConversionResult: 转换结果
            
        Requirements: 10.5 - 强度指标转换
        """
        rpe = self._validate_rpe(rpe)
        
        # 查找最接近的RPE值
        closest_rpe = min(self.RPE_TO_PERCENT_1RM_MAP.keys(), 
                         key=lambda x: abs(x - rpe))
        percent_range = self.RPE_TO_PERCENT_1RM_MAP[closest_rpe]
        percent_1rm = (percent_range[0] + percent_range[1]) / 2
        
        source = IntensityValue(
            metric=IntensityMetric.RPE,
            value=rpe,
            description=self._get_rpe_description(rpe)
        )
        
        target = IntensityValue(
            metric=IntensityMetric.PERCENT_1RM,
            value=percent_1rm,
            description=f"{percent_1rm:.0f}% 1RM ({percent_range[0]:.0f}-{percent_range[1]:.0f}%)"
        )
        
        logger.debug(f"RPE {rpe} -> {percent_1rm:.1f}% 1RM")
        
        return IntensityConversionResult(
            source=source,
            target=target,
            tolerance=self.PERCENT_1RM_TOLERANCE,
            notes=f"RPE {rpe} 约等于 {percent_range[0]:.0f}-{percent_range[1]:.0f}% 1RM"
        )
    
    def percent_1rm_to_rpe(self, percent: float) -> IntensityConversionResult:
        """
        将%1RM转换为RPE
        
        基于研究数据的近似转换。
        
        Args:
            percent: %1RM值（0-100）
            
        Returns:
            IntensityConversionResult: 转换结果
            
        Requirements: 10.5 - 强度指标转换
        """
        percent = self._validate_percent_1rm(percent)
        
        # 查找对应的RPE范围
        rpe = 5.0  # 默认值
        for rpe_val, (low, high) in sorted(
            self.RPE_TO_PERCENT_1RM_MAP.items(), 
            key=lambda x: x[0], 
            reverse=True
        ):
            if low <= percent <= high:
                rpe = rpe_val
                break
            elif percent > high:
                rpe = rpe_val
                break
        
        source = IntensityValue(
            metric=IntensityMetric.PERCENT_1RM,
            value=percent,
            description=f"{percent:.0f}% 1RM"
        )
        
        target = IntensityValue(
            metric=IntensityMetric.RPE,
            value=rpe,
            description=self._get_rpe_description(rpe)
        )
        
        logger.debug(f"{percent:.1f}% 1RM -> RPE {rpe}")
        
        return IntensityConversionResult(
            source=source,
            target=target,
            tolerance=self.RPE_TOLERANCE,
            notes=f"{percent:.0f}% 1RM 约等于 RPE {rpe}"
        )
    
    def rir_to_percent_1rm(self, rir: float) -> IntensityConversionResult:
        """
        将RIR转换为%1RM
        
        通过RIR -> RPE -> %1RM的链式转换。
        
        Args:
            rir: RIR值（0-5+）
            
        Returns:
            IntensityConversionResult: 转换结果
            
        Requirements: 10.5 - 强度指标转换
        """
        # RIR -> RPE
        rpe_result = self.rir_to_rpe(rir)
        rpe = rpe_result.target.value
        
        # RPE -> %1RM
        percent_result = self.rpe_to_percent_1rm(rpe)
        
        source = IntensityValue(
            metric=IntensityMetric.RIR,
            value=rir,
            description=f"储备{rir}次" if rir > 0 else "力竭"
        )
        
        logger.debug(f"RIR {rir} -> {percent_result.target.value:.1f}% 1RM")
        
        return IntensityConversionResult(
            source=source,
            target=percent_result.target,
            tolerance=self.PERCENT_1RM_TOLERANCE + self.RPE_TOLERANCE,
            notes=f"RIR {rir} -> RPE {rpe} -> {percent_result.target.value:.0f}% 1RM"
        )
    
    def percent_1rm_to_rir(self, percent: float) -> IntensityConversionResult:
        """
        将%1RM转换为RIR
        
        通过%1RM -> RPE -> RIR的链式转换。
        
        Args:
            percent: %1RM值（0-100）
            
        Returns:
            IntensityConversionResult: 转换结果
            
        Requirements: 10.5 - 强度指标转换
        """
        # %1RM -> RPE
        rpe_result = self.percent_1rm_to_rpe(percent)
        rpe = rpe_result.target.value
        
        # RPE -> RIR
        rir_result = self.rpe_to_rir(rpe)
        
        source = IntensityValue(
            metric=IntensityMetric.PERCENT_1RM,
            value=percent,
            description=f"{percent:.0f}% 1RM"
        )
        
        logger.debug(f"{percent:.1f}% 1RM -> RIR {rir_result.target.value}")
        
        return IntensityConversionResult(
            source=source,
            target=rir_result.target,
            tolerance=self.RIR_TOLERANCE + self.RPE_TOLERANCE,
            notes=f"{percent:.0f}% 1RM -> RPE {rpe} -> RIR {rir_result.target.value}"
        )

    
    def convert(
        self,
        value: float,
        from_metric: IntensityMetric,
        to_metric: IntensityMetric
    ) -> IntensityConversionResult:
        """
        通用强度指标转换方法
        
        Args:
            value: 源强度值
            from_metric: 源指标类型
            to_metric: 目标指标类型
            
        Returns:
            IntensityConversionResult: 转换结果
            
        Raises:
            ValueError: 如果指标类型无效
            
        Requirements: 10.5 - 强度指标转换
        """
        if from_metric == to_metric:
            # 相同指标，直接返回
            if from_metric == IntensityMetric.RPE:
                value = self._validate_rpe(value)
                desc = self._get_rpe_description(value)
            elif from_metric == IntensityMetric.PERCENT_1RM:
                value = self._validate_percent_1rm(value)
                desc = f"{value:.0f}% 1RM"
            else:
                value = self._validate_rir(value)
                desc = f"储备{value}次" if value > 0 else "力竭"
            
            intensity_value = IntensityValue(
                metric=from_metric,
                value=value,
                description=desc
            )
            return IntensityConversionResult(
                source=intensity_value,
                target=intensity_value,
                tolerance=0.0,
                notes="相同指标，无需转换"
            )
        
        # 转换映射
        conversion_map = {
            (IntensityMetric.RPE, IntensityMetric.RIR): self.rpe_to_rir,
            (IntensityMetric.RPE, IntensityMetric.PERCENT_1RM): self.rpe_to_percent_1rm,
            (IntensityMetric.RIR, IntensityMetric.RPE): self.rir_to_rpe,
            (IntensityMetric.RIR, IntensityMetric.PERCENT_1RM): self.rir_to_percent_1rm,
            (IntensityMetric.PERCENT_1RM, IntensityMetric.RPE): self.percent_1rm_to_rpe,
            (IntensityMetric.PERCENT_1RM, IntensityMetric.RIR): self.percent_1rm_to_rir,
        }
        
        converter = conversion_map.get((from_metric, to_metric))
        if not converter:
            raise ValueError(f"不支持的转换: {from_metric.value} -> {to_metric.value}")
        
        return converter(value)
    
    def convert_all(
        self,
        value: float,
        from_metric: IntensityMetric
    ) -> Dict[IntensityMetric, IntensityConversionResult]:
        """
        将一个强度值转换为所有其他指标
        
        Args:
            value: 源强度值
            from_metric: 源指标类型
            
        Returns:
            Dict[IntensityMetric, IntensityConversionResult]: 所有转换结果
            
        Requirements: 10.5 - 强度指标转换
        """
        results = {}
        for target_metric in IntensityMetric:
            results[target_metric] = self.convert(value, from_metric, target_metric)
        return results
    
    def get_intensity_recommendation(
        self,
        goal: TrainingGoal,
        preferred_metric: IntensityMetric = IntensityMetric.RPE
    ) -> IntensityRecommendation:
        """
        根据训练目标获取强度推荐
        
        Args:
            goal: 训练目标
            preferred_metric: 用户偏好的强度指标
            
        Returns:
            IntensityRecommendation: 强度推荐结果
            
        Requirements: 10.4 - 用户指定偏好强度指标
        """
        config = self.GOAL_INTENSITY_RECOMMENDATIONS.get(goal)
        if not config:
            raise ValueError(f"不支持的训练目标: {goal.value}")
        
        # 计算各指标的中值
        rpe_mid = (config['rpe_range'][0] + config['rpe_range'][1]) / 2
        percent_1rm_mid = (config['percent_1rm_range'][0] + config['percent_1rm_range'][1]) / 2
        rir_mid = (config['rir_range'][0] + config['rir_range'][1]) / 2
        
        rpe_value = IntensityValue(
            metric=IntensityMetric.RPE,
            value=rpe_mid,
            description=f"RPE {config['rpe_range'][0]}-{config['rpe_range'][1]}"
        )
        
        percent_1rm_value = IntensityValue(
            metric=IntensityMetric.PERCENT_1RM,
            value=percent_1rm_mid,
            description=f"{config['percent_1rm_range'][0]:.0f}-{config['percent_1rm_range'][1]:.0f}% 1RM"
        )
        
        rir_value = IntensityValue(
            metric=IntensityMetric.RIR,
            value=rir_mid,
            description=f"RIR {config['rir_range'][0]}-{config['rir_range'][1]}"
        )
        
        recommendation = IntensityRecommendation(
            goal=goal,
            rpe=rpe_value,
            percent_1rm=percent_1rm_value,
            rir=rir_value,
            rep_range=config['rep_range'],
            set_range=config['set_range'],
            rest_seconds=config['rest_seconds'],
            notes=config['description']
        )
        
        logger.info(
            f"强度推荐: goal={goal.value}, "
            f"RPE={rpe_mid}, %1RM={percent_1rm_mid:.0f}%, RIR={rir_mid}",
            extra={'goal': goal.value, 'recommendation': recommendation.to_dict()}
        )
        
        return recommendation
    
    def validate_round_trip(
        self,
        value: float,
        metric: IntensityMetric,
        tolerance: Optional[float] = None
    ) -> Tuple[bool, float, str]:
        """
        验证往返转换的一致性
        
        将值转换到另一个指标再转换回来，检查误差是否在容差范围内。
        
        Args:
            value: 原始值
            metric: 指标类型
            tolerance: 容差（可选，默认使用指标对应的容差）
            
        Returns:
            Tuple[bool, float, str]: (是否通过, 误差值, 说明)
            
        Requirements: 10.5 - 强度指标转换一致性
        """
        # 确定中间指标
        if metric == IntensityMetric.RPE:
            intermediate = IntensityMetric.RIR
            default_tolerance = self.RPE_TOLERANCE
        elif metric == IntensityMetric.RIR:
            intermediate = IntensityMetric.RPE
            default_tolerance = self.RIR_TOLERANCE
        else:  # PERCENT_1RM
            intermediate = IntensityMetric.RPE
            default_tolerance = self.PERCENT_1RM_TOLERANCE
        
        tolerance = tolerance or default_tolerance
        
        # 往返转换
        to_intermediate = self.convert(value, metric, intermediate)
        back_to_original = self.convert(
            to_intermediate.target.value, 
            intermediate, 
            metric
        )
        
        # 计算误差
        error = abs(back_to_original.target.value - value)
        passed = error <= tolerance
        
        message = (
            f"{metric.value} {value} -> {intermediate.value} "
            f"{to_intermediate.target.value} -> {metric.value} "
            f"{back_to_original.target.value} (误差: {error:.2f}, "
            f"容差: {tolerance}, {'通过' if passed else '未通过'})"
        )
        
        logger.debug(f"往返验证: {message}")
        
        return passed, error, message
    
    def format_intensity(
        self,
        value: float,
        metric: IntensityMetric,
        include_equivalents: bool = True
    ) -> str:
        """
        格式化强度值为用户友好的字符串
        
        Args:
            value: 强度值
            metric: 指标类型
            include_equivalents: 是否包含等效值
            
        Returns:
            str: 格式化后的字符串
        """
        if metric == IntensityMetric.RPE:
            value = self._validate_rpe(value)
            base = f"RPE {value} ({self._get_rpe_description(value)})"
            if include_equivalents:
                rir = self.rpe_to_rir(value).target.value
                percent = self.rpe_to_percent_1rm(value).target.value
                return f"{base} ≈ RIR {rir} ≈ {percent:.0f}% 1RM"
            return base
            
        elif metric == IntensityMetric.RIR:
            value = self._validate_rir(value)
            base = f"RIR {value}" if value > 0 else "力竭 (RIR 0)"
            if include_equivalents:
                rpe = self.rir_to_rpe(value).target.value
                percent = self.rir_to_percent_1rm(value).target.value
                return f"{base} ≈ RPE {rpe} ≈ {percent:.0f}% 1RM"
            return base
            
        else:  # PERCENT_1RM
            value = self._validate_percent_1rm(value)
            base = f"{value:.0f}% 1RM"
            if include_equivalents:
                rpe = self.percent_1rm_to_rpe(value).target.value
                rir = self.percent_1rm_to_rir(value).target.value
                return f"{base} ≈ RPE {rpe} ≈ RIR {rir}"
            return base
    
    def get_intensity_for_reps(
        self,
        target_reps: int,
        goal: TrainingGoal = TrainingGoal.HYPERTROPHY
    ) -> Dict[str, Any]:
        """
        根据目标次数推荐强度
        
        基于Prilepin's Chart和现代研究数据。
        
        Args:
            target_reps: 目标次数
            goal: 训练目标
            
        Returns:
            Dict[str, Any]: 推荐的强度参数
        """
        # 基于次数的%1RM估算（Epley公式的逆推）
        # 1RM = weight × (1 + reps/30)
        # 因此 %1RM ≈ 100 / (1 + reps/30)
        estimated_percent = 100 / (1 + target_reps / 30)
        
        # 根据训练目标调整
        goal_adjustments = {
            TrainingGoal.STRENGTH: 5.0,      # 力量训练用更重的重量
            TrainingGoal.HYPERTROPHY: 0.0,   # 增肌训练标准
            TrainingGoal.ENDURANCE: -5.0,    # 耐力训练用更轻的重量
            TrainingGoal.POWER: -10.0,       # 爆发力训练用更轻的重量（速度优先）
        }
        
        adjusted_percent = estimated_percent + goal_adjustments.get(goal, 0.0)
        adjusted_percent = max(30.0, min(100.0, adjusted_percent))
        
        # 转换为其他指标
        rpe_result = self.percent_1rm_to_rpe(adjusted_percent)
        rir_result = self.percent_1rm_to_rir(adjusted_percent)
        
        return {
            'target_reps': target_reps,
            'goal': goal.value,
            'percent_1rm': round(adjusted_percent, 1),
            'rpe': rpe_result.target.value,
            'rir': rir_result.target.value,
            'notes': f"目标{target_reps}次，{goal.value}训练，建议使用{adjusted_percent:.0f}% 1RM"
        }


# 单例实例
_intensity_converter_instance: Optional[IntensityConverter] = None


def get_intensity_converter() -> IntensityConverter:
    """
    获取IntensityConverter单例实例
    
    Returns:
        IntensityConverter: 强度转换器实例
    """
    global _intensity_converter_instance
    if _intensity_converter_instance is None:
        _intensity_converter_instance = IntensityConverter()
    return _intensity_converter_instance


def reset_intensity_converter() -> None:
    """重置IntensityConverter单例实例（用于测试）"""
    global _intensity_converter_instance
    _intensity_converter_instance = None
