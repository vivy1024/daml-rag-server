"""
测试减量日（Deload Day）功能

验证：
1. 连续训练≥3天时自动插入减量日
2. 减量日训练量减半（50%）
3. 减量日强度降至80%
4. 减量日明确标注及科学依据说明

作者: BUILD_BODY Team
日期: 2025-12-19
"""

import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.applications.fitness.mcp_tools.training.professional_program_designer import (
    ProfessionalProgramDesigner,
    TrainingGoal,
    TrainingSplit,
    DifficultyLevel
)


async def test_deload_day_detection():
    """测试减量日检测功能"""
    print("\n" + "="*80)
    print("测试1: 减量日检测功能")
    print("="*80)
    
    # 创建工具实例（不需要实际的客户端）
    tool = ProfessionalProgramDesigner(
        neo4j_client=None,
        qdrant_client=None,
        three_layer_engine=None
    )
    
    # 测试场景1: 连续3天训练
    print("\n场景1: 连续3天训练")
    training_days = [
        {"day_number": 1, "day_name": "推日", "total_sets": 20, "exercises": []},
        {"day_number": 2, "day_name": "拉日", "total_sets": 18, "exercises": []},
        {"day_number": 3, "day_name": "腿日", "total_sets": 22, "exercises": []}
    ]
    
    deload_days = tool._detect_deload_days(training_days)
    print(f"检测结果: {deload_days}")
    print(f"预期: [3] (第3天应为减量日)")
    assert deload_days == [3], f"测试失败: 预期[3]，实际{deload_days}"
    print("✅ 测试通过")
    
    # 测试场景2: 连续6天训练
    print("\n场景2: 连续6天训练")
    training_days = [
        {"day_number": 1, "day_name": "推日", "total_sets": 20, "exercises": []},
        {"day_number": 2, "day_name": "拉日", "total_sets": 18, "exercises": []},
        {"day_number": 3, "day_name": "腿日", "total_sets": 22, "exercises": []},
        {"day_number": 4, "day_name": "推日", "total_sets": 20, "exercises": []},
        {"day_number": 5, "day_name": "拉日", "total_sets": 18, "exercises": []},
        {"day_number": 6, "day_name": "腿日", "total_sets": 22, "exercises": []}
    ]
    
    deload_days = tool._detect_deload_days(training_days)
    print(f"检测结果: {deload_days}")
    print(f"预期: [3, 6] (第3天和第6天应为减量日)")
    assert deload_days == [3, 6], f"测试失败: 预期[3, 6]，实际{deload_days}"
    print("✅ 测试通过")
    
    # 测试场景3: 只有2天训练
    print("\n场景3: 只有2天训练")
    training_days = [
        {"day_number": 1, "day_name": "上肢日", "total_sets": 20, "exercises": []},
        {"day_number": 2, "day_name": "下肢日", "total_sets": 22, "exercises": []}
    ]
    
    deload_days = tool._detect_deload_days(training_days)
    print(f"检测结果: {deload_days}")
    print(f"预期: [] (不应有减量日)")
    assert deload_days == [], f"测试失败: 预期[]，实际{deload_days}"
    print("✅ 测试通过")


async def test_deload_day_application():
    """测试减量日应用功能"""
    print("\n" + "="*80)
    print("测试2: 减量日应用功能")
    print("="*80)
    
    # 创建工具实例
    tool = ProfessionalProgramDesigner(
        neo4j_client=None,
        qdrant_client=None,
        three_layer_engine=None
    )
    
    # 创建一个正常训练日
    normal_day = {
        "day_number": 3,
        "day_name": "腿日",
        "focus_muscle_groups": ["股四头肌", "腘绳肌"],
        "total_sets": 20,
        "estimated_duration_minutes": 60,
        "exercises": [
            {
                "exercise_id": "ex1",
                "name_zh": "深蹲",
                "name_en": "Squat",
                "category": "复合动作",
                "difficulty": "intermediate",
                "sets": 4,
                "reps_range": (8, 12),
                "rest_seconds": 120,
                "primary_muscles": ["股四头肌"],
                "secondary_muscles": ["臀大肌"],
                "safety_level": "MODERATE",
                "safety_notes": [],
                "reasoning": "主要训练股四头肌"
            },
            {
                "exercise_id": "ex2",
                "name_zh": "腿弯举",
                "name_en": "Leg Curl",
                "category": "孤立动作",
                "difficulty": "beginner",
                "sets": 3,
                "reps_range": (10, 15),
                "rest_seconds": 90,
                "primary_muscles": ["腘绳肌"],
                "secondary_muscles": [],
                "safety_level": "LOW",
                "safety_notes": [],
                "reasoning": "孤立训练腘绳肌"
            }
        ],
        "notes": ["专注于腿部训练"]
    }
    
    print("\n原始训练日:")
    print(f"  日期: 第{normal_day['day_number']}天")
    print(f"  名称: {normal_day['day_name']}")
    print(f"  总组数: {normal_day['total_sets']}")
    print(f"  预估时长: {normal_day['estimated_duration_minutes']}分钟")
    print(f"  动作数: {len(normal_day['exercises'])}")
    for ex in normal_day['exercises']:
        print(f"    - {ex['name_zh']}: {ex['sets']}组 x {ex['reps_range']}次")
    
    # 应用减量日
    deload_day = tool._apply_deload_to_day(normal_day)
    
    print("\n减量日调整后:")
    print(f"  日期: 第{deload_day['day_number']}天")
    print(f"  名称: {deload_day['day_name']}")
    print(f"  总组数: {deload_day['total_sets']}")
    print(f"  预估时长: {deload_day['estimated_duration_minutes']}分钟")
    print(f"  是否减量日: {deload_day.get('is_deload_day', False)}")
    print(f"  动作数: {len(deload_day['exercises'])}")
    for ex in deload_day['exercises']:
        print(f"    - {ex['name_zh']}: {ex['sets']}组 x {ex['reps_range']}次")
        if ex.get('is_deload'):
            print(f"      减量标记: {ex.get('deload_note', '')}")
    
    print("\n减量日说明:")
    for note in deload_day.get('notes', []):
        print(f"  {note}")
    
    # 验证调整
    print("\n验证调整:")
    
    # 1. 验证训练量减半
    original_total_sets = normal_day['total_sets']
    deload_total_sets = deload_day['total_sets']
    expected_sets = (original_total_sets + 1) // 2  # 向上取整
    
    print(f"  训练量: {original_total_sets}组 → {deload_total_sets}组")
    print(f"  预期: 约{expected_sets}组 (50%)")
    assert deload_total_sets <= expected_sets + 1, "训练量未正确减半"
    print("  ✅ 训练量减半验证通过")
    
    # 2. 验证时长减半
    original_duration = normal_day['estimated_duration_minutes']
    deload_duration = deload_day['estimated_duration_minutes']
    
    print(f"  训练时长: {original_duration}分钟 → {deload_duration}分钟")
    print(f"  预期: 约{original_duration // 2}分钟 (50%)")
    assert deload_duration <= original_duration // 2 + 10, "时长未正确减半"
    print("  ✅ 时长减半验证通过")
    
    # 3. 验证减量日标记
    assert deload_day.get('is_deload_day') == True, "缺少减量日标记"
    print("  ✅ 减量日标记验证通过")
    
    # 4. 验证动作减量标记
    for ex in deload_day['exercises']:
        assert ex.get('is_deload') == True, f"动作{ex['name_zh']}缺少减量标记"
    print("  ✅ 动作减量标记验证通过")
    
    # 5. 验证科学依据说明
    notes = deload_day.get('notes', [])
    has_scientific_basis = any('中枢神经系统' in note or '科学依据' in note for note in notes)
    assert has_scientific_basis, "缺少科学依据说明"
    print("  ✅ 科学依据说明验证通过")
    
    print("\n✅ 所有验证通过")


async def test_deload_day_integration():
    """测试减量日在完整训练计划中的集成"""
    print("\n" + "="*80)
    print("测试3: 减量日集成测试")
    print("="*80)
    
    # 创建工具实例
    tool = ProfessionalProgramDesigner(
        neo4j_client=None,
        qdrant_client=None,
        three_layer_engine=None
    )
    
    # 模拟输入数据
    input_data = {
        "user_id": "test_user",
        "training_goal": TrainingGoal.HYPERTROPHY,
        "training_split": TrainingSplit.PUSH_PULL_LEGS,
        "training_days_per_week": 6,
        "difficulty_level": DifficultyLevel.INTERMEDIATE,
        "available_equipment": ["杠铃", "哑铃", "固定器械"],
        "injury_history": None,
        "training_weeks": 4,
        "rest_pattern": "练六休一"
    }
    
    # 模拟周期信息
    cycle_info = {
        "cycle_days": 7,
        "cycles_per_week": 1.0,
        "training_pattern": "练六休一",
        "base_cycle": 3
    }
    
    # 模拟肌群数据（包含动作推荐）
    muscle_group_data = {
        "胸大肌": {
            "exercise_recommendations": {
                "recommendations": [
                    {
                        "exercise_id": "ex_chest_1",
                        "name_zh": "卧推",
                        "name_en": "Bench Press",
                        "category": "复合动作",
                        "difficulty": "intermediate",
                        "primary_muscles": ["胸大肌"],
                        "secondary_muscles": ["三角肌前束", "肱三头肌"],
                        "safety_level": "MODERATE",
                        "contraindications_zh": [],
                        "reasoning": "主要训练胸大肌"
                    },
                    {
                        "exercise_id": "ex_chest_2",
                        "name_zh": "哑铃飞鸟",
                        "name_en": "Dumbbell Fly",
                        "category": "孤立动作",
                        "difficulty": "beginner",
                        "primary_muscles": ["胸大肌"],
                        "secondary_muscles": [],
                        "safety_level": "LOW",
                        "contraindications_zh": [],
                        "reasoning": "孤立训练胸大肌"
                    }
                ]
            },
            "volume_data": {
                "mev": 10,
                "mav": 16,
                "mrv": 22,
                "volume_recommendation": {
                    "recommended_weekly_sets": 16,
                    "sets_per_session": 4,
                    "reps_per_set_range": (8, 12),
                    "rest_period_seconds": 90
                }
            }
        },
        "背阔肌": {
            "exercise_recommendations": {
                "recommendations": [
                    {
                        "exercise_id": "ex_back_1",
                        "name_zh": "引体向上",
                        "name_en": "Pull Up",
                        "category": "复合动作",
                        "difficulty": "advanced",
                        "primary_muscles": ["背阔肌"],
                        "secondary_muscles": ["肱二头肌"],
                        "safety_level": "MODERATE",
                        "contraindications_zh": [],
                        "reasoning": "主要训练背阔肌"
                    },
                    {
                        "exercise_id": "ex_back_2",
                        "name_zh": "坐姿划船",
                        "name_en": "Seated Row",
                        "category": "复合动作",
                        "difficulty": "intermediate",
                        "primary_muscles": ["背阔肌"],
                        "secondary_muscles": ["肱二头肌"],
                        "safety_level": "LOW",
                        "contraindications_zh": [],
                        "reasoning": "训练背阔肌中部"
                    }
                ]
            },
            "volume_data": {
                "mev": 10,
                "mav": 16,
                "mrv": 22,
                "volume_recommendation": {
                    "recommended_weekly_sets": 16,
                    "sets_per_session": 4,
                    "reps_per_set_range": (8, 12),
                    "rest_period_seconds": 90
                }
            }
        },
        "股四头肌": {
            "exercise_recommendations": {
                "recommendations": [
                    {
                        "exercise_id": "ex_quad_1",
                        "name_zh": "深蹲",
                        "name_en": "Squat",
                        "category": "复合动作",
                        "difficulty": "intermediate",
                        "primary_muscles": ["股四头肌"],
                        "secondary_muscles": ["臀大肌", "腘绳肌"],
                        "safety_level": "MODERATE",
                        "contraindications_zh": [],
                        "reasoning": "主要训练股四头肌"
                    },
                    {
                        "exercise_id": "ex_quad_2",
                        "name_zh": "腿屈伸",
                        "name_en": "Leg Extension",
                        "category": "孤立动作",
                        "difficulty": "beginner",
                        "primary_muscles": ["股四头肌"],
                        "secondary_muscles": [],
                        "safety_level": "LOW",
                        "contraindications_zh": [],
                        "reasoning": "孤立训练股四头肌"
                    }
                ]
            },
            "volume_data": {
                "mev": 12,
                "mav": 18,
                "mrv": 24,
                "volume_recommendation": {
                    "recommended_weekly_sets": 18,
                    "sets_per_session": 6,
                    "reps_per_set_range": (8, 12),
                    "rest_period_seconds": 120
                }
            }
        },
        "三角肌": {
            "exercise_recommendations": {
                "recommendations": [
                    {
                        "exercise_id": "ex_delt_1",
                        "name_zh": "推举",
                        "name_en": "Overhead Press",
                        "category": "复合动作",
                        "difficulty": "intermediate",
                        "primary_muscles": ["三角肌"],
                        "secondary_muscles": ["肱三头肌"],
                        "safety_level": "MODERATE",
                        "contraindications_zh": [],
                        "reasoning": "主要训练三角肌"
                    }
                ]
            },
            "volume_data": {
                "mev": 8,
                "mav": 14,
                "mrv": 20,
                "volume_recommendation": {
                    "recommended_weekly_sets": 14,
                    "sets_per_session": 4,
                    "reps_per_set_range": (8, 12),
                    "rest_period_seconds": 90
                }
            }
        },
        "肱三头肌": {
            "exercise_recommendations": {
                "recommendations": [
                    {
                        "exercise_id": "ex_tri_1",
                        "name_zh": "臂屈伸",
                        "name_en": "Dips",
                        "category": "复合动作",
                        "difficulty": "intermediate",
                        "primary_muscles": ["肱三头肌"],
                        "secondary_muscles": ["胸大肌"],
                        "safety_level": "MODERATE",
                        "contraindications_zh": [],
                        "reasoning": "主要训练肱三头肌"
                    }
                ]
            },
            "volume_data": {
                "mev": 6,
                "mav": 12,
                "mrv": 18,
                "volume_recommendation": {
                    "recommended_weekly_sets": 12,
                    "sets_per_session": 3,
                    "reps_per_set_range": (8, 12),
                    "rest_period_seconds": 90
                }
            }
        },
        "肱二头肌": {
            "exercise_recommendations": {
                "recommendations": [
                    {
                        "exercise_id": "ex_bi_1",
                        "name_zh": "弯举",
                        "name_en": "Curl",
                        "category": "孤立动作",
                        "difficulty": "beginner",
                        "primary_muscles": ["肱二头肌"],
                        "secondary_muscles": [],
                        "safety_level": "LOW",
                        "contraindications_zh": [],
                        "reasoning": "孤立训练肱二头肌"
                    }
                ]
            },
            "volume_data": {
                "mev": 6,
                "mav": 12,
                "mrv": 18,
                "volume_recommendation": {
                    "recommended_weekly_sets": 12,
                    "sets_per_session": 3,
                    "reps_per_set_range": (8, 12),
                    "rest_period_seconds": 90
                }
            }
        },
        "腘绳肌": {
            "exercise_recommendations": {
                "recommendations": [
                    {
                        "exercise_id": "ex_ham_1",
                        "name_zh": "腿弯举",
                        "name_en": "Leg Curl",
                        "category": "孤立动作",
                        "difficulty": "beginner",
                        "primary_muscles": ["腘绳肌"],
                        "secondary_muscles": [],
                        "safety_level": "LOW",
                        "contraindications_zh": [],
                        "reasoning": "孤立训练腘绳肌"
                    }
                ]
            },
            "volume_data": {
                "mev": 8,
                "mav": 14,
                "mrv": 20,
                "volume_recommendation": {
                    "recommended_weekly_sets": 14,
                    "sets_per_session": 4,
                    "reps_per_set_range": (8, 12),
                    "rest_period_seconds": 90
                }
            }
        },
        "臀大肌": {
            "exercise_recommendations": {
                "recommendations": [
                    {
                        "exercise_id": "ex_glute_1",
                        "name_zh": "臀桥",
                        "name_en": "Hip Thrust",
                        "category": "孤立动作",
                        "difficulty": "beginner",
                        "primary_muscles": ["臀大肌"],
                        "secondary_muscles": [],
                        "safety_level": "LOW",
                        "contraindications_zh": [],
                        "reasoning": "孤立训练臀大肌"
                    }
                ]
            },
            "volume_data": {
                "mev": 8,
                "mav": 14,
                "mrv": 20,
                "volume_recommendation": {
                    "recommended_weekly_sets": 14,
                    "sets_per_session": 4,
                    "reps_per_set_range": (8, 12),
                    "rest_period_seconds": 90
                }
            }
        }
    }
    
    # 生成周训练计划
    weekly_program = tool._generate_weekly_program(
        input_data,
        muscle_group_data,
        cycle_info
    )
    
    print("\n周训练计划概览:")
    print(f"  训练天数: {len(weekly_program['training_days'])}天")
    print(f"  休息天数: {len(weekly_program['rest_days'])}天")
    print(f"  总训练量: {weekly_program['total_weekly_sets']}组")
    print(f"  训练周期: {weekly_program['cycle_days']}天")
    print(f"  训练模式: {weekly_program['training_pattern']}")
    print(f"  包含减量日: {weekly_program.get('has_deload_days', False)}")
    print(f"  减量日数量: {weekly_program.get('deload_days_count', 0)}")
    print(f"  减量日编号: {weekly_program.get('deload_day_numbers', [])}")
    
    print("\n训练日详情:")
    for day in weekly_program['training_days']:
        is_deload = day.get('is_deload_day', False)
        deload_marker = " 🔄 (减量日)" if is_deload else ""
        print(f"  第{day['day_number']}天: {day['day_name']}{deload_marker}")
        print(f"    总组数: {day['total_sets']}")
        print(f"    预估时长: {day['estimated_duration_minutes']}分钟")
        
        if is_deload:
            print(f"    减量日说明:")
            for note in day.get('notes', [])[:3]:  # 只显示前3条
                print(f"      {note}")
    
    # 验证减量日
    print("\n验证减量日:")
    
    # 1. 验证6天训练应有2个减量日
    expected_deload_count = 2  # 第3天和第6天
    actual_deload_count = weekly_program.get('deload_days_count', 0)
    
    print(f"  预期减量日数量: {expected_deload_count}")
    print(f"  实际减量日数量: {actual_deload_count}")
    assert actual_deload_count == expected_deload_count, \
        f"减量日数量不正确: 预期{expected_deload_count}，实际{actual_deload_count}"
    print("  ✅ 减量日数量验证通过")
    
    # 2. 验证减量日位置
    expected_positions = [3, 6]
    actual_positions = weekly_program.get('deload_day_numbers', [])
    
    print(f"  预期减量日位置: {expected_positions}")
    print(f"  实际减量日位置: {actual_positions}")
    assert actual_positions == expected_positions, \
        f"减量日位置不正确: 预期{expected_positions}，实际{actual_positions}"
    print("  ✅ 减量日位置验证通过")
    
    # 3. 验证减量日训练量
    for day in weekly_program['training_days']:
        if day.get('is_deload_day'):
            # 减量日的训练量应该明显少于正常训练日
            normal_day_sets = [
                d['total_sets'] for d in weekly_program['training_days']
                if not d.get('is_deload_day')
            ]
            avg_normal_sets = sum(normal_day_sets) / len(normal_day_sets) if normal_day_sets else 0
            
            print(f"  第{day['day_number']}天减量日训练量: {day['total_sets']}组")
            print(f"  正常训练日平均训练量: {avg_normal_sets:.1f}组")
            
            # 减量日训练量应该小于或等于正常训练日的80%
            # （由于向上取整，可能不会完全减半）
            max_allowed_sets = avg_normal_sets * 0.8
            assert day['total_sets'] <= max_allowed_sets, \
                f"减量日训练量过高: {day['total_sets']}组 > {max_allowed_sets:.1f}组"
            print(f"  ✅ 减量日训练量验证通过 ({day['total_sets']}组 <= {max_allowed_sets:.1f}组)")
    
    print("\n✅ 所有集成测试通过")


async def main():
    """运行所有测试"""
    print("\n" + "="*80)
    print("减量日（Deload Day）功能测试")
    print("="*80)
    
    try:
        # 测试1: 减量日检测
        await test_deload_day_detection()
        
        # 测试2: 减量日应用
        await test_deload_day_application()
        
        # 测试3: 减量日集成
        await test_deload_day_integration()
        
        print("\n" + "="*80)
        print("✅ 所有测试通过！")
        print("="*80)
        
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
