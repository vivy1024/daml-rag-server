# -*- coding: utf-8 -*-
"""
Intensity Converter Unit Tests

测试训练强度指标转换服务的核心功能。

核心功能测试：
- RPE (Rating of Perceived Exertion) 主观疲劳度量表 (1-10)
- %1RM (Percentage of 1 Rep Max) 最大重量百分比
- RIR (Reps in Reserve) 储备次数 (0-5)
- 三种指标间的相互转换
- 往返转换一致性验证

Requirements: 10.1, 10.2, 10.3, 10.4, 10.5 - 训练强度指标扩展

作者: BUILD_BODY Team
版本: 1.0.0
日期: 2026-01-06
"""

import pytest
from typing import Dict, Any

from src.applications.fitness.services.intensity_converter import (
    IntensityConverter,
    IntensityMetric,
    IntensityValue,
    IntensityConversionResult,
    IntensityRecommendation,
    TrainingGoal,
    get_intensity_converter,
    reset_intensity_converter
)


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def converter():
    """创建IntensityConverter实例"""
    reset_intensity_converter()
    return get_intensity_converter()


@pytest.fixture(autouse=True)
def reset_singleton():
    """每个测试后重置单例"""
    yield
    reset_intensity_converter()


# ============================================================================
# Unit Tests - RPE Support (Requirement 10.1)
# ============================================================================

class TestRPESupport:
    """RPE指标支持测试 - Requirements 10.1"""
    
    def test_rpe_validation_valid_range(self, converter):
        """测试RPE有效范围验证"""
        # 有效值应该通过
        assert converter._validate_rpe(1.0) == 1.0
        assert converter._validate_rpe(5.0) == 5.0
        assert converter._validate_rpe(10.0) == 10.0
        assert converter._validate_rpe(7.5) == 7.5
    
    def test_rpe_validation_rounding(self, converter):
        """测试RPE四舍五入到0.5"""
        assert converter._validate_rpe(7.3) == 7.5
        assert converter._validate_rpe(7.7) == 7.5  # 7.7 * 2 = 15.4, round = 15, / 2 = 7.5
        assert converter._validate_rpe(7.8) == 8.0  # 7.8 * 2 = 15.6, round = 16, / 2 = 8.0
        assert converter._validate_rpe(8.1) == 8.0
    
    def test_rpe_validation_invalid_range(self, converter):
        """测试RPE无效范围"""
        with pytest.raises(ValueError):
            converter._validate_rpe(0.5)
        with pytest.raises(ValueError):
            converter._validate_rpe(10.5)
    
    def test_rpe_description(self, converter):
        """测试RPE描述"""
        assert "力竭" in converter._get_rpe_description(10)
        assert "困难" in converter._get_rpe_description(8)
        assert "轻松" in converter._get_rpe_description(5)


# ============================================================================
# Unit Tests - %1RM Support (Requirement 10.2)
# ============================================================================

class TestPercent1RMSupport:
    """%1RM指标支持测试 - Requirements 10.2"""
    
    def test_percent_1rm_validation_valid_range(self, converter):
        """测试%1RM有效范围验证"""
        assert converter._validate_percent_1rm(0.0) == 0.0
        assert converter._validate_percent_1rm(50.0) == 50.0
        assert converter._validate_percent_1rm(100.0) == 100.0
        assert converter._validate_percent_1rm(85.5) == 85.5
    
    def test_percent_1rm_validation_invalid_range(self, converter):
        """测试%1RM无效范围"""
        with pytest.raises(ValueError):
            converter._validate_percent_1rm(-1.0)
        with pytest.raises(ValueError):
            converter._validate_percent_1rm(101.0)


# ============================================================================
# Unit Tests - RIR Support (Requirement 10.3)
# ============================================================================

class TestRIRSupport:
    """RIR指标支持测试 - Requirements 10.3"""
    
    def test_rir_validation_valid_range(self, converter):
        """测试RIR有效范围验证"""
        assert converter._validate_rir(0.0) == 0.0
        assert converter._validate_rir(2.0) == 2.0
        assert converter._validate_rir(5.0) == 5.0
    
    def test_rir_validation_rounding(self, converter):
        """测试RIR四舍五入到0.5"""
        assert converter._validate_rir(2.3) == 2.5
        assert converter._validate_rir(2.7) == 2.5
        assert converter._validate_rir(3.1) == 3.0
    
    def test_rir_validation_max_cap(self, converter):
        """测试RIR最大值限制为5"""
        assert converter._validate_rir(6.0) == 5.0
        assert converter._validate_rir(10.0) == 5.0
    
    def test_rir_validation_invalid_negative(self, converter):
        """测试RIR不能为负数"""
        with pytest.raises(ValueError):
            converter._validate_rir(-1.0)


# ============================================================================
# Unit Tests - Intensity Conversion (Requirement 10.5)
# ============================================================================

class TestRPEToRIRConversion:
    """RPE到RIR转换测试"""
    
    def test_rpe_10_to_rir_0(self, converter):
        """RPE 10 = RIR 0 (力竭)"""
        result = converter.rpe_to_rir(10.0)
        assert result.target.value == 0.0
        assert result.target.metric == IntensityMetric.RIR
    
    def test_rpe_9_to_rir_1(self, converter):
        """RPE 9 = RIR 1"""
        result = converter.rpe_to_rir(9.0)
        assert result.target.value == 1.0
    
    def test_rpe_8_to_rir_2(self, converter):
        """RPE 8 = RIR 2"""
        result = converter.rpe_to_rir(8.0)
        assert result.target.value == 2.0
    
    def test_rpe_7_to_rir_3(self, converter):
        """RPE 7 = RIR 3"""
        result = converter.rpe_to_rir(7.0)
        assert result.target.value == 3.0
    
    def test_rpe_5_to_rir_5(self, converter):
        """RPE 5 = RIR 5"""
        result = converter.rpe_to_rir(5.0)
        assert result.target.value == 5.0


class TestRIRToRPEConversion:
    """RIR到RPE转换测试"""
    
    def test_rir_0_to_rpe_10(self, converter):
        """RIR 0 = RPE 10 (力竭)"""
        result = converter.rir_to_rpe(0.0)
        assert result.target.value == 10.0
        assert result.target.metric == IntensityMetric.RPE
    
    def test_rir_1_to_rpe_9(self, converter):
        """RIR 1 = RPE 9"""
        result = converter.rir_to_rpe(1.0)
        assert result.target.value == 9.0
    
    def test_rir_2_to_rpe_8(self, converter):
        """RIR 2 = RPE 8"""
        result = converter.rir_to_rpe(2.0)
        assert result.target.value == 8.0


class TestRPEToPercent1RMConversion:
    """RPE到%1RM转换测试"""
    
    def test_rpe_10_to_percent_100(self, converter):
        """RPE 10 ≈ 100% 1RM"""
        result = converter.rpe_to_percent_1rm(10.0)
        assert result.target.value == 100.0
    
    def test_rpe_8_to_percent_85_90(self, converter):
        """RPE 8 ≈ 85-90% 1RM"""
        result = converter.rpe_to_percent_1rm(8.0)
        assert 85.0 <= result.target.value <= 90.0
    
    def test_rpe_7_to_percent_78_82(self, converter):
        """RPE 7 ≈ 78-82% 1RM"""
        result = converter.rpe_to_percent_1rm(7.0)
        assert 78.0 <= result.target.value <= 82.0


class TestPercent1RMToRPEConversion:
    """%1RM到RPE转换测试"""
    
    def test_percent_100_to_rpe_10(self, converter):
        """100% 1RM ≈ RPE 10"""
        result = converter.percent_1rm_to_rpe(100.0)
        assert result.target.value == 10.0
    
    def test_percent_85_to_rpe_8(self, converter):
        """85% 1RM ≈ RPE 8"""
        result = converter.percent_1rm_to_rpe(85.0)
        assert 7.5 <= result.target.value <= 8.5
    
    def test_percent_70_to_rpe_6(self, converter):
        """70% 1RM ≈ RPE 6"""
        result = converter.percent_1rm_to_rpe(70.0)
        assert 5.5 <= result.target.value <= 7.0


class TestChainedConversions:
    """链式转换测试"""
    
    def test_rir_to_percent_1rm(self, converter):
        """RIR -> %1RM 链式转换"""
        result = converter.rir_to_percent_1rm(2.0)
        # RIR 2 -> RPE 8 -> ~87% 1RM
        assert 85.0 <= result.target.value <= 90.0
    
    def test_percent_1rm_to_rir(self, converter):
        """%1RM -> RIR 链式转换"""
        result = converter.percent_1rm_to_rir(85.0)
        # 85% 1RM -> RPE ~8 -> RIR ~2
        assert 1.5 <= result.target.value <= 3.0


class TestGenericConvert:
    """通用转换方法测试"""
    
    def test_convert_same_metric(self, converter):
        """相同指标转换"""
        result = converter.convert(8.0, IntensityMetric.RPE, IntensityMetric.RPE)
        assert result.source.value == result.target.value
        assert result.tolerance == 0.0
    
    def test_convert_rpe_to_rir(self, converter):
        """RPE到RIR转换"""
        result = converter.convert(8.0, IntensityMetric.RPE, IntensityMetric.RIR)
        assert result.target.value == 2.0
    
    def test_convert_all(self, converter):
        """转换为所有指标"""
        results = converter.convert_all(8.0, IntensityMetric.RPE)
        assert IntensityMetric.RPE in results
        assert IntensityMetric.RIR in results
        assert IntensityMetric.PERCENT_1RM in results


# ============================================================================
# Unit Tests - Training Goal Recommendations (Requirement 10.4)
# ============================================================================

class TestTrainingGoalRecommendations:
    """训练目标强度推荐测试 - Requirements 10.4"""
    
    def test_strength_recommendation(self, converter):
        """力量训练推荐"""
        rec = converter.get_intensity_recommendation(TrainingGoal.STRENGTH)
        assert rec.goal == TrainingGoal.STRENGTH
        assert 8.0 <= rec.rpe.value <= 9.5
        assert 85.0 <= rec.percent_1rm.value <= 95.0
        assert rec.rep_range == (1, 5)
        assert rec.rest_seconds[0] >= 180  # 长休息
    
    def test_hypertrophy_recommendation(self, converter):
        """增肌训练推荐"""
        rec = converter.get_intensity_recommendation(TrainingGoal.HYPERTROPHY)
        assert rec.goal == TrainingGoal.HYPERTROPHY
        assert 7.0 <= rec.rpe.value <= 9.0
        assert 65.0 <= rec.percent_1rm.value <= 85.0
        assert rec.rep_range == (6, 12)
    
    def test_endurance_recommendation(self, converter):
        """耐力训练推荐"""
        rec = converter.get_intensity_recommendation(TrainingGoal.ENDURANCE)
        assert rec.goal == TrainingGoal.ENDURANCE
        assert 5.0 <= rec.rpe.value <= 7.0
        assert 50.0 <= rec.percent_1rm.value <= 70.0
        assert rec.rep_range == (12, 20)
        assert rec.rest_seconds[1] <= 60  # 短休息
    
    def test_power_recommendation(self, converter):
        """爆发力训练推荐"""
        rec = converter.get_intensity_recommendation(TrainingGoal.POWER)
        assert rec.goal == TrainingGoal.POWER
        assert rec.rep_range == (3, 6)
    
    def test_recommendation_to_dict(self, converter):
        """推荐结果转换为字典"""
        rec = converter.get_intensity_recommendation(TrainingGoal.HYPERTROPHY)
        rec_dict = rec.to_dict()
        assert 'goal' in rec_dict
        assert 'rpe' in rec_dict
        assert 'percent_1rm' in rec_dict
        assert 'rir' in rec_dict
        assert 'rep_range' in rec_dict


# ============================================================================
# Unit Tests - Round Trip Validation (Requirement 10.5)
# ============================================================================

class TestRoundTripValidation:
    """往返转换验证测试 - Requirements 10.5"""
    
    def test_rpe_round_trip(self, converter):
        """RPE往返转换"""
        passed, error, msg = converter.validate_round_trip(8.0, IntensityMetric.RPE)
        assert passed, f"RPE往返验证失败: {msg}"
        assert error <= 0.5
    
    def test_rir_round_trip(self, converter):
        """RIR往返转换"""
        passed, error, msg = converter.validate_round_trip(2.0, IntensityMetric.RIR)
        assert passed, f"RIR往返验证失败: {msg}"
        assert error <= 0.5
    
    def test_percent_1rm_round_trip(self, converter):
        """%1RM往返转换"""
        passed, error, msg = converter.validate_round_trip(85.0, IntensityMetric.PERCENT_1RM)
        assert passed, f"%1RM往返验证失败: {msg}"
        assert error <= 5.0  # %1RM容差较大


# ============================================================================
# Unit Tests - Formatting
# ============================================================================

class TestFormatting:
    """格式化输出测试"""
    
    def test_format_rpe(self, converter):
        """格式化RPE"""
        formatted = converter.format_intensity(8.0, IntensityMetric.RPE)
        assert "RPE 8" in formatted
        assert "RIR" in formatted
        assert "1RM" in formatted
    
    def test_format_rir(self, converter):
        """格式化RIR"""
        formatted = converter.format_intensity(2.0, IntensityMetric.RIR)
        assert "RIR 2" in formatted
        assert "RPE" in formatted
    
    def test_format_percent_1rm(self, converter):
        """格式化%1RM"""
        formatted = converter.format_intensity(85.0, IntensityMetric.PERCENT_1RM)
        assert "85%" in formatted
        assert "1RM" in formatted
    
    def test_format_without_equivalents(self, converter):
        """格式化不包含等效值"""
        formatted = converter.format_intensity(8.0, IntensityMetric.RPE, include_equivalents=False)
        assert "RPE 8" in formatted
        assert "RIR" not in formatted


# ============================================================================
# Unit Tests - Intensity for Reps
# ============================================================================

class TestIntensityForReps:
    """根据次数推荐强度测试"""
    
    def test_low_reps_high_intensity(self, converter):
        """低次数高强度"""
        intensity = converter.get_intensity_for_reps(3, TrainingGoal.STRENGTH)
        assert intensity['percent_1rm'] >= 85.0
    
    def test_medium_reps_medium_intensity(self, converter):
        """中等次数中等强度"""
        intensity = converter.get_intensity_for_reps(10, TrainingGoal.HYPERTROPHY)
        assert 65.0 <= intensity['percent_1rm'] <= 85.0
    
    def test_high_reps_low_intensity(self, converter):
        """高次数低强度"""
        intensity = converter.get_intensity_for_reps(15, TrainingGoal.ENDURANCE)
        assert intensity['percent_1rm'] <= 70.0


# ============================================================================
# Unit Tests - Singleton Pattern
# ============================================================================

class TestSingletonPattern:
    """单例模式测试"""
    
    def test_get_same_instance(self):
        """获取相同实例"""
        reset_intensity_converter()
        instance1 = get_intensity_converter()
        instance2 = get_intensity_converter()
        assert instance1 is instance2
    
    def test_reset_creates_new_instance(self):
        """重置后创建新实例"""
        instance1 = get_intensity_converter()
        reset_intensity_converter()
        instance2 = get_intensity_converter()
        assert instance1 is not instance2


# ============================================================================
# Unit Tests - Data Classes
# ============================================================================

class TestDataClasses:
    """数据类测试"""
    
    def test_intensity_value_to_dict(self):
        """IntensityValue转换为字典"""
        value = IntensityValue(
            metric=IntensityMetric.RPE,
            value=8.0,
            description="困难"
        )
        d = value.to_dict()
        assert d['metric'] == 'rpe'
        assert d['value'] == 8.0
        assert d['description'] == '困难'
    
    def test_conversion_result_to_dict(self, converter):
        """IntensityConversionResult转换为字典"""
        result = converter.rpe_to_rir(8.0)
        d = result.to_dict()
        assert 'source' in d
        assert 'target' in d
        assert 'tolerance' in d
        assert 'notes' in d


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
