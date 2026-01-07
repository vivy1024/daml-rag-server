# -*- coding: utf-8 -*-
"""
Safety Reminder Generator Unit Tests

测试安全提醒生成器的核心功能和属性测试。

Properties:
- Property 16: 免责声明存在性 (Requirements 14.1)
- Property 17: 损伤历史提醒 (Requirements 14.3)

作者: BUILD_BODY Team
版本: 1.0.0
日期: 2025-12-26
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from typing import Dict, Any, List

from src.applications.fitness.services.safety_reminder_generator import (
    SafetyReminderGenerator,
    SafetyConfig,
    SafetyReminder
)


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def generator():
    """创建默认配置的安全提醒生成器"""
    return SafetyReminderGenerator()


@pytest.fixture
def custom_generator():
    """创建自定义配置的安全提醒生成器"""
    config = SafetyConfig(
        high_risk_marker="🔴",
        include_disclaimer=True,
        include_injury_reminder=True
    )
    return SafetyReminderGenerator(config)


@pytest.fixture
def sample_user_profile():
    """创建示例用户档案"""
    return {
        "user_id": "test_user_001",
        "name": "测试用户",
        "injury_history": [
            {"body_part": "shoulder", "date": "2024-06-15", "status": "recovered"},
            {"body_part": "lower_back", "date": "2024-03-20", "status": "active"}
        ]
    }


@pytest.fixture
def sample_exercises():
    """创建示例动作列表"""
    return [
        {
            "exercise_id": "barbell_squat",
            "name_zh": "杠铃深蹲",
            "name_en": "Barbell Squat",
            "sets": 4,
            "reps_range": (5, 5)
        },
        {
            "exercise_id": "barbell_deadlift",
            "name_zh": "杠铃硬拉",
            "name_en": "Barbell Deadlift",
            "sets": 4,
            "reps_range": (5, 5)
        },
        {
            "exercise_id": "bicep_curl",
            "name_zh": "二头弯举",
            "name_en": "Bicep Curl",
            "sets": 3,
            "reps_range": (12, 15)
        },
        {
            "exercise_id": "lat_pulldown",
            "name_zh": "高位下拉",
            "name_en": "Lat Pulldown",
            "sets": 3,
            "reps_range": (10, 12)
        }
    ]


# ============================================================================
# Hypothesis Strategies
# ============================================================================

def injury_strategy():
    """生成随机损伤记录的策略"""
    body_parts = ['shoulder', 'knee', 'lower_back', 'wrist', 'elbow', 
                  'neck', 'hip', 'ankle', 'rotator_cuff', 'spine']
    statuses = ['active', 'recovered', 'chronic', 'unknown']
    
    return st.fixed_dictionaries({
        'body_part': st.sampled_from(body_parts),
        'date': st.one_of(
            st.none(),
            st.text(
                alphabet='0123456789-',
                min_size=10,
                max_size=10
            )
        ),
        'status': st.sampled_from(statuses)
    })


def user_profile_strategy():
    """生成随机用户档案的策略"""
    return st.fixed_dictionaries({
        'user_id': st.text(min_size=1, max_size=20),
        'name': st.text(min_size=1, max_size=50),
        'injury_history': st.lists(injury_strategy(), min_size=0, max_size=5)
    })


def user_profile_with_injuries_strategy():
    """生成带有损伤历史的用户档案策略"""
    return st.fixed_dictionaries({
        'user_id': st.text(min_size=1, max_size=20),
        'name': st.text(min_size=1, max_size=50),
        'injury_history': st.lists(injury_strategy(), min_size=1, max_size=5)
    })


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
        )
    })


# ============================================================================
# Unit Tests - Basic Functionality
# ============================================================================

class TestSafetyReminderGeneratorBasic:
    """基础功能测试"""
    
    def test_init_default_config(self, generator):
        """测试默认配置初始化"""
        assert generator.config.high_risk_marker == "⚠️"
        assert generator.config.include_disclaimer is True
        assert generator.config.include_injury_reminder is True
    
    def test_init_custom_config(self, custom_generator):
        """测试自定义配置初始化"""
        assert custom_generator.config.high_risk_marker == "🔴"
    
    def test_generate_disclaimer_returns_string(self, generator):
        """测试免责声明返回字符串"""
        disclaimer = generator.generate_disclaimer()
        
        assert isinstance(disclaimer, str)
        assert len(disclaimer) > 0
    
    def test_generate_injury_reminder_with_injuries(self, generator, sample_user_profile):
        """测试有损伤历史时生成提醒"""
        reminder = generator.generate_injury_reminder(sample_user_profile)
        
        assert isinstance(reminder, str)
        assert len(reminder) > 0
        assert "肩部" in reminder or "shoulder" in reminder
    
    def test_generate_injury_reminder_without_injuries(self, generator):
        """测试无损伤历史时返回空字符串"""
        user_profile = {
            "user_id": "test_user",
            "injury_history": []
        }
        
        reminder = generator.generate_injury_reminder(user_profile)
        
        assert reminder == ""
    
    def test_mark_high_risk_exercises(self, generator, sample_exercises):
        """测试高风险动作标记"""
        marked = generator.mark_high_risk_exercises(sample_exercises)
        
        assert len(marked) == len(sample_exercises)
        
        # 深蹲应该被标记
        squat = next(e for e in marked if e['exercise_id'] == 'barbell_squat')
        assert squat.get('safety_marker') == '⚠️'
        assert squat.get('is_high_risk') is True
        
        # 二头弯举不应该被标记
        curl = next(e for e in marked if e['exercise_id'] == 'bicep_curl')
        assert curl.get('safety_marker') is None
        assert curl.get('is_high_risk') is False
    
    def test_get_contraindications(self, generator):
        """测试获取禁忌条件"""
        contras = generator.get_contraindications('barbell_deadlift')
        
        assert isinstance(contras, list)
        assert len(contras) > 0
        assert any('背' in c or 'back' in c.lower() for c in contras)
    
    def test_get_contraindications_unknown_exercise(self, generator):
        """测试未知动作的禁忌条件"""
        contras = generator.get_contraindications('unknown_exercise')
        
        assert isinstance(contras, list)
        # 未知动作返回空列表
        assert len(contras) == 0
    
    def test_get_exercises_to_avoid(self, generator):
        """测试根据损伤获取应避免的动作"""
        injury_history = [
            {"body_part": "shoulder"},
            {"body_part": "lower_back"}
        ]
        
        to_avoid = generator.get_exercises_to_avoid(injury_history)
        
        assert isinstance(to_avoid, list)
        assert len(to_avoid) > 0
        # 肩部损伤应该避免颈后推举
        assert 'behind_neck_press' in to_avoid
        # 下背部损伤应该避免硬拉
        assert 'barbell_deadlift' in to_avoid


# ============================================================================
# Property Tests
# ============================================================================

class TestProperty16DisclaimerExistence:
    """
    Property 16: 免责声明存在性
    
    **Feature: training-plan-china-localization, Property 16: 免责声明存在性**
    **Validates: Requirements 14.1**
    
    验证: Requirements 14.1 - 输出训练计划时在计划开头添加免责声明
    """
    
    def test_disclaimer_always_exists(self, generator):
        """
        Property: 免责声明始终存在且非空
        """
        disclaimer = generator.generate_disclaimer()
        
        assert disclaimer is not None
        assert len(disclaimer) > 0
    
    def test_disclaimer_contains_required_elements(self, generator):
        """
        Property: 免责声明包含必要元素
        """
        disclaimer = generator.generate_disclaimer()
        
        # 必须包含安全提醒标记
        assert "⚠️" in disclaimer or "重要" in disclaimer or "安全" in disclaimer
        
        # 必须包含免责声明关键词
        assert "免责" in disclaimer or "声明" in disclaimer or "建议" in disclaimer
    
    def test_disclaimer_mentions_professional_consultation(self, generator):
        """
        Property: 免责声明提及专业咨询
        """
        disclaimer = generator.generate_disclaimer()
        
        # 应该提及咨询专业人士
        assert any(keyword in disclaimer for keyword in [
            "咨询", "医生", "教练", "专业", "professional"
        ])
    
    @given(st.booleans())
    @settings(max_examples=10, deadline=None)
    def test_disclaimer_format_consistent(self, include_disclaimer):
        """
        Property: 无论配置如何，generate_disclaimer方法始终返回有效免责声明
        """
        config = SafetyConfig(include_disclaimer=include_disclaimer)
        generator = SafetyReminderGenerator(config)
        
        # generate_disclaimer方法本身始终返回免责声明
        # include_disclaimer配置只影响generate_full_safety_section
        disclaimer = generator.generate_disclaimer()
        
        assert isinstance(disclaimer, str)
        assert len(disclaimer) > 100  # 免责声明应该有足够长度
    
    def test_full_safety_section_includes_disclaimer(self, generator):
        """
        Property: 完整安全部分包含免责声明
        """
        result = generator.generate_full_safety_section()
        
        assert result.disclaimer is not None
        assert len(result.disclaimer) > 0
    
    def test_formatted_output_starts_with_disclaimer(self, generator):
        """
        Property: 格式化输出以免责声明开头
        """
        result = generator.generate_full_safety_section()
        formatted = generator.format_safety_section(result)
        
        # 格式化输出应该以免责声明开头
        assert formatted.startswith("⚠️") or "重要" in formatted[:100]


class TestProperty17InjuryHistoryReminder:
    """
    Property 17: 损伤历史提醒
    
    **Feature: training-plan-china-localization, Property 17: 损伤历史提醒**
    **Validates: Requirements 14.3**
    
    验证: Requirements 14.3 - 用户有损伤历史时在计划开头添加针对性提醒
    """
    
    @given(user_profile_with_injuries_strategy())
    @settings(max_examples=50, deadline=None)
    def test_injury_reminder_generated_when_injuries_exist(self, user_profile):
        """
        Property: 对于任意有损伤历史的用户，系统应该生成损伤提醒
        """
        generator = SafetyReminderGenerator()
        reminder = generator.generate_injury_reminder(user_profile)
        
        # 有损伤历史时，提醒不应为空
        assert reminder is not None
        assert len(reminder) > 0, (
            f"用户有{len(user_profile['injury_history'])}个损伤记录，但未生成提醒"
        )
    
    @given(user_profile_strategy())
    @settings(max_examples=30, deadline=None)
    def test_no_reminder_when_no_injuries(self, user_profile):
        """
        Property: 对于没有损伤历史的用户，不生成损伤提醒
        """
        # 确保没有损伤历史
        user_profile['injury_history'] = []
        
        generator = SafetyReminderGenerator()
        reminder = generator.generate_injury_reminder(user_profile)
        
        assert reminder == "", "无损伤历史时不应生成提醒"
    
    def test_reminder_mentions_injured_body_parts(self, generator, sample_user_profile):
        """
        Property: 损伤提醒应该提及受伤部位
        """
        reminder = generator.generate_injury_reminder(sample_user_profile)
        
        # 应该提及肩部（shoulder的中文名）
        assert "肩部" in reminder or "肩" in reminder
        # 应该提及下背部
        assert "下背部" in reminder or "背" in reminder
    
    @pytest.mark.parametrize("body_part,expected_zh", [
        ("shoulder", "肩部"),
        ("knee", "膝盖"),
        ("lower_back", "下背部"),
        ("wrist", "手腕"),
        ("elbow", "肘部"),
        ("neck", "颈部"),
        ("hip", "髋部"),
    ])
    def test_body_part_translation(self, generator, body_part, expected_zh):
        """
        Property: 损伤部位应该正确翻译为中文
        """
        user_profile = {
            "injury_history": [{"body_part": body_part}]
        }
        
        reminder = generator.generate_injury_reminder(user_profile)
        
        assert expected_zh in reminder, (
            f"损伤部位'{body_part}'应该翻译为'{expected_zh}'"
        )
    
    def test_reminder_includes_recommendations(self, generator, sample_user_profile):
        """
        Property: 损伤提醒应该包含针对性建议
        """
        reminder = generator.generate_injury_reminder(sample_user_profile)
        
        # 应该包含建议关键词
        assert any(keyword in reminder for keyword in [
            "建议", "避免", "注意", "调整"
        ])
    
    def test_full_safety_section_includes_injury_reminders(self, generator, sample_user_profile):
        """
        Property: 完整安全部分包含损伤提醒
        """
        result = generator.generate_full_safety_section(
            user_profile=sample_user_profile
        )
        
        assert len(result.injury_reminders) > 0
    
    def test_string_format_injury_history_supported(self, generator):
        """
        Property: 支持字符串格式的损伤历史
        """
        user_profile = {
            "injury_history": ["shoulder", "knee"]
        }
        
        reminder = generator.generate_injury_reminder(user_profile)
        
        assert len(reminder) > 0
        assert "肩部" in reminder
        assert "膝盖" in reminder


# ============================================================================
# Additional Unit Tests
# ============================================================================

class TestHighRiskExerciseMarking:
    """高风险动作标记测试"""
    
    HIGH_RISK_IDS = [
        'barbell_deadlift', 'sumo_deadlift', 'romanian_deadlift',
        'barbell_squat', 'front_squat', 'overhead_squat',
        'barbell_snatch', 'power_clean', 'clean_and_jerk',
        'behind_neck_press', 'good_morning'
    ]
    
    @pytest.mark.parametrize("exercise_id", HIGH_RISK_IDS)
    def test_high_risk_exercises_are_marked(self, generator, exercise_id):
        """测试所有高风险动作都被标记"""
        exercises = [{
            "exercise_id": exercise_id,
            "name_zh": "测试动作",
            "name_en": "Test Exercise"
        }]
        
        marked = generator.mark_high_risk_exercises(exercises)
        
        assert marked[0].get('safety_marker') == '⚠️', (
            f"高风险动作 {exercise_id} 未被标记"
        )
        assert marked[0].get('is_high_risk') is True
    
    def test_safe_exercises_not_marked(self, generator):
        """测试安全动作不被标记"""
        safe_exercises = [
            {'exercise_id': 'bicep_curl', 'name_zh': '二头弯举'},
            {'exercise_id': 'tricep_pushdown', 'name_zh': '三头下压'},
            {'exercise_id': 'leg_extension', 'name_zh': '腿屈伸'},
            {'exercise_id': 'lateral_raise', 'name_zh': '侧平举'},
            {'exercise_id': 'face_pull', 'name_zh': '面拉'}
        ]
        
        marked = generator.mark_high_risk_exercises(safe_exercises)
        
        for exercise in marked:
            assert exercise.get('safety_marker') is None, (
                f"安全动作 {exercise['exercise_id']} 被错误标记"
            )
            assert exercise.get('is_high_risk') is False
    
    def test_keyword_detection_in_name(self, generator):
        """测试通过名称关键词检测高风险动作"""
        exercises = [
            {'exercise_id': 'custom_deadlift_variation', 'name_zh': '自定义硬拉变体', 'name_en': 'Custom Deadlift'},
            {'exercise_id': 'custom_squat_variation', 'name_zh': '自定义深蹲变体', 'name_en': 'Custom Squat'}
        ]
        
        marked = generator.mark_high_risk_exercises(exercises)
        
        for exercise in marked:
            assert exercise.get('is_high_risk') is True, (
                f"包含高风险关键词的动作 {exercise['exercise_id']} 未被标记"
            )


class TestContraindications:
    """禁忌条件测试"""
    
    def test_deadlift_contraindications(self, generator):
        """测试硬拉禁忌条件"""
        contras = generator.get_contraindications('barbell_deadlift')
        
        assert len(contras) > 0
        # 应该包含下背部相关禁忌
        assert any('背' in c for c in contras)
    
    def test_squat_contraindications(self, generator):
        """测试深蹲禁忌条件"""
        contras = generator.get_contraindications('barbell_squat')
        
        assert len(contras) > 0
        # 应该包含膝盖相关禁忌
        assert any('膝' in c for c in contras)
    
    def test_behind_neck_press_contraindications(self, generator):
        """测试颈后推举禁忌条件"""
        contras = generator.get_contraindications('behind_neck_press')
        
        assert len(contras) > 0
        # 应该包含肩袖相关禁忌
        assert any('肩' in c for c in contras)


class TestFullSafetySection:
    """完整安全部分测试"""
    
    def test_generate_full_safety_section(self, generator, sample_user_profile, sample_exercises):
        """测试生成完整安全部分"""
        result = generator.generate_full_safety_section(
            user_profile=sample_user_profile,
            exercises=sample_exercises
        )
        
        assert isinstance(result, SafetyReminder)
        assert result.disclaimer is not None
        assert len(result.injury_reminders) > 0
        assert len(result.high_risk_exercises) > 0
        assert result.generated_at is not None
    
    def test_format_safety_section(self, generator, sample_user_profile, sample_exercises):
        """测试格式化安全部分"""
        result = generator.generate_full_safety_section(
            user_profile=sample_user_profile,
            exercises=sample_exercises
        )
        
        formatted = generator.format_safety_section(result)
        
        assert isinstance(formatted, str)
        assert len(formatted) > 0
        # 应该包含免责声明
        assert "⚠️" in formatted
    
    def test_empty_inputs_handling(self, generator):
        """测试空输入处理"""
        result = generator.generate_full_safety_section()
        
        assert result.disclaimer is not None
        assert result.injury_reminders == []
        assert result.high_risk_exercises == []


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
