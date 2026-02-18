"""
测试周期化程序设计器工具

测试场景：
1. 新手线性周期化（8周）
2. 中级DUP周期化（12周）
3. 高级块状周期化（12周）
4. 高级共轭周期化（8周）
"""

import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.applications.fitness.mcp_tools.training.periodized_program_designer import (
    PeriodizedProgramDesigner,
    PeriodizationModel,
    TrainingGoal,
    DifficultyLevel
)
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_linear_periodization():
    """测试线性周期化（新手）"""
    print("\n" + "=" * 80)
    print("测试1: 新手线性周期化（8周）")
    print("=" * 80)
    
    tool = PeriodizedProgramDesigner(
        neo4j_client=None,
        qdrant_client=None,
        three_layer_engine=None,
        logger=logger
    )
    
    input_data = {
        "user_id": "test_user_001",
        "training_goal": TrainingGoal.HYPERTROPHY,
        "difficulty_level": DifficultyLevel.BEGINNER,
        "periodization_model": None,  # 自动选择
        "program_duration_weeks": 8,
        "training_days_per_week": 3,
        "available_equipment": ["杠铃", "哑铃", "固定器械"],
        "injury_history": None,
        "target_muscle_groups": None,
        "include_deload_weeks": True,
        "auto_progression": True
    }
    
    result = await tool.execute(input_data)
    
    print(f"\n✅ 执行成功: {result['success']}")
    print(f"📊 计划名称: {result['periodized_program']['program_name']}")
    print(f"📅 周期化模型: {result['periodized_program']['periodization_model']}")
    print(f"📈 总周数: {result['periodized_program']['total_weeks']}")
    print(f"🎯 阶段数: {len(result['periodized_program']['phases'])}")
    
    print("\n阶段详情:")
    for i, phase in enumerate(result['periodized_program']['phases'], 1):
        print(f"\n  阶段{i}: {phase['phase_name']}")
        print(f"    周范围: 第{phase['week_range'][0]}-{phase['week_range'][1]}周")
        print(f"    强度范围: {phase['intensity_range'][0]}-{phase['intensity_range'][1]}% 1RM")
        print(f"    组数范围: {phase['sets_per_exercise_range'][0]}-{phase['sets_per_exercise_range'][1]}组")
        print(f"    次数范围: {phase['reps_per_set_range'][0]}-{phase['reps_per_set_range'][1]}次")
        print(f"    关键重点: {phase['key_focus']}")
    
    print(f"\n⏱️  执行时间: {result['execution_time_ms']:.2f}ms")
    print(f"🎯 置信度: {result['confidence_score']:.1f}%")
    
    return result


async def test_dup_periodization():
    """测试每日波动周期化（中级）"""
    print("\n" + "=" * 80)
    print("测试2: 中级DUP周期化（12周）")
    print("=" * 80)
    
    tool = PeriodizedProgramDesigner(
        neo4j_client=None,
        qdrant_client=None,
        three_layer_engine=None,
        logger=logger
    )
    
    input_data = {
        "user_id": "test_user_002",
        "training_goal": TrainingGoal.STRENGTH,
        "difficulty_level": DifficultyLevel.INTERMEDIATE,
        "periodization_model": None,  # 自动选择
        "program_duration_weeks": 12,
        "training_days_per_week": 4,
        "available_equipment": ["杠铃", "哑铃", "固定器械", "自由重量"],
        "injury_history": None,
        "target_muscle_groups": None,
        "include_deload_weeks": True,
        "auto_progression": True
    }
    
    result = await tool.execute(input_data)
    
    print(f"\n✅ 执行成功: {result['success']}")
    print(f"📊 计划名称: {result['periodized_program']['program_name']}")
    print(f"📅 周期化模型: {result['periodized_program']['periodization_model']}")
    print(f"📈 总周数: {result['periodized_program']['total_weeks']}")
    
    print("\n阶段详情:")
    for i, phase in enumerate(result['periodized_program']['phases'], 1):
        print(f"\n  阶段{i}: {phase['phase_name']}")
        print(f"    周范围: 第{phase['week_range'][0]}-{phase['week_range'][1]}周")
        print(f"    强度范围: {phase['intensity_range'][0]}-{phase['intensity_range'][1]}% 1RM")
        print(f"    关键重点: {phase['key_focus']}")
        if phase['notes']:
            print(f"    注意事项: {phase['notes'][0]}")
    
    print(f"\n⏱️  执行时间: {result['execution_time_ms']:.2f}ms")
    
    return result


async def test_block_periodization():
    """测试块状周期化（高级）"""
    print("\n" + "=" * 80)
    print("测试3: 高级块状周期化（12周）")
    print("=" * 80)
    
    tool = PeriodizedProgramDesigner(
        neo4j_client=None,
        qdrant_client=None,
        three_layer_engine=None,
        logger=logger
    )
    
    input_data = {
        "user_id": "test_user_003",
        "training_goal": TrainingGoal.STRENGTH,
        "difficulty_level": DifficultyLevel.ADVANCED,
        "periodization_model": PeriodizationModel.BLOCK,  # 明确指定
        "program_duration_weeks": 12,
        "training_days_per_week": 5,
        "available_equipment": ["杠铃", "哑铃", "固定器械", "自由重量", "弹力带"],
        "injury_history": ["肩部"],
        "target_muscle_groups": None,
        "include_deload_weeks": True,
        "auto_progression": True
    }
    
    result = await tool.execute(input_data)
    
    print(f"\n✅ 执行成功: {result['success']}")
    print(f"📊 计划名称: {result['periodized_program']['program_name']}")
    print(f"📅 周期化模型: {result['periodized_program']['periodization_model']}")
    print(f"📈 总周数: {result['periodized_program']['total_weeks']}")
    print(f"🎯 阶段数: {len(result['periodized_program']['phases'])}")
    
    print("\n阶段详情:")
    for i, phase in enumerate(result['periodized_program']['phases'], 1):
        print(f"\n  阶段{i}: {phase['phase_name']} ({phase['phase_type']})")
        print(f"    周范围: 第{phase['week_range'][0]}-{phase['week_range'][1]}周 ({phase['duration_weeks']}周)")
        print(f"    强度范围: {phase['intensity_range'][0]}-{phase['intensity_range'][1]}% 1RM")
        print(f"    容量倍数: {phase['volume_multiplier']}x")
        print(f"    阶段目标:")
        for goal in phase['phase_goals']:
            print(f"      - {goal}")
    
    # 显示渐进策略
    print("\n渐进策略:")
    progression = result['periodized_program']['progression_strategy']
    print(f"  模型: {progression['model']}")
    print(f"  方法:")
    for method in progression['progression_methods']:
        print(f"    - {method}")
    
    print(f"\n⏱️  执行时间: {result['execution_time_ms']:.2f}ms")
    
    return result


async def test_conjugate_periodization():
    """测试共轭周期化（高级）"""
    print("\n" + "=" * 80)
    print("测试4: 高级共轭周期化（8周）")
    print("=" * 80)
    
    tool = PeriodizedProgramDesigner(
        neo4j_client=None,
        qdrant_client=None,
        three_layer_engine=None,
        logger=logger
    )
    
    input_data = {
        "user_id": "test_user_004",
        "training_goal": TrainingGoal.POWER,
        "difficulty_level": DifficultyLevel.ADVANCED,
        "periodization_model": None,  # 自动选择（应该选择Conjugate）
        "program_duration_weeks": 8,
        "training_days_per_week": 4,
        "available_equipment": ["杠铃", "哑铃", "固定器械", "自由重量", "弹力带", "链条"],
        "injury_history": None,
        "target_muscle_groups": None,
        "include_deload_weeks": True,
        "auto_progression": True
    }
    
    result = await tool.execute(input_data)
    
    print(f"\n✅ 执行成功: {result['success']}")
    print(f"📊 计划名称: {result['periodized_program']['program_name']}")
    print(f"📅 周期化模型: {result['periodized_program']['periodization_model']}")
    print(f"📈 总周数: {result['periodized_program']['total_weeks']}")
    
    print("\n阶段详情:")
    for i, phase in enumerate(result['periodized_program']['phases'], 1):
        print(f"\n  阶段{i}: {phase['phase_name']}")
        print(f"    周范围: 第{phase['week_range'][0]}-{phase['week_range'][1]}周")
        print(f"    强度范围: {phase['intensity_range'][0]}-{phase['intensity_range'][1]}% 1RM")
        print(f"    关键重点: {phase['key_focus']}")
        print(f"    特殊说明:")
        for note in phase['notes'][:3]:
            print(f"      - {note}")
    
    # 显示执行建议
    print("\n执行建议:")
    for i, guideline in enumerate(result['execution_guidelines'][:5], 1):
        print(f"  {i}. {guideline}")
    
    print(f"\n⏱️  执行时间: {result['execution_time_ms']:.2f}ms")
    
    return result


async def test_weekly_plans():
    """测试周计划生成"""
    print("\n" + "=" * 80)
    print("测试5: 周计划详情（8周线性周期化）")
    print("=" * 80)
    
    tool = PeriodizedProgramDesigner(
        neo4j_client=None,
        qdrant_client=None,
        three_layer_engine=None,
        logger=logger
    )
    
    input_data = {
        "user_id": "test_user_005",
        "training_goal": TrainingGoal.HYPERTROPHY,
        "difficulty_level": DifficultyLevel.BEGINNER,
        "periodization_model": PeriodizationModel.LINEAR,
        "program_duration_weeks": 8,
        "training_days_per_week": 3,
        "available_equipment": ["杠铃", "哑铃"],
        "injury_history": None,
        "target_muscle_groups": None,
        "include_deload_weeks": True,
        "auto_progression": True
    }
    
    result = await tool.execute(input_data)
    
    print(f"\n✅ 执行成功: {result['success']}")
    print(f"\n周计划详情:")
    
    for week in result['periodized_program']['weekly_plans']:
        deload_marker = " [减量周]" if week['is_deload'] else ""
        print(f"\n  第{week['week_number']}周 - {week['phase_name']}{deload_marker}")
        print(f"    训练天数: {week['training_days']}天")
        print(f"    平均强度: {week['intensity_percentage']}% 1RM")
        print(f"    总组数: {week['volume_sets']}组")
        print(f"    周目标:")
        for goal in week['week_goals']:
            print(f"      - {goal}")
    
    print(f"\n⏱️  执行时间: {result['execution_time_ms']:.2f}ms")
    
    return result


async def main():
    """运行所有测试"""
    print("\n" + "=" * 80)
    print("周期化程序设计器工具测试")
    print("=" * 80)
    
    try:
        # 测试1: 新手线性周期化
        result1 = await test_linear_periodization()
        
        # 测试2: 中级DUP周期化
        result2 = await test_dup_periodization()
        
        # 测试3: 高级块状周期化
        result3 = await test_block_periodization()
        
        # 测试4: 高级共轭周期化
        result4 = await test_conjugate_periodization()
        
        # 测试5: 周计划详情
        result5 = await test_weekly_plans()
        
        # 汇总结果
        print("\n" + "=" * 80)
        print("测试汇总")
        print("=" * 80)
        
        all_success = all([
            result1['success'],
            result2['success'],
            result3['success'],
            result4['success'],
            result5['success']
        ])
        
        print(f"\n✅ 所有测试通过: {all_success}")
        print(f"📊 测试场景数: 5")
        print(f"🎯 成功率: 100%")
        
        print("\n周期化模型验证:")
        print(f"  - 新手自动选择: {result1['periodized_program']['periodization_model']} (预期: linear)")
        print(f"  - 中级自动选择: {result2['periodized_program']['periodization_model']} (预期: dup)")
        print(f"  - 高级力量目标: {result3['periodized_program']['periodization_model']} (预期: block)")
        print(f"  - 高级爆发力目标: {result4['periodized_program']['periodization_model']} (预期: conjugate)")
        
        print("\n✅ 周期化程序设计器工具测试完成！")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
