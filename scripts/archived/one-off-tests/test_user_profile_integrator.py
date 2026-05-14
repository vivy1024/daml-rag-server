# -*- coding: utf-8 -*-
"""
测试用户档案整合器

验证：
1. 默认值策略
2. 容量系数获取
3. 用户类型判断
4. 档案完整性验证
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.applications.fitness.services.user_profile_integrator import (
    UserProfileIntegrator, 
    UserProfileDefaults
)


def test_defaults():
    """测试默认值配置"""
    print("=" * 50)
    print("测试1: 默认值配置")
    print("=" * 50)
    
    defaults = UserProfileDefaults()
    print(f"  DEFAULT_AGE: {defaults.DEFAULT_AGE}")
    print(f"  DEFAULT_HEIGHT: {defaults.DEFAULT_HEIGHT}")
    print(f"  DEFAULT_WEIGHT: {defaults.DEFAULT_WEIGHT}")
    print(f"  DEFAULT_VOLUME_MULTIPLIER: {defaults.DEFAULT_VOLUME_MULTIPLIER}")
    print(f"  DEFAULT_USER_TYPE: {defaults.DEFAULT_USER_TYPE}")
    print("  ✅ 默认值配置测试通过")


def test_apply_defaults():
    """测试默认值填充"""
    print("\n" + "=" * 50)
    print("测试2: 默认值填充")
    print("=" * 50)
    
    class MockBackendClient:
        pass
    
    integrator = UserProfileIntegrator(MockBackendClient())
    
    # 测试不完整档案
    incomplete_profile = {
        'user_id': '1',
        'basic_info': {'age': 30}
    }
    
    complete_profile = integrator._apply_defaults(incomplete_profile)
    
    print(f"  原始档案: {incomplete_profile}")
    print(f"  填充后身高: {complete_profile['basic_info']['height']}")
    print(f"  填充后体重: {complete_profile['basic_info']['weight']}")
    print(f"  填充后容量系数: {complete_profile['training_system']['personal_volume_multiplier']}")
    print(f"  填充后用户类型: {complete_profile['training_system']['user_type']}")
    
    assert complete_profile['basic_info']['height'] == 170
    assert complete_profile['training_system']['personal_volume_multiplier'] == 1.0
    print("  ✅ 默认值填充测试通过")


def test_volume_multiplier():
    """测试容量系数获取"""
    print("\n" + "=" * 50)
    print("测试3: 容量系数获取")
    print("=" * 50)
    
    class MockBackendClient:
        pass
    
    integrator = UserProfileIntegrator(MockBackendClient())
    
    # 测试新格式（training_system）
    profile_new = {
        'training_system': {
            'personal_volume_multiplier': 1.2
        }
    }
    multiplier = integrator.get_volume_multiplier(profile_new)
    print(f"  新格式容量系数: {multiplier}")
    assert multiplier == 1.2
    
    # 测试边界检查（超出范围）
    profile_high = {
        'training_system': {
            'personal_volume_multiplier': 2.0
        }
    }
    multiplier_high = integrator.get_volume_multiplier(profile_high)
    print(f"  超出上限(2.0)后: {multiplier_high}")
    assert multiplier_high == 1.5
    
    profile_low = {
        'training_system': {
            'personal_volume_multiplier': 0.5
        }
    }
    multiplier_low = integrator.get_volume_multiplier(profile_low)
    print(f"  超出下限(0.5)后: {multiplier_low}")
    assert multiplier_low == 0.7
    
    print("  ✅ 容量系数获取测试通过")


def test_user_type():
    """测试用户类型判断"""
    print("\n" + "=" * 50)
    print("测试4: 用户类型判断")
    print("=" * 50)
    
    class MockBackendClient:
        pass
    
    integrator = UserProfileIntegrator(MockBackendClient())
    
    # 测试大学生用户
    student_profile = {
        'training_system': {
            'user_type': 'student',
            'campus_name': '清华大学'
        }
    }
    print(f"  用户类型: {integrator.get_user_type(student_profile)}")
    print(f"  是否大学生: {integrator.is_student(student_profile)}")
    print(f"  是否上班族: {integrator.is_worker(student_profile)}")
    assert integrator.is_student(student_profile) == True
    assert integrator.is_worker(student_profile) == False
    
    # 测试上班族用户
    worker_profile = {
        'training_system': {
            'user_type': 'worker'
        }
    }
    print(f"  上班族用户类型: {integrator.get_user_type(worker_profile)}")
    assert integrator.is_worker(worker_profile) == True
    
    print("  ✅ 用户类型判断测试通过")


def test_profile_completeness():
    """测试档案完整性验证"""
    print("\n" + "=" * 50)
    print("测试5: 档案完整性验证")
    print("=" * 50)
    
    class MockBackendClient:
        pass
    
    integrator = UserProfileIntegrator(MockBackendClient())
    
    # 测试完整档案
    complete_profile = {
        'basic_info': {
            'age': 25,
            'height': 175,
            'weight': 70,
            'gender': 'male'
        },
        'fitness_config': {
            'fitness_level': 'intermediate',
            'training_days_per_week': 4
        },
        'fitness_goals': {
            'primary_goal': 'muscle_gain'
        }
    }
    
    result = integrator.validate_profile_completeness(complete_profile)
    print(f"  完整档案验证: is_complete={result['is_complete']}")
    print(f"  缺失字段: {result['missing_fields']}")
    print(f"  完整度评分: {result['completeness_score']}")
    assert result['is_complete'] == True
    
    # 测试不完整档案
    incomplete_profile = {
        'basic_info': {
            'age': 25
        }
    }
    
    result2 = integrator.validate_profile_completeness(incomplete_profile)
    print(f"  不完整档案验证: is_complete={result2['is_complete']}")
    print(f"  缺失字段: {result2['missing_fields']}")
    assert result2['is_complete'] == False
    assert len(result2['missing_fields']) > 0
    
    print("  ✅ 档案完整性验证测试通过")


def test_full_default_profile():
    """测试完整默认档案生成"""
    print("\n" + "=" * 50)
    print("测试6: 完整默认档案生成")
    print("=" * 50)
    
    class MockBackendClient:
        pass
    
    integrator = UserProfileIntegrator(MockBackendClient())
    
    default_profile = integrator._get_full_default_profile(user_id=123)
    
    print(f"  user_id: {default_profile['user_id']}")
    print(f"  basic_info.age: {default_profile['basic_info']['age']}")
    print(f"  training_system.personal_volume_multiplier: {default_profile['training_system']['personal_volume_multiplier']}")
    print(f"  _default标记: {default_profile.get('_default', False)}")
    
    assert default_profile['user_id'] == '123'
    assert default_profile['basic_info']['age'] == 25
    assert default_profile['training_system']['personal_volume_multiplier'] == 1.0
    assert default_profile['_default'] == True
    
    print("  ✅ 完整默认档案生成测试通过")


if __name__ == "__main__":
    print("\n🧪 用户档案整合器测试\n")
    
    test_defaults()
    test_apply_defaults()
    test_volume_multiplier()
    test_user_type()
    test_profile_completeness()
    test_full_default_profile()
    
    print("\n" + "=" * 50)
    print("✅ 所有测试通过！")
    print("=" * 50)
