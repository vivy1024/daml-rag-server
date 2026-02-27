"""
测试训练周期计算逻辑

验证不同训练分化类型的周期计算是否正确
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.applications.fitness.mcp_tools.training.professional_program_designer import (
    ProfessionalProgramDesigner
)


def test_push_pull_legs_cycle():
    """测试推拉腿分化的周期计算"""
    print("\n" + "="*60)
    print("测试1: 推拉腿分化 - 练三休一")
    print("="*60)
    
    designer = ProfessionalProgramDesigner(None, None, None, None)
    
    input_data = {
        "training_split": "push_pull_legs",
        "training_days_per_week": 3,
        "rest_pattern": None
    }
    
    cycle_info = designer._calculate_training_cycle(input_data)
    
    print(f"训练分化: {input_data['training_split']}")
    print(f"每周训练天数: {input_data['training_days_per_week']}")
    print(f"实际周期天数: {cycle_info['cycle_days']} 天")
    print(f"每周完整周期数: {cycle_info['cycles_per_week']:.2f}")
    print(f"训练模式: {cycle_info['training_pattern']}")
    
    assert cycle_info['cycle_days'] == 4, "练三休一应该是4天周期"
    assert cycle_info['training_pattern'] == "练三休一"
    print("✅ 测试通过")


def test_push_pull_legs_6days():
    """测试推拉腿分化 - 练六休一"""
    print("\n" + "="*60)
    print("测试2: 推拉腿分化 - 练六休一")
    print("="*60)
    
    designer = ProfessionalProgramDesigner(None, None, None, None)
    
    input_data = {
        "training_split": "push_pull_legs",
        "training_days_per_week": 6,
        "rest_pattern": None
    }
    
    cycle_info = designer._calculate_training_cycle(input_data)
    
    print(f"训练分化: {input_data['training_split']}")
    print(f"每周训练天数: {input_data['training_days_per_week']}")
    print(f"实际周期天数: {cycle_info['cycle_days']} 天")
    print(f"每周完整周期数: {cycle_info['cycles_per_week']:.2f}")
    print(f"训练模式: {cycle_info['training_pattern']}")
    
    assert cycle_info['cycle_days'] == 7, "练六休一应该是7天周期"
    assert cycle_info['training_pattern'] == "练六休一"
    print("✅ 测试通过")


def test_upper_lower_cycle():
    """测试上下肢分化的周期计算"""
    print("\n" + "="*60)
    print("测试3: 上下肢分化 - 练二休一")
    print("="*60)
    
    designer = ProfessionalProgramDesigner(None, None, None, None)
    
    input_data = {
        "training_split": "upper_lower",
        "training_days_per_week": 4,
        "rest_pattern": None
    }
    
    cycle_info = designer._calculate_training_cycle(input_data)
    
    print(f"训练分化: {input_data['training_split']}")
    print(f"每周训练天数: {input_data['training_days_per_week']}")
    print(f"实际周期天数: {cycle_info['cycle_days']} 天")
    print(f"每周完整周期数: {cycle_info['cycles_per_week']:.2f}")
    print(f"训练模式: {cycle_info['training_pattern']}")
    
    assert cycle_info['cycle_days'] == 3, "练二休一应该是3天周期"
    assert cycle_info['training_pattern'] == "练二休一"
    print("✅ 测试通过")


def test_full_body_cycle():
    """测试全身训练的周期计算"""
    print("\n" + "="*60)
    print("测试4: 全身训练 - 练一休一")
    print("="*60)
    
    designer = ProfessionalProgramDesigner(None, None, None, None)
    
    input_data = {
        "training_split": "full_body",
        "training_days_per_week": 3,
        "rest_pattern": None
    }
    
    cycle_info = designer._calculate_training_cycle(input_data)
    
    print(f"训练分化: {input_data['training_split']}")
    print(f"每周训练天数: {input_data['training_days_per_week']}")
    print(f"实际周期天数: {cycle_info['cycle_days']} 天")
    print(f"每周完整周期数: {cycle_info['cycles_per_week']:.2f}")
    print(f"训练模式: {cycle_info['training_pattern']}")
    
    assert cycle_info['cycle_days'] == 2, "练一休一应该是2天周期"
    assert cycle_info['training_pattern'] == "练一休一"
    print("✅ 测试通过")


def test_cycle_calculations():
    """测试周期计算的数学正确性"""
    print("\n" + "="*60)
    print("测试5: 周期计算数学验证")
    print("="*60)
    
    designer = ProfessionalProgramDesigner(None, None, None, None)
    
    test_cases = [
        {
            "split": "push_pull_legs",
            "days": 3,
            "expected_cycle": 4,
            "expected_cycles_per_week": 7/4
        },
        {
            "split": "push_pull_legs",
            "days": 6,
            "expected_cycle": 7,
            "expected_cycles_per_week": 1.0
        },
        {
            "split": "upper_lower",
            "days": 4,
            "expected_cycle": 3,
            "expected_cycles_per_week": 7/3
        },
        {
            "split": "full_body",
            "days": 3,
            "expected_cycle": 2,
            "expected_cycles_per_week": 3.5
        }
    ]
    
    for i, case in enumerate(test_cases, 1):
        input_data = {
            "training_split": case["split"],
            "training_days_per_week": case["days"],
            "rest_pattern": None
        }
        
        cycle_info = designer._calculate_training_cycle(input_data)
        
        print(f"\n案例 {i}:")
        print(f"  分化: {case['split']}, 天数: {case['days']}")
        print(f"  预期周期: {case['expected_cycle']}天, 实际: {cycle_info['cycle_days']}天")
        print(f"  预期每周周期数: {case['expected_cycles_per_week']:.2f}, 实际: {cycle_info['cycles_per_week']:.2f}")
        
        assert cycle_info['cycle_days'] == case['expected_cycle'], \
            f"周期天数不匹配: 预期{case['expected_cycle']}, 实际{cycle_info['cycle_days']}"
        
        assert abs(cycle_info['cycles_per_week'] - case['expected_cycles_per_week']) < 0.01, \
            f"每周周期数不匹配: 预期{case['expected_cycles_per_week']:.2f}, 实际{cycle_info['cycles_per_week']:.2f}"
        
        print(f"  ✅ 通过")
    
    print("\n✅ 所有数学验证通过")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("训练周期计算逻辑测试")
    print("="*60)
    
    try:
        test_push_pull_legs_cycle()
        test_push_pull_legs_6days()
        test_upper_lower_cycle()
        test_full_body_cycle()
        test_cycle_calculations()
        
        print("\n" + "="*60)
        print("✅ 所有测试通过！")
        print("="*60)
        
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
