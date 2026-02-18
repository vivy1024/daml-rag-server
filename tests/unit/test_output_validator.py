# -*- coding: utf-8 -*-
"""
LLM输出验证器 - 单元测试

覆盖场景:
- 正常通过（无违规）
- 禁忌症触发
- 禁忌症在警告上下文中（不触发）
- 训练量超标
- 多种违规同时触发
- apply_to_analysis降低置信度

Task 43 - Phase 7 Batch 3 性能与可观测性
"""

import pytest
import sys
import os
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from framework.validators.output_validator import LLMOutputValidator, ValidationResult


@dataclass
class MockAnalysisResult:
    """模拟AnalysisResult"""
    professional_analysis: str = ""
    personalized_recommendations: List[str] = field(default_factory=list)
    safety_reminders: List[str] = field(default_factory=list)
    reasoning_basis: Dict[str, List[str]] = field(default_factory=dict)
    confidence: float = 0.85
    model_used: str = "test"
    analysis_metadata: Dict[str, Any] = field(default_factory=dict)


class TestContraindicationCheck:
    """禁忌症交叉检查测试"""

    def setup_method(self):
        self.validator = LLMOutputValidator()

    def test_no_contraindications_passes(self):
        """无禁忌列表时直接通过"""
        result = self.validator.validate("推荐做深蹲和卧推", contraindications=None)
        assert result.is_valid is True
        assert len(result.contraindication_violations) == 0

    def test_safe_output_passes(self):
        """输出不包含禁忌动作时通过"""
        result = self.validator.validate(
            "推荐做俯卧撑和平板支撑",
            contraindications=[{"name": "深蹲", "reason": "膝盖损伤"}],
        )
        assert result.is_valid is True

    def test_contraindication_violation_detected(self):
        """检测到推荐了禁忌动作"""
        result = self.validator.validate(
            "建议每天做3组深蹲，每组15次",
            contraindications=[{"name": "深蹲", "reason": "膝盖损伤"}],
        )
        assert result.is_valid is False
        assert len(result.contraindication_violations) == 1
        assert "深蹲" in result.contraindication_violations[0]
        assert "膝盖损伤" in result.contraindication_violations[0]

    def test_contraindication_in_warning_context_ok(self):
        """禁忌动作出现在警告上下文中不触发"""
        result = self.validator.validate(
            "⚠️ 注意：由于膝盖损伤，请避免深蹲动作",
            contraindications=[{"name": "深蹲", "reason": "膝盖损伤"}],
        )
        assert result.is_valid is True

    def test_contraindication_with_avoid_keyword(self):
        """禁忌动作在'不推荐'上下文中不触发"""
        result = self.validator.validate(
            "不推荐做深蹲，建议用腿举替代",
            contraindications=[{"name": "深蹲", "reason": "膝盖损伤"}],
        )
        assert result.is_valid is True

    def test_multiple_contraindications(self):
        """多个禁忌动作检查"""
        result = self.validator.validate(
            "今天的训练计划：深蹲5组、硬拉3组、卧推4组",
            contraindications=[
                {"name": "深蹲", "reason": "膝盖损伤"},
                {"name": "硬拉", "reason": "腰椎间盘突出"},
            ],
        )
        assert len(result.contraindication_violations) == 2

    def test_string_contraindication_format(self):
        """支持字符串格式的禁忌列表"""
        result = self.validator.validate(
            "推荐做深蹲训练",
            contraindications=["深蹲"],
        )
        assert result.is_valid is False


class TestTrainingLoadCheck:
    """训练量范围检查测试"""

    def setup_method(self):
        self.validator = LLMOutputValidator()

    def test_no_capacity_skips_check(self):
        """无用户能力数据时跳过检查"""
        result = self.validator.validate("使用100kg做卧推", user_capacity=None)
        assert result.is_valid is True

    def test_within_range_passes(self):
        """训练量在安全范围内通过"""
        result = self.validator.validate(
            "建议使用80kg做卧推，每组10次，共4组",
            user_capacity={"max_weight_kg": 80, "max_reps": 12, "max_sets": 5},
        )
        assert result.is_valid is True

    def test_weight_overload_detected(self):
        """检测到重量超标"""
        result = self.validator.validate(
            "建议使用120kg做卧推",
            user_capacity={"max_weight_kg": 80},  # 120% = 96kg
        )
        assert result.is_valid is False
        assert len(result.overload_violations) == 1
        assert "重量" in result.overload_violations[0]

    def test_reps_overload_detected(self):
        """检测到次数超标"""
        result = self.validator.validate(
            "每组做30次俯卧撑",
            user_capacity={"max_reps": 15},  # 120% = 18次
        )
        assert result.is_valid is False
        assert "次数" in result.overload_violations[0]

    def test_sets_overload_detected(self):
        """检测到组数超标"""
        result = self.validator.validate(
            "做10组深蹲",
            user_capacity={"max_sets": 5},  # 120% = 6组
        )
        assert result.is_valid is False
        assert "组数" in result.overload_violations[0]

    def test_at_threshold_passes(self):
        """刚好在120%阈值内通过"""
        result = self.validator.validate(
            "建议使用96kg做卧推",
            user_capacity={"max_weight_kg": 80},  # 120% = 96kg
        )
        assert result.is_valid is True


class TestApplyToAnalysis:
    """apply_to_analysis测试"""

    def setup_method(self):
        self.validator = LLMOutputValidator()

    def test_no_violations_unchanged(self):
        """无违规时不修改结果"""
        analysis = MockAnalysisResult(confidence=0.85)
        validation = ValidationResult()
        result = self.validator.apply_to_analysis(analysis, validation)
        assert result.confidence == 0.85

    def test_violations_lower_confidence(self):
        """有违规时降低置信度到0.3"""
        analysis = MockAnalysisResult(confidence=0.85)
        validation = ValidationResult(
            contraindication_violations=["推荐了禁忌动作深蹲"],
        )
        result = self.validator.apply_to_analysis(analysis, validation)
        assert result.confidence == 0.3

    def test_violations_add_safety_reminders(self):
        """有违规时附加安全警告"""
        analysis = MockAnalysisResult()
        validation = ValidationResult(
            contraindication_violations=["推荐了禁忌动作深蹲"],
            overload_violations=["重量超标"],
        )
        result = self.validator.apply_to_analysis(analysis, validation)
        assert len(result.safety_reminders) == 2
        assert any("安全警告" in r for r in result.safety_reminders)
        assert any("训练量警告" in r for r in result.safety_reminders)

    def test_violations_mark_metadata(self):
        """有违规时在元数据中标记"""
        analysis = MockAnalysisResult()
        validation = ValidationResult(
            contraindication_violations=["v1", "v2"],
        )
        result = self.validator.apply_to_analysis(analysis, validation)
        assert result.analysis_metadata["validation_failed"] is True
        assert result.analysis_metadata["violation_count"] == 2
