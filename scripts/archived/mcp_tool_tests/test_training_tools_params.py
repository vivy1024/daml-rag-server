#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试训练工具参数映射

验证 training_split_designer 和 periodized_program_designer 的参数构建是否正确
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.applications.fitness.enhanced_dag_orchestrator import EnhancedDAGOrchestrator


def test_training_split_params():
    """测试训练分化参数构建"""
    print("\n" + "="*60)
    print("测试 training_split_designer 参数构建")
    print("="*60)
    
    orchestrator = EnhancedDAGOrchestrator()
    
    # 模拟用户档案
    user_profile = {
        "user_id": "test_user",
        "fitness_level": "intermediate",
        "fitness_goals": ["增肌"],
        "preferred_training_days": 4,
        "session_duration": 75,
        "available_equipment": ["杠铃", "哑铃", "史密斯机"],
        "target_muscle_groups": ["胸大肌", "背阔肌"],
        "injury_history": ["右肩轻微拉伤"],
        "include_cardio": True
    }
    
    # 构建参数
    params = orchestrator._build_training_split_params(user_profile, {})
    
    print("\n✅ 构建的参数:")
    for key, value in params.items():
        print(f"  - {key}: {value}")
    
    # 验证必需参数
    required_params = [
        "training_level",
        "primary_goal", 
        "training_days_per_week",
        "session_duration_minutes",
        "available_equipment"
    ]
    
    print("\n🔍 验证必需参数:")
    all_present = True
    for param in required_params:
        if param in params:
            print(f"  ✅ {param}: {params[param]}")
        else:
            print(f"  ❌ {param}: 缺失")
            all_present = False
    
    if all_present:
        print("\n✅ 所有必需参数都已提供")
    else:
        print("\n❌ 部分必需参数缺失")
    
    return all_present


def test_periodized_program_params():
    """测试周期化训练参数构建"""
    print("\n" + "="*60)
    print("测试 periodized_program_designer 参数构建")
    print("="*60)
    
    orchestrator = EnhancedDAGOrchestrator()
    
    # 模拟用户档案
    user_profile = {
        "user_id": "test_user",
        "fitness_level": "advanced",
        "fitness_goals": ["力量"],
        "preferred_training_days": 5,
        "available_equipment": ["杠铃", "哑铃", "深蹲架"],
        "target_muscle_groups": ["股四头肌", "腘绳肌"],
        "injury_history": []
    }
    
    # 构建参数
    params = orchestrator._build_periodized_program_params(user_profile, {})
    
    print("\n✅ 构建的参数:")
    for key, value in params.items():
        print(f"  - {key}: {value}")
    
    # 验证必需参数
    required_params = [
        "training_goal",
        "difficulty_level",
        "program_duration_weeks",
        "training_days_per_week",
        "available_equipment"
    ]
    
    print("\n🔍 验证必需参数:")
    all_present = True
    for param in required_params:
        if param in params:
            print(f"  ✅ {param}: {params[param]}")
        else:
            print(f"  ❌ {param}: 缺失")
            all_present = False
    
    if all_present:
        print("\n✅ 所有必需参数都已提供")
    else:
        print("\n❌ 部分必需参数缺失")
    
    return all_present


def test_goal_mapping():
    """测试训练目标映射"""
    print("\n" + "="*60)
    print("测试训练目标映射")
    print("="*60)
    
    orchestrator = EnhancedDAGOrchestrator()
    
    test_cases = [
        ("增肌", "hypertrophy"),
        ("力量", "strength"),
        ("耐力", "endurance"),
        ("减脂", "general_fitness"),
        ("爆发力", "power"),
        ("未知目标", "hypertrophy")  # 默认值
    ]
    
    print("\n🔍 测试中文目标到英文枚举的映射:")
    all_correct = True
    
    for chinese_goal, expected_english in test_cases:
        user_profile = {
            "user_id": "test",
            "fitness_goals": [chinese_goal],
            "fitness_level": "beginner",
            "preferred_training_days": 3,
            "available_equipment": ["哑铃"]
        }
        
        # 测试 training_split_designer
        params = orchestrator._build_training_split_params(user_profile, {})
        actual_goal = params.get("primary_goal")
        
        if actual_goal == expected_english:
            print(f"  ✅ {chinese_goal} → {actual_goal}")
        else:
            print(f"  ❌ {chinese_goal} → {actual_goal} (期望: {expected_english})")
            all_correct = False
    
    if all_correct:
        print("\n✅ 所有目标映射正确")
    else:
        print("\n❌ 部分目标映射错误")
    
    return all_correct


def main():
    """主测试函数"""
    print("\n" + "="*60)
    print("训练工具参数映射测试")
    print("="*60)
    
    results = []
    
    # 测试1: training_split_designer参数
    results.append(("training_split_designer参数", test_training_split_params()))
    
    # 测试2: periodized_program_designer参数
    results.append(("periodized_program_designer参数", test_periodized_program_params()))
    
    # 测试3: 目标映射
    results.append(("训练目标映射", test_goal_mapping()))
    
    # 总结
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)
    
    for test_name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{status} - {test_name}")
    
    all_passed = all(result[1] for result in results)
    
    if all_passed:
        print("\n🎉 所有测试通过！")
        return 0
    else:
        print("\n❌ 部分测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
