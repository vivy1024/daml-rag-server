# -*- coding: utf-8 -*-
"""
Progressive Overload Calculator Unit Tests

测试渐进过载计算器的核心功能和属性测试。

Properties:
- Property 8: 渐进过载正向调整 (Requirements 8.1)
- Property 9: 渐进过载保守调整 (Requirements 8.2)

作者: BUILD_BODY Team
版本: 1.0.0
日期: 2025-12-26
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from typing import Dict, Any, Tuple
from unittest.mock import AsyncMock, MagicMock

from src.applications.fitness.services.progressive_overload import (
    ProgressiveOverloadCalculator,
    OverloadResult,
    OverloadDecision,
    ExerciseType,
    MAVCheckResult
)


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def mock_backend_client():
    """创建模拟的BackendClient"""
    client = MagicMock()
    client.get_personal_bests = AsyncMock(return_value=[])
    return client


@pytest.fixture
def mock_training_log_analyzer():
    """创建模拟的TrainingLogAnalyzer"""
    analyzer = MagicMock()
    return analyzer


@pytest.fixture
def calculator(mock_backend_client, mock_training_log_analyzer):
    """创建ProgressiveOverloadCalculator实例"""
    return ProgressiveOverloadCalculator(
        backend_client=mock_backend_client,
        training_log_analyzer=mock_training_log_analyzer
    )


@pytest.fixture
def calculator_no_deps():
    """创建无依赖的ProgressiveOverloadCalculator实例"""
    return ProgressiveOverloadCalculator()


# ============================================================================
# Hypothesis Strategies
# ============================================================================

# 重量策略（正数，合理范围）
weight_strategy = st.floats(min_value=2.5, max_value=300.0, allow_nan=False, allow_infinity=False)

# 个人最佳记录策略
personal_best_strategy = st.floats(min_value=0.0, max_value=400.0, allow_nan=False, allow_infinity=False)

# 动作类型策略
exercise_type_strategy = st.sampled_from([ExerciseType.COMPOUND, ExerciseType.ISOLATION])

# 容量系数策略
volume_multiplier_strategy = st.floats(min_value=0.7, max_value=1.5, allow_nan=False, allow_infinity=False)

# 每周组数策略
weekly_sets_strategy = st.integers(min_value=1, max_value=30)


# ============================================================================
# Unit Tests - Basic Functionality
# ============================================================================

class TestProgressiveOverloadBasic:
    """基础功能测试"""
    
    def test_init(self, calculator_no_deps):
        """测试初始化"""
        assert calculator_no_deps.WEIGHT_INCREMENT[ExerciseType.COMPOUND] == 2.5
        assert calculator_no_deps.WEIGHT_INCREMENT[ExerciseType.ISOLATION] == 1.25
        assert calculator_no_deps.REGRESSION_THRESHOLD == 0.10
    
    def test_identify_compound_exercise(self, calculator_no_deps):
        """测试识别复合动作"""
        assert calculator_no_deps._identify_exercise_type("squat", "深蹲") == ExerciseType.COMPOUND
        assert calculator_no_deps._identify_exercise_type("bench_press", "卧推") == ExerciseType.COMPOUND
        assert calculator_no_deps._identify_exercise_type("deadlift", "硬拉") == ExerciseType.COMPOUND
    
    def test_identify_isolation_exercise(self, calculator_no_deps):
        """测试识别孤立动作"""
        assert calculator_no_deps._identify_exercise_type("bicep_curl", "弯举") == ExerciseType.ISOLATION
        assert calculator_no_deps._identify_exercise_type("lateral_raise", "侧平举") == ExerciseType.ISOLATION
        assert calculator_no_deps._identify_exercise_type("fly", "飞鸟") == ExerciseType.ISOLATION
    
    def test_identify_explicit_type(self, calculator_no_deps):
        """测试显式指定类型"""
        # 显式指定应该覆盖自动识别
        assert calculator_no_deps._identify_exercise_type(
            "squat", "深蹲", ExerciseType.ISOLATION
        ) == ExerciseType.ISOLATION
    
    def test_weight_annotation_increase(self, calculator_no_deps):
        """测试重量增加标注"""
        annotation = calculator_no_deps.get_weight_annotation(50.0, 52.5)
        assert annotation == "+2.5kg"
    
    def test_weight_annotation_maintain(self, calculator_no_deps):
        """测试重量保持标注"""
        annotation = calculator_no_deps.get_weight_annotation(50.0, 50.0)
        assert annotation == "保持"
    
    def test_weight_annotation_decrease(self, calculator_no_deps):
        """测试重量降低标注"""
        annotation = calculator_no_deps.get_weight_annotation(50.0, 47.5)
        assert annotation == "-2.5kg"


class TestMicroPlateSuggestion:
    """小片建议测试"""
    
    def test_suggest_for_isolation(self, calculator_no_deps):
        """测试孤立动作建议小片"""
        suggest, message = calculator_no_deps.suggest_micro_plates(
            ExerciseType.ISOLATION, "弯举"
        )
        assert suggest is True
        assert "1.25kg" in message
        assert "弯举" in message
    
    def test_no_suggest_for_compound(self, calculator_no_deps):
        """测试复合动作不建议小片"""
        suggest, message = calculator_no_deps.suggest_micro_plates(
            ExerciseType.COMPOUND, "深蹲"
        )
        assert suggest is False
        assert message is None


class TestRegressionDetection:
    """退步检测测试"""
    
    def test_detect_regression(self, calculator_no_deps):
        """测试检测到退步"""
        # 当前重量比最佳下降超过10%
        detected, message = calculator_no_deps.detect_regression(
            current_weight=80.0,
            personal_best=100.0,
            exercise_name="卧推"
        )
        assert detected is True
        assert "下降" in message
        assert "卧推" in message
    
    def test_no_regression(self, calculator_no_deps):
        """测试未检测到退步"""
        # 当前重量接近最佳
        detected, message = calculator_no_deps.detect_regression(
            current_weight=95.0,
            personal_best=100.0,
            exercise_name="卧推"
        )
        assert detected is False
        assert message is None
    
    def test_no_regression_with_zero_pb(self, calculator_no_deps):
        """测试没有个人最佳记录时不检测退步"""
        detected, message = calculator_no_deps.detect_regression(
            current_weight=50.0,
            personal_best=0.0,
            exercise_name="卧推"
        )
        assert detected is False
        assert message is None


class TestMAVCheck:
    """MAV检查测试"""
    
    def test_within_mav(self, calculator_no_deps):
        """测试在MAV范围内"""
        result = calculator_no_deps.check_mav_limit(
            muscle_group="chest",
            current_weekly_sets=15,
            user_volume_multiplier=1.0
        )
        assert result.is_approaching_mav is False
        assert result.is_exceeding_mav is False
        assert "合理范围" in result.message
    
    def test_approaching_mav(self, calculator_no_deps):
        """测试接近MAV"""
        result = calculator_no_deps.check_mav_limit(
            muscle_group="chest",
            current_weekly_sets=19,  # 接近MAV 20
            user_volume_multiplier=1.0
        )
        assert result.is_approaching_mav is True
        assert result.is_exceeding_mav is False
        assert "接近" in result.message
    
    def test_exceeding_mav(self, calculator_no_deps):
        """测试超过MAV"""
        result = calculator_no_deps.check_mav_limit(
            muscle_group="chest",
            current_weekly_sets=25,  # 超过MAV 20
            user_volume_multiplier=1.0
        )
        assert result.is_approaching_mav is True
        assert result.is_exceeding_mav is True
        assert "超过" in result.message
    
    def test_mav_with_volume_multiplier(self, calculator_no_deps):
        """测试容量系数影响MAV"""
        # 高容量系数用户，MAV更高
        result = calculator_no_deps.check_mav_limit(
            muscle_group="chest",
            current_weekly_sets=25,
            user_volume_multiplier=1.5  # MAV变为30
        )
        assert result.is_exceeding_mav is False


# ============================================================================
# Property Tests
# ============================================================================

class TestProperty8PositiveOverload:
    """
    **Feature: training-plan-china-localization, Property 8: 渐进过载正向调整**
    
    验证: Requirements 8.1 - 完成所有目标次数时，下周建议重量应该增加2.5-5kg
    
    当用户完成本周所有目标次数时，系统应该建议增加重量：
    - 复合动作增加2.5kg
    - 孤立动作增加1.25kg（如果有小片）
    """
    
    @given(weight_strategy, exercise_type_strategy)
    @settings(max_examples=100, deadline=None)
    def test_increase_when_completed(self, last_weight, exercise_type):
        """
        Property: 当完成所有目标次数时，下周重量应该增加
        
        **Validates: Requirements 8.1**
        """
        calculator = ProgressiveOverloadCalculator()
        
        next_weight, decision, reason = calculator.calculate_next_weight(
            last_weight=last_weight,
            completed_all_reps=True,
            exercise_type=exercise_type
        )
        
        # 验证决策为增加
        assert decision == OverloadDecision.INCREASE, (
            f"完成所有目标次数时应该增加重量: "
            f"last_weight={last_weight}, exercise_type={exercise_type.value}, "
            f"但decision={decision.value}"
        )
        
        # 验证重量增加
        expected_increment = calculator.WEIGHT_INCREMENT[exercise_type]
        assert next_weight == last_weight + expected_increment, (
            f"重量增加不正确: "
            f"last_weight={last_weight}, expected_increment={expected_increment}, "
            f"next_weight={next_weight}"
        )
    
    @given(weight_strategy)
    @settings(max_examples=100, deadline=None)
    def test_compound_increase_2_5kg(self, last_weight):
        """
        Property: 复合动作完成时增加2.5kg
        
        **Validates: Requirements 8.1**
        """
        calculator = ProgressiveOverloadCalculator()
        
        next_weight, decision, reason = calculator.calculate_next_weight(
            last_weight=last_weight,
            completed_all_reps=True,
            exercise_type=ExerciseType.COMPOUND
        )
        
        assert next_weight == last_weight + 2.5, (
            f"复合动作应增加2.5kg: last_weight={last_weight}, next_weight={next_weight}"
        )
    
    @given(weight_strategy)
    @settings(max_examples=100, deadline=None)
    def test_isolation_increase_1_25kg(self, last_weight):
        """
        Property: 孤立动作完成时增加1.25kg
        
        **Validates: Requirements 8.1**
        """
        calculator = ProgressiveOverloadCalculator()
        
        next_weight, decision, reason = calculator.calculate_next_weight(
            last_weight=last_weight,
            completed_all_reps=True,
            exercise_type=ExerciseType.ISOLATION
        )
        
        assert next_weight == last_weight + 1.25, (
            f"孤立动作应增加1.25kg: last_weight={last_weight}, next_weight={next_weight}"
        )
    
    def test_increase_annotation_format(self):
        """测试增加时的标注格式"""
        calculator = ProgressiveOverloadCalculator()
        
        result = calculator.calculate_overload(
            exercise_id="bench_press",
            exercise_name="卧推",
            last_weight=60.0,
            completed_all_reps=True
        )
        
        assert result.decision == OverloadDecision.INCREASE
        assert result.annotation == "+2.5kg"
        assert result.next_weight == 62.5


class TestProperty9ConservativeOverload:
    """
    **Feature: training-plan-china-localization, Property 9: 渐进过载保守调整**
    
    验证: Requirements 8.2 - 未完成目标次数时，下周建议重量应该保持或微降（不超过5%）
    
    当用户未完成本周目标次数时，系统应该保守处理：
    - 保持当前重量
    - 不应该增加重量
    """
    
    @given(weight_strategy, exercise_type_strategy)
    @settings(max_examples=100, deadline=None)
    def test_maintain_when_not_completed(self, last_weight, exercise_type):
        """
        Property: 当未完成目标次数时，下周重量应该保持不变
        
        **Validates: Requirements 8.2**
        """
        calculator = ProgressiveOverloadCalculator()
        
        next_weight, decision, reason = calculator.calculate_next_weight(
            last_weight=last_weight,
            completed_all_reps=False,
            exercise_type=exercise_type
        )
        
        # 验证决策为保持
        assert decision == OverloadDecision.MAINTAIN, (
            f"未完成目标次数时应该保持重量: "
            f"last_weight={last_weight}, exercise_type={exercise_type.value}, "
            f"但decision={decision.value}"
        )
        
        # 验证重量保持不变
        assert next_weight == last_weight, (
            f"重量应该保持不变: "
            f"last_weight={last_weight}, next_weight={next_weight}"
        )
    
    @given(weight_strategy, exercise_type_strategy)
    @settings(max_examples=100, deadline=None)
    def test_no_increase_when_not_completed(self, last_weight, exercise_type):
        """
        Property: 当未完成目标次数时，下周重量不应该增加
        
        **Validates: Requirements 8.2**
        """
        calculator = ProgressiveOverloadCalculator()
        
        next_weight, decision, reason = calculator.calculate_next_weight(
            last_weight=last_weight,
            completed_all_reps=False,
            exercise_type=exercise_type
        )
        
        # 验证重量不增加
        assert next_weight <= last_weight, (
            f"未完成时重量不应增加: "
            f"last_weight={last_weight}, next_weight={next_weight}"
        )
    
    @given(weight_strategy, exercise_type_strategy)
    @settings(max_examples=100, deadline=None)
    def test_decrease_within_5_percent(self, last_weight, exercise_type):
        """
        Property: 如果重量降低，降幅不应超过5%
        
        **Validates: Requirements 8.2**
        """
        calculator = ProgressiveOverloadCalculator()
        
        next_weight, decision, reason = calculator.calculate_next_weight(
            last_weight=last_weight,
            completed_all_reps=False,
            exercise_type=exercise_type
        )
        
        # 当前实现是保持不变，但如果有降低，不应超过5%
        if next_weight < last_weight:
            decrease_percent = (last_weight - next_weight) / last_weight
            assert decrease_percent <= 0.05, (
                f"降幅超过5%: "
                f"last_weight={last_weight}, next_weight={next_weight}, "
                f"decrease={decrease_percent:.2%}"
            )
    
    def test_maintain_annotation_format(self):
        """测试保持时的标注格式"""
        calculator = ProgressiveOverloadCalculator()
        
        result = calculator.calculate_overload(
            exercise_id="bench_press",
            exercise_name="卧推",
            last_weight=60.0,
            completed_all_reps=False
        )
        
        assert result.decision == OverloadDecision.MAINTAIN
        assert result.annotation == "保持"
        assert result.next_weight == 60.0


# ============================================================================
# Integration Tests
# ============================================================================

class TestProgressiveOverloadIntegration:
    """集成测试"""
    
    def test_full_overload_calculation(self, calculator_no_deps):
        """测试完整的渐进过载计算"""
        result = calculator_no_deps.calculate_overload(
            exercise_id="squat",
            exercise_name="深蹲",
            last_weight=100.0,
            completed_all_reps=True,
            personal_best=105.0,
            muscle_group="quads",
            current_weekly_sets=15,
            user_volume_multiplier=1.0
        )
        
        assert result.exercise_id == "squat"
        assert result.exercise_name == "深蹲"
        assert result.exercise_type == ExerciseType.COMPOUND
        assert result.last_weight == 100.0
        assert result.next_weight == 102.5
        assert result.decision == OverloadDecision.INCREASE
        assert result.annotation == "+2.5kg"
        assert result.regression_detected is False
    
    def test_regression_triggers_technique_check(self, calculator_no_deps):
        """测试退步触发技术排查"""
        result = calculator_no_deps.calculate_overload(
            exercise_id="bench_press",
            exercise_name="卧推",
            last_weight=70.0,
            completed_all_reps=True,
            personal_best=100.0  # 当前重量比最佳下降30%
        )
        
        assert result.regression_detected is True
        assert result.decision == OverloadDecision.TECHNIQUE_CHECK
        assert result.regression_message is not None
    
    def test_isolation_with_micro_plate_suggestion(self, calculator_no_deps):
        """测试孤立动作带小片建议"""
        result = calculator_no_deps.calculate_overload(
            exercise_id="bicep_curl",
            exercise_name="弯举",
            last_weight=15.0,
            completed_all_reps=True
        )
        
        assert result.exercise_type == ExerciseType.ISOLATION
        assert result.next_weight == 16.25
        assert result.micro_plate_suggestion is True
        assert "1.25kg" in result.micro_plate_message
    
    def test_mav_warning_included(self, calculator_no_deps):
        """测试MAV警告包含在结果中"""
        result = calculator_no_deps.calculate_overload(
            exercise_id="bench_press",
            exercise_name="卧推",
            last_weight=80.0,
            completed_all_reps=True,
            muscle_group="chest",
            current_weekly_sets=25,  # 超过MAV
            user_volume_multiplier=1.0
        )
        
        assert result.mav_warning is True
        assert result.mav_message is not None
        assert "超过" in result.mav_message
    
    def test_result_to_dict(self, calculator_no_deps):
        """测试结果转换为字典"""
        result = calculator_no_deps.calculate_overload(
            exercise_id="squat",
            exercise_name="深蹲",
            last_weight=100.0,
            completed_all_reps=True
        )
        
        result_dict = result.to_dict()
        
        assert 'exercise_id' in result_dict
        assert 'next_weight' in result_dict
        assert 'decision' in result_dict
        assert 'annotation' in result_dict
        assert result_dict['exercise_id'] == "squat"
        assert result_dict['next_weight'] == 102.5


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
