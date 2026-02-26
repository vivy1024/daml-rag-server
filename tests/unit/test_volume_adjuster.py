# -*- coding: utf-8 -*-
"""
Volume Adjuster Unit Tests

测试容量动态调整器的核心功能和属性测试。

Properties:
- Property 5: 容量调整边界约束 (Requirements 7.5)
- Property 6: 容量上调条件 (Requirements 7.2)
- Property 7: 容量下调条件 (Requirements 7.3)

作者: BUILD_BODY Team
版本: 1.0.0
日期: 2025-12-26
"""

import pytest
pytest.importorskip("hypothesis", reason="属性测试依赖 hypothesis（可选）")
from hypothesis import given, strategies as st, settings, assume
from typing import Dict, Any, Tuple
from unittest.mock import AsyncMock, MagicMock

from src.applications.fitness.services.volume_adjuster import (
    VolumeAdjuster,
    VolumeAdjustmentResult,
    AdjustmentDirection
)


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def mock_training_log_analyzer():
    """创建模拟的TrainingLogAnalyzer"""
    analyzer = MagicMock()
    return analyzer


@pytest.fixture
def mock_backend_client():
    """创建模拟的BackendClient"""
    client = MagicMock()
    client.get_user_profile = AsyncMock(return_value={
        'training_system': {
            'personal_volume_multiplier': 1.0
        }
    })
    client.update_volume_multiplier = AsyncMock(return_value={
        'success': True,
        'new_multiplier': 1.0
    })
    return client


@pytest.fixture
def volume_adjuster(mock_training_log_analyzer, mock_backend_client):
    """创建VolumeAdjuster实例"""
    return VolumeAdjuster(
        training_log_analyzer=mock_training_log_analyzer,
        backend_client=mock_backend_client
    )


# ============================================================================
# Hypothesis Strategies
# ============================================================================

# RPE值策略（1-10范围）
rpe_strategy = st.floats(min_value=1.0, max_value=10.0, allow_nan=False, allow_infinity=False)

# 完成率策略（0-1范围）
completion_rate_strategy = st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)

# 容量系数策略（任意浮点数，用于测试边界约束）
multiplier_strategy = st.floats(min_value=-1.0, max_value=3.0, allow_nan=False, allow_infinity=False)

# 有效容量系数策略（0.7-1.5范围内）
valid_multiplier_strategy = st.floats(min_value=0.7, max_value=1.5, allow_nan=False, allow_infinity=False)


# ============================================================================
# Unit Tests - Basic Functionality
# ============================================================================

class TestVolumeAdjusterBasic:
    """基础功能测试"""
    
    def test_init(self, volume_adjuster):
        """测试初始化"""
        assert volume_adjuster.MULTIPLIER_MIN == 0.7
        assert volume_adjuster.MULTIPLIER_MAX == 1.5
        assert volume_adjuster.LOW_RPE_THRESHOLD == 7.0
        assert volume_adjuster.HIGH_RPE_THRESHOLD == 9.5
    
    def test_clamp_multiplier_within_range(self, volume_adjuster):
        """测试范围内的值不变"""
        assert volume_adjuster.clamp_multiplier(1.0) == 1.0
        assert volume_adjuster.clamp_multiplier(0.7) == 0.7
        assert volume_adjuster.clamp_multiplier(1.5) == 1.5
        assert volume_adjuster.clamp_multiplier(1.2) == 1.2
    
    def test_clamp_multiplier_below_min(self, volume_adjuster):
        """测试低于最小值被限制"""
        assert volume_adjuster.clamp_multiplier(0.5) == 0.7
        assert volume_adjuster.clamp_multiplier(0.0) == 0.7
        assert volume_adjuster.clamp_multiplier(-1.0) == 0.7
    
    def test_clamp_multiplier_above_max(self, volume_adjuster):
        """测试高于最大值被限制"""
        assert volume_adjuster.clamp_multiplier(1.6) == 1.5
        assert volume_adjuster.clamp_multiplier(2.0) == 1.5
        assert volume_adjuster.clamp_multiplier(10.0) == 1.5
    
    def test_calculate_adjustment_maintain(self, volume_adjuster):
        """测试保持不变的情况"""
        # RPE和完成率都在正常范围
        adjustment, direction, reason = volume_adjuster.calculate_adjustment(
            avg_rpe=7.5,
            avg_completion_rate=0.90,
            current_multiplier=1.0
        )
        
        assert direction == AdjustmentDirection.MAINTAIN
        assert adjustment == 0.0
    
    def test_should_suggest_deload_false(self, volume_adjuster):
        """测试不需要Deload的情况"""
        should_deload, reason = volume_adjuster.should_suggest_deload(
            avg_rpe=7.0,
            avg_completion_rate=0.90
        )
        
        assert should_deload is False
        assert reason is None
    
    def test_should_suggest_deload_high_rpe(self, volume_adjuster):
        """测试高RPE触发Deload建议"""
        should_deload, reason = volume_adjuster.should_suggest_deload(
            avg_rpe=9.8,
            avg_completion_rate=0.90
        )
        
        assert should_deload is True
        assert 'RPE' in reason
    
    def test_should_suggest_deload_consecutive_high_rpe(self, volume_adjuster):
        """测试连续2周高RPE触发Deload建议 - Requirements 9.2"""
        should_deload, reason = volume_adjuster.should_suggest_deload(
            avg_rpe=9.2,
            avg_completion_rate=0.88,
            previous_week_rpe=9.3,
            previous_week_completion=0.87
        )
        
        assert should_deload is True
        assert '连续2' in reason and 'RPE过高' in reason
    
    def test_should_suggest_deload_consecutive_low_completion(self, volume_adjuster):
        """测试连续2周低完成率触发Deload建议 - Requirements 9.2"""
        should_deload, reason = volume_adjuster.should_suggest_deload(
            avg_rpe=8.0,
            avg_completion_rate=0.82,
            previous_week_rpe=8.0,
            previous_week_completion=0.80
        )
        
        assert should_deload is True
        assert '连续2' in reason and '完成率过低' in reason
    
    def test_should_suggest_deload_single_week_extreme(self, volume_adjuster):
        """测试单周极端情况触发Deload建议"""
        should_deload, reason = volume_adjuster.should_suggest_deload(
            avg_rpe=9.8,
            avg_completion_rate=0.75
        )
        
        assert should_deload is True
        assert '极端疲劳' in reason or 'RPE' in reason
    
    def test_get_deload_recommendation(self, volume_adjuster):
        """测试获取Deload建议详情 - Requirements 9.1, 9.3"""
        recommendation = volume_adjuster.get_deload_recommendation(
            avg_rpe=9.5,
            avg_completion_rate=0.82,
            previous_week_rpe=9.2,
            previous_week_completion=0.83,
            current_week_number=3,
            total_weeks=4
        )
        
        assert recommendation['should_deload'] is True
        assert recommendation['reason'] is not None
        assert recommendation['notification_message'] is not None
        assert recommendation['deload_config'] is not None
        assert recommendation['deload_config']['volume_factor'] == 0.6
        assert '减量' in recommendation['notification_message']
    
    def test_get_deload_recommendation_no_deload(self, volume_adjuster):
        """测试不需要Deload时的建议"""
        recommendation = volume_adjuster.get_deload_recommendation(
            avg_rpe=7.0,
            avg_completion_rate=0.92,
            current_week_number=2,
            total_weeks=4
        )
        
        assert recommendation['should_deload'] is False
        assert recommendation['reason'] is None
        assert recommendation['notification_message'] is None
        assert recommendation['deload_config'] is None


# ============================================================================
# Property Tests
# ============================================================================

class TestProperty5MultiplierBounds:
    """
    **Feature: training-plan-china-localization, Property 5: 容量调整边界约束**
    
    验证: Requirements 7.5 - personal_volume_multiplier始终在0.7-1.5范围内
    
    对于任意容量系数输入，clamp_multiplier方法应该返回0.7-1.5范围内的值
    """
    
    @given(multiplier_strategy)
    @settings(max_examples=100, deadline=None)
    def test_clamp_always_within_bounds(self, multiplier):
        """
        Property: 对于任意输入值，clamp_multiplier返回值始终在[0.7, 1.5]范围内
        
        **Validates: Requirements 7.5**
        """
        adjuster = VolumeAdjuster(
            training_log_analyzer=MagicMock(),
            backend_client=MagicMock()
        )
        
        result = adjuster.clamp_multiplier(multiplier)
        
        assert 0.7 <= result <= 1.5, (
            f"容量系数超出边界: input={multiplier}, output={result}"
        )
    
    @given(rpe_strategy, completion_rate_strategy, valid_multiplier_strategy)
    @settings(max_examples=100, deadline=None)
    def test_adjustment_result_within_bounds(self, avg_rpe, avg_completion_rate, current_multiplier):
        """
        Property: 对于任意RPE、完成率和当前容量系数，调整后的结果始终在[0.7, 1.5]范围内
        
        **Validates: Requirements 7.5**
        """
        adjuster = VolumeAdjuster(
            training_log_analyzer=MagicMock(),
            backend_client=MagicMock()
        )
        
        adjustment, direction, reason = adjuster.calculate_adjustment(
            avg_rpe=avg_rpe,
            avg_completion_rate=avg_completion_rate,
            current_multiplier=current_multiplier
        )
        
        # 计算调整后的值
        new_multiplier = adjuster.clamp_multiplier(current_multiplier + adjustment)
        
        assert 0.7 <= new_multiplier <= 1.5, (
            f"调整后容量系数超出边界: "
            f"current={current_multiplier}, adjustment={adjustment}, new={new_multiplier}"
        )
    
    def test_boundary_values(self):
        """测试边界值"""
        adjuster = VolumeAdjuster(
            training_log_analyzer=MagicMock(),
            backend_client=MagicMock()
        )
        
        # 测试精确边界
        assert adjuster.clamp_multiplier(0.7) == 0.7
        assert adjuster.clamp_multiplier(1.5) == 1.5
        
        # 测试略超边界
        assert adjuster.clamp_multiplier(0.69) == 0.7
        assert adjuster.clamp_multiplier(1.51) == 1.5


class TestProperty6IncreaseCondition:
    """
    **Feature: training-plan-china-localization, Property 6: 容量上调条件**
    
    验证: Requirements 7.2 - RPE<7且完成率>95%时，调整值在+0.05到+0.1之间
    
    当用户训练表现优秀（RPE低且完成率高）时，应该增加训练容量
    """
    
    # 生成满足上调条件的数据
    low_rpe_strategy = st.floats(min_value=1.0, max_value=6.9, allow_nan=False, allow_infinity=False)
    high_completion_strategy = st.floats(min_value=0.951, max_value=1.0, allow_nan=False, allow_infinity=False)
    
    @given(low_rpe_strategy, high_completion_strategy, valid_multiplier_strategy)
    @settings(max_examples=100, deadline=None)
    def test_increase_when_conditions_met(self, avg_rpe, avg_completion_rate, current_multiplier):
        """
        Property: 当RPE<7且完成率>95%时，调整值在+0.05到+0.1之间
        
        **Validates: Requirements 7.2**
        """
        adjuster = VolumeAdjuster(
            training_log_analyzer=MagicMock(),
            backend_client=MagicMock()
        )
        
        adjustment, direction, reason = adjuster.calculate_adjustment(
            avg_rpe=avg_rpe,
            avg_completion_rate=avg_completion_rate,
            current_multiplier=current_multiplier
        )
        
        # 验证方向为上调
        assert direction == AdjustmentDirection.INCREASE, (
            f"应该上调容量: RPE={avg_rpe}, completion={avg_completion_rate}, "
            f"但direction={direction.value}"
        )
        
        # 验证调整值在+0.05到+0.1之间
        assert 0.05 <= adjustment <= 0.10, (
            f"调整值应在[0.05, 0.10]范围内: "
            f"RPE={avg_rpe}, completion={avg_completion_rate}, adjustment={adjustment}"
        )
    
    def test_increase_at_boundary(self):
        """测试边界条件"""
        adjuster = VolumeAdjuster(
            training_log_analyzer=MagicMock(),
            backend_client=MagicMock()
        )
        
        # RPE刚好小于7，完成率刚好大于95%
        adjustment, direction, reason = adjuster.calculate_adjustment(
            avg_rpe=6.9,
            avg_completion_rate=0.96,
            current_multiplier=1.0
        )
        
        assert direction == AdjustmentDirection.INCREASE
        assert 0.05 <= adjustment <= 0.10
    
    def test_no_increase_when_rpe_too_high(self):
        """测试RPE过高时不上调"""
        adjuster = VolumeAdjuster(
            training_log_analyzer=MagicMock(),
            backend_client=MagicMock()
        )
        
        # RPE=7.5，即使完成率高也不应该大幅上调
        adjustment, direction, reason = adjuster.calculate_adjustment(
            avg_rpe=7.5,
            avg_completion_rate=0.98,
            current_multiplier=1.0
        )
        
        # 不应该是大幅上调
        assert adjustment < 0.05 or direction != AdjustmentDirection.INCREASE


class TestProperty7DecreaseCondition:
    """
    **Feature: training-plan-china-localization, Property 7: 容量下调条件**
    
    验证: Requirements 7.3 - RPE>9.5或完成率<80%时，调整值在-0.1到-0.15之间
    
    当用户训练负荷过重时，应该降低训练容量
    """
    
    # 生成满足下调条件的数据 - 高RPE
    high_rpe_strategy = st.floats(min_value=9.51, max_value=10.0, allow_nan=False, allow_infinity=False)
    # 生成满足下调条件的数据 - 低完成率
    low_completion_strategy = st.floats(min_value=0.0, max_value=0.79, allow_nan=False, allow_infinity=False)
    # 正常范围的RPE和完成率
    normal_rpe_strategy = st.floats(min_value=5.0, max_value=9.0, allow_nan=False, allow_infinity=False)
    normal_completion_strategy = st.floats(min_value=0.85, max_value=0.95, allow_nan=False, allow_infinity=False)
    
    @given(high_rpe_strategy, normal_completion_strategy, valid_multiplier_strategy)
    @settings(max_examples=100, deadline=None)
    def test_decrease_when_rpe_too_high(self, avg_rpe, avg_completion_rate, current_multiplier):
        """
        Property: 当RPE>9.5时，调整值在-0.15到-0.10之间
        
        **Validates: Requirements 7.3**
        """
        adjuster = VolumeAdjuster(
            training_log_analyzer=MagicMock(),
            backend_client=MagicMock()
        )
        
        adjustment, direction, reason = adjuster.calculate_adjustment(
            avg_rpe=avg_rpe,
            avg_completion_rate=avg_completion_rate,
            current_multiplier=current_multiplier
        )
        
        # 验证方向为下调
        assert direction == AdjustmentDirection.DECREASE, (
            f"应该下调容量: RPE={avg_rpe}, completion={avg_completion_rate}, "
            f"但direction={direction.value}"
        )
        
        # 验证调整值在-0.15到-0.10之间
        assert -0.15 <= adjustment <= -0.10, (
            f"调整值应在[-0.15, -0.10]范围内: "
            f"RPE={avg_rpe}, completion={avg_completion_rate}, adjustment={adjustment}"
        )
    
    @given(normal_rpe_strategy, low_completion_strategy, valid_multiplier_strategy)
    @settings(max_examples=100, deadline=None)
    def test_decrease_when_completion_too_low(self, avg_rpe, avg_completion_rate, current_multiplier):
        """
        Property: 当完成率<80%时，调整值在-0.15到-0.10之间
        
        **Validates: Requirements 7.3**
        """
        adjuster = VolumeAdjuster(
            training_log_analyzer=MagicMock(),
            backend_client=MagicMock()
        )
        
        adjustment, direction, reason = adjuster.calculate_adjustment(
            avg_rpe=avg_rpe,
            avg_completion_rate=avg_completion_rate,
            current_multiplier=current_multiplier
        )
        
        # 验证方向为下调
        assert direction == AdjustmentDirection.DECREASE, (
            f"应该下调容量: RPE={avg_rpe}, completion={avg_completion_rate}, "
            f"但direction={direction.value}"
        )
        
        # 验证调整值在-0.15到-0.10之间
        assert -0.15 <= adjustment <= -0.10, (
            f"调整值应在[-0.15, -0.10]范围内: "
            f"RPE={avg_rpe}, completion={avg_completion_rate}, adjustment={adjustment}"
        )
    
    def test_decrease_at_boundary(self):
        """测试边界条件"""
        adjuster = VolumeAdjuster(
            training_log_analyzer=MagicMock(),
            backend_client=MagicMock()
        )
        
        # RPE刚好大于9.5
        adjustment, direction, reason = adjuster.calculate_adjustment(
            avg_rpe=9.6,
            avg_completion_rate=0.90,
            current_multiplier=1.0
        )
        
        assert direction == AdjustmentDirection.DECREASE
        assert -0.15 <= adjustment <= -0.10
        
        # 完成率刚好小于80%
        adjustment, direction, reason = adjuster.calculate_adjustment(
            avg_rpe=7.0,
            avg_completion_rate=0.79,
            current_multiplier=1.0
        )
        
        assert direction == AdjustmentDirection.DECREASE
        assert -0.15 <= adjustment <= -0.10
    
    def test_both_conditions_trigger_decrease(self):
        """测试两个条件同时满足时的下调"""
        adjuster = VolumeAdjuster(
            training_log_analyzer=MagicMock(),
            backend_client=MagicMock()
        )
        
        # RPE高且完成率低
        adjustment, direction, reason = adjuster.calculate_adjustment(
            avg_rpe=9.8,
            avg_completion_rate=0.70,
            current_multiplier=1.0
        )
        
        assert direction == AdjustmentDirection.DECREASE
        # 两个条件都满足时，应该取更大的下调
        assert -0.15 <= adjustment <= -0.10


class TestProperty10DeloadTriggerCondition:
    """
    **Feature: training-plan-china-localization, Property 10: Deload提示触发条件**
    
    验证: Requirements 9.2 - 连续2周RPE>9或完成率<85%的用户，系统应该提示考虑进入Deload阶段
    
    当用户连续两周训练表现不佳时，应该建议进入减量恢复周
    """
    
    # 生成高RPE数据（>9）
    high_rpe_strategy = st.floats(min_value=9.01, max_value=10.0, allow_nan=False, allow_infinity=False)
    # 生成低完成率数据（<85%）
    low_completion_strategy = st.floats(min_value=0.0, max_value=0.849, allow_nan=False, allow_infinity=False)
    # 生成正常RPE数据
    normal_rpe_strategy = st.floats(min_value=5.0, max_value=8.5, allow_nan=False, allow_infinity=False)
    # 生成正常完成率数据
    normal_completion_strategy = st.floats(min_value=0.86, max_value=1.0, allow_nan=False, allow_infinity=False)
    
    @given(high_rpe_strategy, high_rpe_strategy, normal_completion_strategy, normal_completion_strategy)
    @settings(max_examples=100, deadline=None)
    def test_consecutive_high_rpe_triggers_deload(
        self, 
        current_rpe, 
        previous_rpe, 
        current_completion, 
        previous_completion
    ):
        """
        Property: 连续2周RPE>9时，应该建议Deload
        
        **Validates: Requirements 9.2**
        """
        adjuster = VolumeAdjuster(
            training_log_analyzer=MagicMock(),
            backend_client=MagicMock()
        )
        
        should_deload, reason = adjuster.should_suggest_deload(
            avg_rpe=current_rpe,
            avg_completion_rate=current_completion,
            previous_week_rpe=previous_rpe,
            previous_week_completion=previous_completion
        )
        
        # 连续两周RPE>9应该触发Deload建议
        assert should_deload is True, (
            f"连续2周RPE>9应该建议Deload: "
            f"current_rpe={current_rpe}, previous_rpe={previous_rpe}"
        )
        assert reason is not None
        assert 'RPE' in reason
    
    @given(normal_rpe_strategy, normal_rpe_strategy, low_completion_strategy, low_completion_strategy)
    @settings(max_examples=100, deadline=None)
    def test_consecutive_low_completion_triggers_deload(
        self, 
        current_rpe, 
        previous_rpe, 
        current_completion, 
        previous_completion
    ):
        """
        Property: 连续2周完成率<85%时，应该建议Deload
        
        **Validates: Requirements 9.2**
        """
        adjuster = VolumeAdjuster(
            training_log_analyzer=MagicMock(),
            backend_client=MagicMock()
        )
        
        should_deload, reason = adjuster.should_suggest_deload(
            avg_rpe=current_rpe,
            avg_completion_rate=current_completion,
            previous_week_rpe=previous_rpe,
            previous_week_completion=previous_completion
        )
        
        # 连续两周完成率<85%应该触发Deload建议
        assert should_deload is True, (
            f"连续2周完成率<85%应该建议Deload: "
            f"current_completion={current_completion}, previous_completion={previous_completion}"
        )
        assert reason is not None
        assert '完成率' in reason
    
    @given(normal_rpe_strategy, normal_rpe_strategy, normal_completion_strategy, normal_completion_strategy)
    @settings(max_examples=100, deadline=None)
    def test_normal_metrics_no_deload(
        self, 
        current_rpe, 
        previous_rpe, 
        current_completion, 
        previous_completion
    ):
        """
        Property: 正常训练指标时，不应该建议Deload
        
        **Validates: Requirements 9.2**
        """
        adjuster = VolumeAdjuster(
            training_log_analyzer=MagicMock(),
            backend_client=MagicMock()
        )
        
        should_deload, reason = adjuster.should_suggest_deload(
            avg_rpe=current_rpe,
            avg_completion_rate=current_completion,
            previous_week_rpe=previous_rpe,
            previous_week_completion=previous_completion
        )
        
        # 正常指标不应该触发Deload建议
        assert should_deload is False, (
            f"正常指标不应该建议Deload: "
            f"current_rpe={current_rpe}, current_completion={current_completion}"
        )
        assert reason is None
    
    def test_deload_recommendation_contains_notification(self):
        """
        测试Deload建议包含通知消息
        
        **Validates: Requirements 9.3**
        """
        adjuster = VolumeAdjuster(
            training_log_analyzer=MagicMock(),
            backend_client=MagicMock()
        )
        
        recommendation = adjuster.get_deload_recommendation(
            avg_rpe=9.5,
            avg_completion_rate=0.80,
            previous_week_rpe=9.3,
            previous_week_completion=0.82,
            current_week_number=3,
            total_weeks=4
        )
        
        assert recommendation['should_deload'] is True
        assert recommendation['notification_message'] is not None
        assert '减量' in recommendation['notification_message']
        assert '恢复' in recommendation['notification_message']
    
    def test_deload_config_uses_periodization_model(self):
        """
        测试Deload配置复用周期化模型
        
        **Validates: Requirements 9.1**
        """
        adjuster = VolumeAdjuster(
            training_log_analyzer=MagicMock(),
            backend_client=MagicMock()
        )
        
        recommendation = adjuster.get_deload_recommendation(
            avg_rpe=9.8,
            avg_completion_rate=0.75,
            current_week_number=3,
            total_weeks=4
        )
        
        assert recommendation['should_deload'] is True
        assert recommendation['deload_config'] is not None
        # 验证复用周期化模型的Deload配置
        assert recommendation['deload_config']['phase'] == 'deload'
        assert recommendation['deload_config']['volume_factor'] == 0.6
        assert recommendation['deload_config']['intensity_factor'] == 0.8


# ============================================================================
# Integration Tests
# ============================================================================

class TestVolumeAdjusterIntegration:
    """集成测试"""
    
    def test_adjustment_direction_consistency(self, volume_adjuster):
        """测试调整方向的一致性"""
        # 上调情况
        adjustment, direction, reason = volume_adjuster.calculate_adjustment(
            avg_rpe=5.0,
            avg_completion_rate=0.98,
            current_multiplier=1.0
        )
        assert direction == AdjustmentDirection.INCREASE
        assert adjustment > 0
        
        # 下调情况
        adjustment, direction, reason = volume_adjuster.calculate_adjustment(
            avg_rpe=9.8,
            avg_completion_rate=0.75,
            current_multiplier=1.0
        )
        assert direction == AdjustmentDirection.DECREASE
        assert adjustment < 0
        
        # 保持情况
        adjustment, direction, reason = volume_adjuster.calculate_adjustment(
            avg_rpe=7.5,
            avg_completion_rate=0.88,
            current_multiplier=1.0
        )
        assert direction == AdjustmentDirection.MAINTAIN
        assert adjustment == 0
    
    def test_reason_contains_metrics(self, volume_adjuster):
        """测试原因包含指标信息"""
        adjustment, direction, reason = volume_adjuster.calculate_adjustment(
            avg_rpe=5.5,
            avg_completion_rate=0.97,
            current_multiplier=1.0
        )
        
        # 原因应该包含RPE和完成率信息
        assert 'RPE' in reason or 'rpe' in reason.lower()
        assert '%' in reason or '完成率' in reason
    
    def test_deload_suggestion_with_extreme_values(self, volume_adjuster):
        """测试极端值时的Deload建议"""
        # 极端高RPE
        should_deload, reason = volume_adjuster.should_suggest_deload(
            avg_rpe=10.0,
            avg_completion_rate=0.90
        )
        assert should_deload is True
        
        # 极端低完成率
        should_deload, reason = volume_adjuster.should_suggest_deload(
            avg_rpe=7.0,
            avg_completion_rate=0.50
        )
        assert should_deload is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
