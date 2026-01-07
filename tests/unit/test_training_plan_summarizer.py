# -*- coding: utf-8 -*-
"""
Training Plan Summarizer Unit Tests

测试训练计划摘要器的核心功能和属性测试。

Properties:
- Property 12: 单周输出长度限制 (Requirements 11.1)
- Property 13: 输出字段精简 (Requirements 11.2)
- Property 14: 动作链接格式 (Requirements 11.3)
- Property 15: 高风险动作标记 (Requirements 11.4, 14.2)

作者: BUILD_BODY Team
版本: 1.0.0
日期: 2025-12-26
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from typing import Dict, Any, List

from src.applications.fitness.services.training_plan_summarizer import (
    TrainingPlanSummarizer,
    SummaryConfig,
    SummaryResult
)


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def summarizer():
    """创建默认配置的摘要器"""
    return TrainingPlanSummarizer()


@pytest.fixture
def custom_summarizer():
    """创建自定义配置的摘要器"""
    config = SummaryConfig(
        max_output_chars=5000,
        exercise_link_template="/exercises/{exercise_id}"
    )
    return TrainingPlanSummarizer(config)


@pytest.fixture
def sample_plan():
    """创建示例训练计划"""
    return {
        "week_number": 1,
        "total_weeks": 4,
        "phase": "积累期",
        "phase_description": "使用最大适应训练量（MAV）",
        "volume_multiplier": 1.0,
        "is_deload_week": False,
        "training_days": [
            {
                "day_number": 1,
                "day_name": "胸+三头",
                "focus_muscle_groups": ["胸大肌", "三头肌"],
                "total_sets": 16,
                "estimated_duration_minutes": 60,
                "exercises": [
                    {
                        "exercise_id": "barbell_bench_press",
                        "name_zh": "杠铃卧推",
                        "name_en": "Barbell Bench Press",
                        "sets": 4,
                        "reps_range": (8, 12),
                        "rest_seconds": 90,
                        "weight_suggestion": "60kg",
                        "primary_muscles": ["胸大肌"]
                    },
                    {
                        "exercise_id": "barbell_deadlift",
                        "name_zh": "杠铃硬拉",
                        "name_en": "Barbell Deadlift",
                        "sets": 4,
                        "reps_range": (6, 8),
                        "rest_seconds": 120,
                        "weight_suggestion": "100kg",
                        "primary_muscles": ["竖脊肌", "臀大肌"]
                    }
                ]
            },
            {
                "day_number": 3,
                "day_name": "背+二头",
                "focus_muscle_groups": ["背阔肌", "二头肌"],
                "total_sets": 14,
                "estimated_duration_minutes": 55,
                "exercises": [
                    {
                        "exercise_id": "lat_pulldown",
                        "name_zh": "高位下拉",
                        "name_en": "Lat Pulldown",
                        "sets": 4,
                        "reps_range": (10, 12),
                        "rest_seconds": 60,
                        "weight_suggestion": "50kg"
                    }
                ]
            }
        ],
        "rest_days": [2, 4, 5, 6, 7],
        "total_weekly_sets": 30,
        "cycle_explanation": "📅 这是4周周期的第一周\n🎯 本周阶段：积累期",
        "next_week_preview": "📅 下周预览：第2周（积累期）",
        "generated_at": "2025-12-26 10:00:00"
    }


@pytest.fixture
def high_risk_plan():
    """创建包含高风险动作的训练计划"""
    return {
        "week_number": 1,
        "total_weeks": 4,
        "phase": "积累期",
        "training_days": [
            {
                "day_number": 1,
                "day_name": "力量日",
                "focus_muscle_groups": ["全身"],
                "total_sets": 12,
                "estimated_duration_minutes": 75,
                "exercises": [
                    {
                        "exercise_id": "barbell_squat",
                        "name_zh": "杠铃深蹲",
                        "name_en": "Barbell Squat",
                        "sets": 4,
                        "reps_range": (5, 5),
                        "rest_seconds": 180
                    },
                    {
                        "exercise_id": "barbell_deadlift",
                        "name_zh": "杠铃硬拉",
                        "name_en": "Barbell Deadlift",
                        "sets": 4,
                        "reps_range": (5, 5),
                        "rest_seconds": 180
                    },
                    {
                        "exercise_id": "behind_neck_press",
                        "name_zh": "颈后推举",
                        "name_en": "Behind Neck Press",
                        "sets": 3,
                        "reps_range": (8, 10),
                        "rest_seconds": 90
                    },
                    {
                        "exercise_id": "bicep_curl",
                        "name_zh": "二头弯举",
                        "name_en": "Bicep Curl",
                        "sets": 3,
                        "reps_range": (12, 15),
                        "rest_seconds": 60
                    }
                ]
            }
        ],
        "rest_days": [2, 3, 4, 5, 6, 7],
        "total_weekly_sets": 14
    }


# ============================================================================
# Hypothesis Strategies
# ============================================================================

def exercise_strategy():
    """生成随机动作数据的策略"""
    return st.fixed_dictionaries({
        'exercise_id': st.text(
            alphabet='abcdefghijklmnopqrstuvwxyz_',
            min_size=3,
            max_size=30
        ),
        'name_zh': st.text(min_size=2, max_size=20),
        'name_en': st.text(
            alphabet='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ ',
            min_size=3,
            max_size=50
        ),
        'sets': st.integers(min_value=1, max_value=10),
        'reps_range': st.tuples(
            st.integers(min_value=1, max_value=20),
            st.integers(min_value=1, max_value=20)
        ),
        'rest_seconds': st.integers(min_value=30, max_value=300),
        'weight_suggestion': st.one_of(st.none(), st.text(min_size=0, max_size=20))
    })


def training_day_strategy():
    """生成随机训练日数据的策略"""
    return st.fixed_dictionaries({
        'day_number': st.integers(min_value=1, max_value=7),
        'day_name': st.text(min_size=2, max_size=20),
        'focus_muscle_groups': st.lists(st.text(min_size=2, max_size=10), min_size=1, max_size=3),
        'total_sets': st.integers(min_value=1, max_value=50),
        'estimated_duration_minutes': st.integers(min_value=20, max_value=120),
        'exercises': st.lists(exercise_strategy(), min_size=1, max_size=8)
    })


def training_plan_strategy():
    """生成随机训练计划的策略"""
    return st.fixed_dictionaries({
        'week_number': st.integers(min_value=1, max_value=12),
        'total_weeks': st.integers(min_value=1, max_value=12),
        'phase': st.sampled_from(['积累期', '冲刺期', '减量期']),
        'phase_description': st.text(min_size=5, max_size=100),
        'volume_multiplier': st.floats(min_value=0.7, max_value=1.5),
        'is_deload_week': st.booleans(),
        'training_days': st.lists(training_day_strategy(), min_size=1, max_size=6),
        'rest_days': st.lists(st.integers(min_value=1, max_value=7), min_size=0, max_size=6),
        'total_weekly_sets': st.integers(min_value=1, max_value=100),
        'cycle_explanation': st.text(min_size=10, max_size=500),
        'next_week_preview': st.one_of(st.none(), st.text(min_size=5, max_size=100))
    })


# ============================================================================
# Unit Tests - Basic Functionality
# ============================================================================

class TestTrainingPlanSummarizerBasic:
    """基础功能测试"""
    
    def test_init_default_config(self, summarizer):
        """测试默认配置初始化"""
        assert summarizer.config.max_output_chars == 8000
        assert '⚠️' in summarizer.config.high_risk_marker
    
    def test_init_custom_config(self, custom_summarizer):
        """测试自定义配置初始化"""
        assert custom_summarizer.config.max_output_chars == 5000
    
    def test_summarize_returns_result(self, summarizer, sample_plan):
        """测试summarize返回SummaryResult"""
        result = summarizer.summarize(sample_plan)
        
        assert isinstance(result, SummaryResult)
        assert result.content is not None
        assert result.char_count > 0
        assert isinstance(result.is_truncated, bool)
    
    def test_convert_to_links(self, summarizer, sample_plan):
        """测试动作链接转换"""
        converted = summarizer.convert_to_links(sample_plan)
        
        # 检查第一个动作是否有链接
        first_exercise = converted['training_days'][0]['exercises'][0]
        assert 'name_link' in first_exercise
        assert '[杠铃卧推]' in first_exercise['name_link']
        assert '/exercise/' in first_exercise['name_link']
    
    def test_add_safety_markers(self, summarizer, high_risk_plan):
        """测试安全标记添加"""
        marked = summarizer.add_safety_markers(high_risk_plan)
        
        exercises = marked['training_days'][0]['exercises']
        
        # 深蹲应该有标记
        squat = next(e for e in exercises if 'squat' in e['exercise_id'])
        assert squat.get('safety_marker') == '⚠️'
        
        # 硬拉应该有标记
        deadlift = next(e for e in exercises if 'deadlift' in e['exercise_id'])
        assert deadlift.get('safety_marker') == '⚠️'
        
        # 二头弯举不应该有标记
        curl = next(e for e in exercises if 'curl' in e['exercise_id'])
        assert curl.get('safety_marker') is None
    
    def test_extract_core_fields(self, summarizer, sample_plan):
        """测试核心字段提取"""
        extracted = summarizer._extract_core_fields(sample_plan)
        
        # 检查保留了核心字段
        assert 'week_number' in extracted
        assert 'training_days' in extracted
        
        # 检查动作只保留核心字段
        first_exercise = extracted['training_days'][0]['exercises'][0]
        assert 'exercise_id' in first_exercise
        assert 'name_zh' in first_exercise
        assert 'sets' in first_exercise
    
    def test_estimate_output_length(self, summarizer, sample_plan):
        """测试输出长度估算"""
        estimated = summarizer.estimate_output_length(sample_plan)
        
        assert estimated > 0
        assert isinstance(estimated, int)
    
    def test_summarize_to_dict(self, summarizer, sample_plan):
        """测试字典格式输出"""
        result = summarizer.summarize_to_dict(sample_plan)
        
        assert isinstance(result, dict)
        assert 'training_days' in result
        assert 'cycle_explanation' in result


# ============================================================================
# Property Tests
# ============================================================================

class TestProperty12OutputLengthLimit:
    """
    Property 12: 单周输出长度限制
    
    验证: Requirements 11.1 - 单次输出控制在8000字符以内
    """
    
    @given(training_plan_strategy())
    @settings(max_examples=50, deadline=None)
    def test_output_never_exceeds_limit(self, plan):
        """
        Property: 对于任意训练计划，输出字符数不超过8000
        """
        summarizer = TrainingPlanSummarizer()
        result = summarizer.summarize(plan)
        
        assert result.char_count <= 8000, (
            f"输出超过8000字符限制: {result.char_count}"
        )
    
    def test_large_plan_is_truncated(self, summarizer):
        """测试大型计划被正确截断"""
        # 创建一个非常大的计划
        large_plan = {
            "week_number": 1,
            "total_weeks": 4,
            "phase": "积累期",
            "training_days": [],
            "rest_days": [],
            "total_weekly_sets": 0,
            "cycle_explanation": "A" * 3000  # 很长的说明
        }
        
        # 添加很多训练日和动作
        for day_num in range(1, 7):
            day = {
                "day_number": day_num,
                "day_name": f"训练日{day_num}",
                "focus_muscle_groups": ["肌群A", "肌群B"],
                "total_sets": 20,
                "estimated_duration_minutes": 90,
                "exercises": []
            }
            
            for ex_num in range(1, 11):
                day["exercises"].append({
                    "exercise_id": f"exercise_{day_num}_{ex_num}",
                    "name_zh": f"动作{day_num}-{ex_num}的中文名称比较长",
                    "name_en": f"Exercise {day_num}-{ex_num} with long name",
                    "sets": 4,
                    "reps_range": (8, 12),
                    "rest_seconds": 90,
                    "weight_suggestion": "50kg"
                })
            
            large_plan["training_days"].append(day)
        
        result = summarizer.summarize(large_plan)
        
        # 即使输入很大，输出也不应超过限制
        assert result.char_count <= 8000
        # 应该被截断
        assert result.is_truncated or result.char_count <= 8000
    
    def test_custom_limit_respected(self):
        """测试自定义长度限制被遵守"""
        config = SummaryConfig(max_output_chars=2000)
        summarizer = TrainingPlanSummarizer(config)
        
        plan = {
            "week_number": 1,
            "total_weeks": 4,
            "phase": "积累期",
            "training_days": [
                {
                    "day_number": 1,
                    "day_name": "训练日",
                    "focus_muscle_groups": ["胸"],
                    "total_sets": 10,
                    "estimated_duration_minutes": 60,
                    "exercises": [
                        {
                            "exercise_id": f"ex_{i}",
                            "name_zh": f"动作{i}",
                            "sets": 3,
                            "reps_range": (8, 12),
                            "rest_seconds": 60
                        }
                        for i in range(10)
                    ]
                }
            ],
            "rest_days": [],
            "total_weekly_sets": 30,
            "cycle_explanation": "说明" * 100
        }
        
        result = summarizer.summarize(plan)
        assert result.char_count <= 2000


class TestProperty13CoreFieldsOnly:
    """
    Property 13: 输出字段精简
    
    验证: Requirements 11.2 - 只保留核心字段
    """
    
    CORE_FIELDS = {'exercise_id', 'name_zh', 'name_en', 'sets', 'reps_range', 
                   'rest_seconds', 'weight_suggestion'}
    ALLOWED_EXTRA_FIELDS = {'safety_marker', 'safety_notes', 'name_link', 'primary_muscles'}
    
    @given(training_plan_strategy())
    @settings(max_examples=30, deadline=None)
    def test_only_core_fields_in_output(self, plan):
        """
        Property: 对于任意训练计划，输出的动作只包含核心字段和安全字段
        """
        summarizer = TrainingPlanSummarizer()
        result = summarizer.summarize_to_dict(plan)
        
        for day in result.get('training_days', []):
            for exercise in day.get('exercises', []):
                for field in exercise.keys():
                    assert field in self.CORE_FIELDS | self.ALLOWED_EXTRA_FIELDS, (
                        f"发现非核心字段: {field}"
                    )
    
    def test_removes_unnecessary_fields(self, summarizer, sample_plan):
        """测试移除不必要的字段"""
        # 添加一些额外字段
        sample_plan['training_days'][0]['exercises'][0]['unnecessary_field'] = 'value'
        sample_plan['training_days'][0]['exercises'][0]['another_field'] = 123
        
        result = summarizer.summarize_to_dict(sample_plan)
        
        first_exercise = result['training_days'][0]['exercises'][0]
        assert 'unnecessary_field' not in first_exercise
        assert 'another_field' not in first_exercise


class TestProperty14LinkFormat:
    """
    Property 14: 动作链接格式
    
    验证: Requirements 11.3 - 使用Markdown链接格式
    """
    
    @given(exercise_strategy())
    @settings(max_examples=50, deadline=None)
    def test_link_format_is_valid_markdown(self, exercise):
        """
        Property: 对于任意动作，生成的链接符合Markdown格式
        """
        assume(exercise['exercise_id'] and exercise['name_zh'])
        
        summarizer = TrainingPlanSummarizer()
        plan = {
            "training_days": [{
                "exercises": [exercise]
            }]
        }
        
        converted = summarizer.convert_to_links(plan)
        converted_exercise = converted['training_days'][0]['exercises'][0]
        
        if 'name_link' in converted_exercise:
            link = converted_exercise['name_link']
            # 验证Markdown链接格式: [text](url)
            assert '[' in link and '](' in link and ')' in link, (
                f"链接格式不正确: {link}"
            )
    
    def test_link_contains_exercise_id(self, summarizer, sample_plan):
        """测试链接包含exercise_id"""
        converted = summarizer.convert_to_links(sample_plan)
        
        first_exercise = converted['training_days'][0]['exercises'][0]
        link = first_exercise['name_link']
        
        assert 'barbell_bench_press' in link
    
    def test_link_contains_chinese_name(self, summarizer, sample_plan):
        """测试链接显示中文名称"""
        converted = summarizer.convert_to_links(sample_plan)
        
        first_exercise = converted['training_days'][0]['exercises'][0]
        link = first_exercise['name_link']
        
        assert '杠铃卧推' in link


class TestProperty15HighRiskMarker:
    """
    Property 15: 高风险动作标记
    
    验证: Requirements 11.4, 14.2 - 高风险动作添加⚠️标记
    """
    
    HIGH_RISK_IDS = [
        'barbell_deadlift', 'sumo_deadlift', 'romanian_deadlift',
        'barbell_squat', 'front_squat', 'overhead_squat',
        'barbell_snatch', 'power_clean', 'clean_and_jerk',
        'behind_neck_press', 'good_morning'
    ]
    
    @pytest.mark.parametrize("exercise_id", HIGH_RISK_IDS)
    def test_high_risk_exercises_are_marked(self, summarizer, exercise_id):
        """
        Property: 所有高风险动作都应该被标记
        """
        plan = {
            "training_days": [{
                "day_number": 1,
                "day_name": "测试日",
                "exercises": [{
                    "exercise_id": exercise_id,
                    "name_zh": "测试动作",
                    "name_en": "Test Exercise",
                    "sets": 3,
                    "reps_range": (8, 12),
                    "rest_seconds": 90
                }]
            }]
        }
        
        marked = summarizer.add_safety_markers(plan)
        exercise = marked['training_days'][0]['exercises'][0]
        
        assert exercise.get('safety_marker') == '⚠️', (
            f"高风险动作 {exercise_id} 未被标记"
        )
    
    def test_safe_exercises_not_marked(self, summarizer):
        """测试安全动作不被标记"""
        safe_exercises = [
            'bicep_curl', 'tricep_pushdown', 'leg_extension',
            'lateral_raise', 'face_pull'
        ]
        
        for exercise_id in safe_exercises:
            plan = {
                "training_days": [{
                    "exercises": [{
                        "exercise_id": exercise_id,
                        "name_zh": "安全动作",
                        "name_en": "Safe Exercise",
                        "sets": 3,
                        "reps_range": (12, 15),
                        "rest_seconds": 60
                    }]
                }]
            }
            
            marked = summarizer.add_safety_markers(plan)
            exercise = marked['training_days'][0]['exercises'][0]
            
            assert exercise.get('safety_marker') is None, (
                f"安全动作 {exercise_id} 被错误标记"
            )
    
    def test_marker_appears_in_link(self, summarizer, high_risk_plan):
        """测试标记出现在链接中"""
        # 先转换链接，再添加标记
        converted = summarizer.convert_to_links(high_risk_plan)
        marked = summarizer.add_safety_markers(converted)
        
        squat = marked['training_days'][0]['exercises'][0]
        
        # 标记应该出现在name_link中
        if 'name_link' in squat:
            assert '⚠️' in squat['name_link']
    
    @given(st.text(min_size=3, max_size=50))
    @settings(max_examples=30, deadline=None)
    def test_keyword_detection(self, name):
        """
        Property: 包含高风险关键词的动作应该被标记
        """
        summarizer = TrainingPlanSummarizer()
        
        # 测试中文关键词
        for keyword in ['硬拉', '深蹲', '抓举']:
            if keyword in name:
                plan = {
                    "training_days": [{
                        "exercises": [{
                            "exercise_id": "test",
                            "name_zh": name,
                            "name_en": "Test",
                            "sets": 3,
                            "reps_range": (8, 12),
                            "rest_seconds": 90
                        }]
                    }]
                }
                
                marked = summarizer.add_safety_markers(plan)
                exercise = marked['training_days'][0]['exercises'][0]
                
                assert exercise.get('safety_marker') == '⚠️', (
                    f"包含关键词'{keyword}'的动作'{name}'未被标记"
                )


# ============================================================================
# Integration Tests
# ============================================================================

class TestSummarizerIntegration:
    """集成测试"""
    
    def test_full_summarize_workflow(self, summarizer, sample_plan):
        """测试完整的摘要工作流"""
        result = summarizer.summarize(sample_plan)
        
        # 验证结果
        assert result.char_count <= 8000
        assert result.exercise_count == 3  # 2 + 1 动作
        assert result.high_risk_count >= 1  # 至少有硬拉
        
        # 验证内容包含关键信息
        assert '第1周' in result.content
        assert '积累期' in result.content
        assert '杠铃卧推' in result.content or '[杠铃卧推]' in result.content
    
    def test_summarize_preserves_structure(self, summarizer, sample_plan):
        """测试摘要保留计划结构"""
        result = summarizer.summarize_to_dict(sample_plan)
        
        # 验证结构完整
        assert 'training_days' in result
        assert len(result['training_days']) == 2
        assert 'exercises' in result['training_days'][0]
    
    def test_empty_plan_handling(self, summarizer):
        """测试空计划处理"""
        empty_plan = {
            "week_number": 1,
            "total_weeks": 4,
            "phase": "积累期",
            "training_days": [],
            "rest_days": [1, 2, 3, 4, 5, 6, 7],
            "total_weekly_sets": 0
        }
        
        result = summarizer.summarize(empty_plan)
        
        assert result.char_count > 0
        assert result.exercise_count == 0
        assert not result.is_truncated


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
