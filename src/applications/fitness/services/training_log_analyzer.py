# -*- coding: utf-8 -*-
"""
Training Log Analyzer Service

训练日志分析服务，用于闭环学习系统的数据分析。
通过BackendClient读取Laravel后端的训练日志数据，
为容量调整和计划生成提供智能分析支持。

Requirements: 7.1 - 分析中周期训练表现

作者: BUILD_BODY Team
版本: 1.0.0
日期: 2025-12-26
"""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class TrendDirection(str, Enum):
    """趋势方向"""
    IMPROVING = "improving"      # 改善中
    STABLE = "stable"            # 稳定
    DECLINING = "declining"      # 下降中
    INSUFFICIENT_DATA = "insufficient_data"  # 数据不足


@dataclass
class CompletionTrendAnalysis:
    """完成率趋势分析结果"""
    direction: TrendDirection
    avg_completion_rate: float
    recent_completion_rate: float  # 最近一周
    trend_change: float  # 变化幅度（正数表示改善）
    weeks_analyzed: int
    recommendation: str


@dataclass
class RPETrendAnalysis:
    """RPE趋势分析结果"""
    direction: TrendDirection
    avg_rpe: float
    recent_rpe: float  # 最近一周
    trend_change: float  # 变化幅度（正数表示RPE上升）
    weeks_analyzed: int
    fatigue_warning: bool  # 是否有疲劳警告
    recommendation: str


@dataclass
class MesocycleAnalysis:
    """中周期分析结果"""
    user_id: int
    mesocycle_weeks: int
    total_sessions: int
    avg_completion_rate: float
    avg_rpe: float
    completion_trend: CompletionTrendAnalysis
    rpe_trend: RPETrendAnalysis
    volume_adjustment_suggestion: float  # 建议的容量调整值
    should_deload: bool
    deload_reason: Optional[str]
    analysis_date: str


class TrainingLogAnalyzer:
    """
    训练日志分析服务
    
    通过BackendClient读取用户训练日志，提供：
    - 训练历史获取
    - 完成率趋势分析
    - RPE趋势分析
    - 中周期综合分析
    
    用于容量动态调整和计划生成的智能决策支持。
    
    Requirements: 7.1 - 分析中周期训练表现
    """
    
    # 分析阈值配置
    MIN_SESSIONS_FOR_ANALYSIS = 3  # 最少需要3次训练才能分析
    HIGH_RPE_THRESHOLD = 9.0       # 高RPE阈值
    LOW_COMPLETION_THRESHOLD = 0.80  # 低完成率阈值
    HIGH_COMPLETION_THRESHOLD = 0.95  # 高完成率阈值
    OPTIMAL_RPE_RANGE = (6.5, 8.5)   # 最佳RPE范围
    
    def __init__(self, backend_client):
        """
        初始化训练日志分析器
        
        Args:
            backend_client: BackendClient实例，用于访问Laravel后端API
        """
        self.backend_client = backend_client
        logger.info("TrainingLogAnalyzer initialized")
    
    async def get_user_training_history(
        self,
        user_id: int,
        days_back: int = 42,  # 默认6周
        mesocycle_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        获取用户训练历史
        
        Args:
            user_id: 用户ID
            days_back: 回溯天数，默认42天（6周）
            mesocycle_id: 可选的中周期ID筛选
            
        Returns:
            List[Dict]: 训练日志列表
            
        Requirements: 7.1 - 获取用户训练数据用于分析
        """
        try:
            # 计算日期范围
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
            
            # 调用BackendClient获取训练日志
            logs = await self.backend_client.get_training_logs(
                user_id=user_id,
                start_date=start_date,
                end_date=end_date,
                mesocycle_id=mesocycle_id
            )
            
            logger.info(
                f"获取用户训练历史: user_id={user_id}, "
                f"days_back={days_back}, logs_count={len(logs)}",
                extra={
                    'user_id': user_id,
                    'days_back': days_back,
                    'logs_count': len(logs)
                }
            )
            
            return logs
            
        except Exception as e:
            logger.error(f"获取训练历史失败: user_id={user_id}, error={e}")
            return []
    
    async def analyze_completion_trend(
        self,
        user_id: int,
        weeks: int = 4
    ) -> CompletionTrendAnalysis:
        """
        分析完成率趋势
        
        Args:
            user_id: 用户ID
            weeks: 分析周数，默认4周
            
        Returns:
            CompletionTrendAnalysis: 完成率趋势分析结果
            
        Requirements: 7.1 - 分析完成率趋势用于容量调整
        """
        try:
            # 获取训练历史
            logs = await self.get_user_training_history(
                user_id=user_id,
                days_back=weeks * 7
            )
            
            if len(logs) < self.MIN_SESSIONS_FOR_ANALYSIS:
                return CompletionTrendAnalysis(
                    direction=TrendDirection.INSUFFICIENT_DATA,
                    avg_completion_rate=0.0,
                    recent_completion_rate=0.0,
                    trend_change=0.0,
                    weeks_analyzed=0,
                    recommendation="训练数据不足，建议继续记录训练日志"
                )
            
            # 提取完成率数据
            completion_rates = [
                log.get('completion_rate', 0.0) 
                for log in logs 
                if log.get('completion_rate') is not None
            ]
            
            if not completion_rates:
                return CompletionTrendAnalysis(
                    direction=TrendDirection.INSUFFICIENT_DATA,
                    avg_completion_rate=0.0,
                    recent_completion_rate=0.0,
                    trend_change=0.0,
                    weeks_analyzed=0,
                    recommendation="没有有效的完成率数据"
                )
            
            # 计算平均完成率
            avg_rate = sum(completion_rates) / len(completion_rates)
            
            # 计算最近一周的完成率（取最近的记录）
            recent_count = min(3, len(completion_rates))
            recent_rates = completion_rates[:recent_count]  # 假设按日期降序
            recent_rate = sum(recent_rates) / len(recent_rates)
            
            # 计算早期完成率（用于趋势比较）
            if len(completion_rates) > recent_count:
                early_rates = completion_rates[recent_count:]
                early_rate = sum(early_rates) / len(early_rates)
                trend_change = recent_rate - early_rate
            else:
                trend_change = 0.0
            
            # 判断趋势方向
            if abs(trend_change) < 0.05:
                direction = TrendDirection.STABLE
            elif trend_change > 0:
                direction = TrendDirection.IMPROVING
            else:
                direction = TrendDirection.DECLINING
            
            # 生成建议
            recommendation = self._generate_completion_recommendation(
                avg_rate, recent_rate, direction
            )
            
            result = CompletionTrendAnalysis(
                direction=direction,
                avg_completion_rate=round(avg_rate, 2),
                recent_completion_rate=round(recent_rate, 2),
                trend_change=round(trend_change, 3),
                weeks_analyzed=weeks,
                recommendation=recommendation
            )
            
            logger.info(
                f"完成率趋势分析完成: user_id={user_id}, "
                f"avg={avg_rate:.2f}, direction={direction.value}",
                extra={
                    'user_id': user_id,
                    'avg_completion_rate': avg_rate,
                    'direction': direction.value
                }
            )
            
            return result
            
        except Exception as e:
            logger.error(f"完成率趋势分析失败: user_id={user_id}, error={e}")
            return CompletionTrendAnalysis(
                direction=TrendDirection.INSUFFICIENT_DATA,
                avg_completion_rate=0.0,
                recent_completion_rate=0.0,
                trend_change=0.0,
                weeks_analyzed=0,
                recommendation=f"分析失败: {str(e)}"
            )
    
    async def analyze_rpe_trend(
        self,
        user_id: int,
        weeks: int = 4
    ) -> RPETrendAnalysis:
        """
        分析RPE趋势
        
        Args:
            user_id: 用户ID
            weeks: 分析周数，默认4周
            
        Returns:
            RPETrendAnalysis: RPE趋势分析结果
            
        Requirements: 7.1 - 分析RPE趋势用于容量调整
        """
        try:
            # 获取训练历史
            logs = await self.get_user_training_history(
                user_id=user_id,
                days_back=weeks * 7
            )
            
            if len(logs) < self.MIN_SESSIONS_FOR_ANALYSIS:
                return RPETrendAnalysis(
                    direction=TrendDirection.INSUFFICIENT_DATA,
                    avg_rpe=0.0,
                    recent_rpe=0.0,
                    trend_change=0.0,
                    weeks_analyzed=0,
                    fatigue_warning=False,
                    recommendation="训练数据不足，建议继续记录训练日志"
                )
            
            # 提取RPE数据
            rpe_values = [
                log.get('avg_rpe', 0.0) 
                for log in logs 
                if log.get('avg_rpe') is not None and log.get('avg_rpe') > 0
            ]
            
            if not rpe_values:
                return RPETrendAnalysis(
                    direction=TrendDirection.INSUFFICIENT_DATA,
                    avg_rpe=0.0,
                    recent_rpe=0.0,
                    trend_change=0.0,
                    weeks_analyzed=0,
                    fatigue_warning=False,
                    recommendation="没有有效的RPE数据"
                )
            
            # 计算平均RPE
            avg_rpe = sum(rpe_values) / len(rpe_values)
            
            # 计算最近的RPE
            recent_count = min(3, len(rpe_values))
            recent_rpes = rpe_values[:recent_count]
            recent_rpe = sum(recent_rpes) / len(recent_rpes)
            
            # 计算早期RPE（用于趋势比较）
            if len(rpe_values) > recent_count:
                early_rpes = rpe_values[recent_count:]
                early_rpe = sum(early_rpes) / len(early_rpes)
                trend_change = recent_rpe - early_rpe
            else:
                trend_change = 0.0
            
            # 判断趋势方向（RPE上升可能表示疲劳累积）
            if abs(trend_change) < 0.3:
                direction = TrendDirection.STABLE
            elif trend_change > 0:
                direction = TrendDirection.DECLINING  # RPE上升表示状态下降
            else:
                direction = TrendDirection.IMPROVING  # RPE下降表示状态改善
            
            # 检查疲劳警告
            fatigue_warning = recent_rpe > self.HIGH_RPE_THRESHOLD
            
            # 生成建议
            recommendation = self._generate_rpe_recommendation(
                avg_rpe, recent_rpe, direction, fatigue_warning
            )
            
            result = RPETrendAnalysis(
                direction=direction,
                avg_rpe=round(avg_rpe, 1),
                recent_rpe=round(recent_rpe, 1),
                trend_change=round(trend_change, 2),
                weeks_analyzed=weeks,
                fatigue_warning=fatigue_warning,
                recommendation=recommendation
            )
            
            logger.info(
                f"RPE趋势分析完成: user_id={user_id}, "
                f"avg={avg_rpe:.1f}, direction={direction.value}, "
                f"fatigue_warning={fatigue_warning}",
                extra={
                    'user_id': user_id,
                    'avg_rpe': avg_rpe,
                    'direction': direction.value,
                    'fatigue_warning': fatigue_warning
                }
            )
            
            return result
            
        except Exception as e:
            logger.error(f"RPE趋势分析失败: user_id={user_id}, error={e}")
            return RPETrendAnalysis(
                direction=TrendDirection.INSUFFICIENT_DATA,
                avg_rpe=0.0,
                recent_rpe=0.0,
                trend_change=0.0,
                weeks_analyzed=0,
                fatigue_warning=False,
                recommendation=f"分析失败: {str(e)}"
            )
    
    async def analyze_mesocycle(
        self,
        user_id: int,
        mesocycle_weeks: int = 4
    ) -> MesocycleAnalysis:
        """
        分析中周期训练表现
        
        综合分析用户在一个中周期（4-6周）内的训练表现，
        为容量调整提供决策依据。
        
        Args:
            user_id: 用户ID
            mesocycle_weeks: 中周期周数，默认4周
            
        Returns:
            MesocycleAnalysis: 中周期综合分析结果
            
        Requirements: 7.1 - 分析中周期训练表现
        """
        try:
            # 获取训练历史
            logs = await self.get_user_training_history(
                user_id=user_id,
                days_back=mesocycle_weeks * 7
            )
            
            # 分析完成率趋势
            completion_trend = await self.analyze_completion_trend(
                user_id=user_id,
                weeks=mesocycle_weeks
            )
            
            # 分析RPE趋势
            rpe_trend = await self.analyze_rpe_trend(
                user_id=user_id,
                weeks=mesocycle_weeks
            )
            
            # 计算综合指标
            total_sessions = len(logs)
            avg_completion = completion_trend.avg_completion_rate
            avg_rpe = rpe_trend.avg_rpe
            
            # 计算容量调整建议
            volume_adjustment = self._calculate_volume_adjustment(
                avg_completion, avg_rpe, completion_trend, rpe_trend
            )
            
            # 判断是否需要Deload
            should_deload, deload_reason = self._check_deload_needed(
                avg_rpe, avg_completion, rpe_trend
            )
            
            result = MesocycleAnalysis(
                user_id=user_id,
                mesocycle_weeks=mesocycle_weeks,
                total_sessions=total_sessions,
                avg_completion_rate=avg_completion,
                avg_rpe=avg_rpe,
                completion_trend=completion_trend,
                rpe_trend=rpe_trend,
                volume_adjustment_suggestion=volume_adjustment,
                should_deload=should_deload,
                deload_reason=deload_reason,
                analysis_date=datetime.now().strftime('%Y-%m-%d')
            )
            
            logger.info(
                f"中周期分析完成: user_id={user_id}, "
                f"sessions={total_sessions}, "
                f"volume_adj={volume_adjustment:+.2f}, "
                f"should_deload={should_deload}",
                extra={
                    'user_id': user_id,
                    'total_sessions': total_sessions,
                    'volume_adjustment': volume_adjustment,
                    'should_deload': should_deload
                }
            )
            
            return result
            
        except Exception as e:
            logger.error(f"中周期分析失败: user_id={user_id}, error={e}")
            # 返回默认分析结果
            return MesocycleAnalysis(
                user_id=user_id,
                mesocycle_weeks=mesocycle_weeks,
                total_sessions=0,
                avg_completion_rate=0.0,
                avg_rpe=0.0,
                completion_trend=CompletionTrendAnalysis(
                    direction=TrendDirection.INSUFFICIENT_DATA,
                    avg_completion_rate=0.0,
                    recent_completion_rate=0.0,
                    trend_change=0.0,
                    weeks_analyzed=0,
                    recommendation=f"分析失败: {str(e)}"
                ),
                rpe_trend=RPETrendAnalysis(
                    direction=TrendDirection.INSUFFICIENT_DATA,
                    avg_rpe=0.0,
                    recent_rpe=0.0,
                    trend_change=0.0,
                    weeks_analyzed=0,
                    fatigue_warning=False,
                    recommendation=f"分析失败: {str(e)}"
                ),
                volume_adjustment_suggestion=0.0,
                should_deload=False,
                deload_reason=None,
                analysis_date=datetime.now().strftime('%Y-%m-%d')
            )
    
    def _calculate_volume_adjustment(
        self,
        avg_completion: float,
        avg_rpe: float,
        completion_trend: CompletionTrendAnalysis,
        rpe_trend: RPETrendAnalysis
    ) -> float:
        """
        计算容量调整建议值
        
        Requirements: 7.2, 7.3 - 根据RPE和完成率计算容量调整
        
        调整规则：
        - RPE < 7 且 完成率 > 95%: +0.05 ~ +0.1
        - RPE > 9.5 或 完成率 < 80%: -0.1 ~ -0.15
        - 其他情况: 保持不变或微调
        """
        adjustment = 0.0
        
        # 检查是否数据不足
        if completion_trend.direction == TrendDirection.INSUFFICIENT_DATA:
            return 0.0
        
        # 规则1: RPE < 7 且 完成率 > 95% -> 上调容量
        if avg_rpe < 7.0 and avg_completion > self.HIGH_COMPLETION_THRESHOLD:
            # 根据具体数值计算调整幅度
            rpe_factor = (7.0 - avg_rpe) / 7.0  # RPE越低，调整越大
            completion_factor = (avg_completion - 0.95) / 0.05  # 完成率越高，调整越大
            adjustment = 0.05 + 0.05 * min(rpe_factor, completion_factor)
            adjustment = min(adjustment, 0.1)  # 上限0.1
            
        # 规则2: RPE > 9.5 或 完成率 < 80% -> 下调容量
        elif avg_rpe > 9.5 or avg_completion < self.LOW_COMPLETION_THRESHOLD:
            if avg_rpe > 9.5:
                rpe_factor = (avg_rpe - 9.5) / 0.5  # RPE越高，调整越大
                adjustment = -0.1 - 0.05 * min(rpe_factor, 1.0)
            if avg_completion < self.LOW_COMPLETION_THRESHOLD:
                completion_factor = (0.80 - avg_completion) / 0.20
                completion_adj = -0.1 - 0.05 * min(completion_factor, 1.0)
                adjustment = min(adjustment, completion_adj)  # 取更大的下调
            adjustment = max(adjustment, -0.15)  # 下限-0.15
            
        # 规则3: 趋势调整
        elif completion_trend.direction == TrendDirection.IMPROVING and avg_rpe < 8.0:
            adjustment = 0.02  # 小幅上调
        elif rpe_trend.fatigue_warning:
            adjustment = -0.05  # 疲劳警告时小幅下调
        
        return round(adjustment, 2)
    
    def _check_deload_needed(
        self,
        avg_rpe: float,
        avg_completion: float,
        rpe_trend: RPETrendAnalysis
    ) -> tuple[bool, Optional[str]]:
        """
        检查是否需要Deload周
        
        Requirements: 9.2 - 连续2周RPE>9或完成率<85%时提示Deload
        """
        reasons = []
        
        # 检查高RPE
        if avg_rpe > 9.0:
            reasons.append(f"平均RPE过高({avg_rpe:.1f})")
        
        # 检查低完成率
        if avg_completion < 0.85:
            reasons.append(f"完成率过低({avg_completion:.0%})")
        
        # 检查疲劳警告
        if rpe_trend.fatigue_warning:
            reasons.append("检测到疲劳累积")
        
        # 检查RPE持续上升趋势
        if rpe_trend.direction == TrendDirection.DECLINING and rpe_trend.trend_change > 1.0:
            reasons.append("RPE持续上升")
        
        should_deload = len(reasons) >= 2 or (avg_rpe > 9.5 and avg_completion < 0.85)
        deload_reason = "；".join(reasons) if reasons else None
        
        return should_deload, deload_reason
    
    def _generate_completion_recommendation(
        self,
        avg_rate: float,
        recent_rate: float,
        direction: TrendDirection
    ) -> str:
        """生成完成率相关建议"""
        if avg_rate > self.HIGH_COMPLETION_THRESHOLD:
            if direction == TrendDirection.STABLE:
                return "完成率优秀且稳定，可以考虑适当增加训练容量"
            return "完成率优秀，继续保持当前训练强度"
        elif avg_rate < self.LOW_COMPLETION_THRESHOLD:
            if direction == TrendDirection.DECLINING:
                return "完成率下降，建议降低训练容量或检查恢复情况"
            return "完成率偏低，建议适当降低训练强度"
        else:
            if direction == TrendDirection.IMPROVING:
                return "完成率正在改善，继续保持"
            return "完成率正常，保持当前训练计划"
    
    def _generate_rpe_recommendation(
        self,
        avg_rpe: float,
        recent_rpe: float,
        direction: TrendDirection,
        fatigue_warning: bool
    ) -> str:
        """生成RPE相关建议"""
        if fatigue_warning:
            return "⚠️ 检测到疲劳累积，建议安排减量周或增加休息"
        
        if avg_rpe < self.OPTIMAL_RPE_RANGE[0]:
            return "训练强度偏低，可以适当增加重量或组数"
        elif avg_rpe > self.OPTIMAL_RPE_RANGE[1]:
            if direction == TrendDirection.DECLINING:
                return "RPE持续上升，建议降低训练强度或增加休息"
            return "训练强度偏高，注意恢复"
        else:
            return "训练强度适中，继续保持"
