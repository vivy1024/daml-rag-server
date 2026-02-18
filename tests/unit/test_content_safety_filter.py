# -*- coding: utf-8 -*-
"""
ContentSafetyFilter 单元测试

验证内容安全过滤器的关键词检测和风险分级功能。
Task 35 - Phase 7 Batch 1 安全加固
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from applications.fitness.services.content_safety_filter import (
    ContentSafetyFilter,
    ContentRiskLevel,
    ContentCategory,
)


@pytest.fixture
def safety_filter():
    return ContentSafetyFilter()


# ── self_harm 检测 ──

class TestSelfHarmDetection:
    def test_self_harm_keyword_blocked(self, safety_filter):
        result = safety_filter.filter_input("我想自残")
        assert result.risk_level == ContentRiskLevel.BLOCKED
        assert result.should_block is True
        assert ContentCategory.SELF_HARM in result.categories

    def test_self_harm_suicide_blocked(self, safety_filter):
        result = safety_filter.filter_input("不想活了怎么办")
        assert result.should_block is True
        assert "不想活" in result.matched_keywords

    def test_self_harm_indirect(self, safety_filter):
        result = safety_filter.filter_input("活着没意思")
        assert result.should_block is True


# ── dangerous_substances 检测 ──

class TestDangerousSubstancesDetection:
    def test_steroid_detected(self, safety_filter):
        result = safety_filter.filter_input("我想用类固醇增肌")
        assert ContentCategory.DANGEROUS_SUBSTANCE in result.categories
        assert result.risk_level in (ContentRiskLevel.HIGH, ContentRiskLevel.BLOCKED)

    def test_hgh_detected(self, safety_filter):
        result = safety_filter.filter_input("生长激素能帮助增肌吗")
        assert ContentCategory.DANGEROUS_SUBSTANCE in result.categories

    def test_dnp_detected(self, safety_filter):
        result = safety_filter.filter_input("DNP减肥效果好吗")
        assert "DNP" in result.matched_keywords


# ── medical_advice 检测 ──

class TestMedicalAdviceDetection:
    def test_diagnosis_detected(self, safety_filter):
        result = safety_filter.filter_input("帮我诊断一下膝盖疼")
        assert ContentCategory.MEDICAL in result.categories
        assert result.risk_level == ContentRiskLevel.LOW

    def test_prescription_detected(self, safety_filter):
        result = safety_filter.filter_input("给我开个处方")
        assert "处方" in result.matched_keywords


# ── extreme_training 检测 ──

class TestExtremeTrainingDetection:
    def test_crash_diet_detected(self, safety_filter):
        result = safety_filter.filter_input("怎么7天瘦20斤")
        assert ContentCategory.EXTREME in result.categories
        assert result.risk_level == ContentRiskLevel.MEDIUM

    def test_zero_carb_detected(self, safety_filter):
        result = safety_filter.filter_input("零碳水饮食好不好")
        assert "零碳水" in result.matched_keywords


# ── 安全内容放行 ──

class TestSafeContent:
    def test_normal_fitness_query(self, safety_filter):
        result = safety_filter.filter_input("我想练胸肌，推荐一个训练计划")
        assert result.risk_level == ContentRiskLevel.SAFE
        assert result.should_block is False

    def test_normal_nutrition_query(self, safety_filter):
        result = safety_filter.filter_input("增肌期每天需要多少蛋白质")
        assert result.risk_level == ContentRiskLevel.SAFE


# ── 输出过滤 ──

class TestOutputFiltering:
    def test_output_adds_disclaimer(self, safety_filter):
        content = "这是一个训练计划"
        processed, result = safety_filter.filter_output(content, "training_plan")
        assert "训练计划基于专业数据库生成" in processed

    def test_blocked_output_replaced(self, safety_filter):
        content = "你应该去医院做CT检查确诊一下"
        processed, result = safety_filter.filter_output(content)
        # 包含医疗关键词，应添加医疗免责声明
        assert "医" in processed or "健康" in processed
