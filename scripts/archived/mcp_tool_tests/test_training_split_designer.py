"""
训练分化设计器工具测试脚本

测试training_split_designer工具的功能
重点验证训练周期(cycle)和日历周(week)的正确区分
"""

import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.applications.fitness.mcp_tools.training.training_split_designer import TrainingSplitDesigner
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_training_split_designer():
    """测试训练分化设计器"""
    
    # 创建工具实例（不需要真实客户端）
    tool = TrainingSplitDesigner(
        neo4j_client=None,
        qdrant_client=None,
        three_layer_engine=None,
        logger=logger
    )
    
    print("\n" + "="*80)
    print("测试1: 推拉腿分化（3天训练，练三休一 = 4天周期）")
    print("="*80)
    
    test_input_1 = {
        "user_id": "test_user_001",
        "training_level": "intermediate",
        "primary_goal": "hypertrophy",
        "training_days_per_week": 3,
        "session_duration_minutes": 60,
        "available_equipment": ["杠铃", "哑铃", "拉力器", "史密斯机"],
        "muscle_group_focus": None,
        "injury_history": None,
        "preferred_split_type": "push_pull_legs",
        "include_cardio": True,
        "rest_day_preference": "spread_out",
        "time_constraints": None
    }
    
    try:
        result_1 = await tool.execute(test_input_1)
        
        if result_1["success"]:
            print(f"\n✅ 测试1成功")
            print(f"分化类型: {result_1['split_plan']['split_name']}")
            print(f"训练天数/周: {result_1['split_plan']['training_days']}")
            
            # 验证周期信息
            cycle_info = result_1.get("cycle_info", {})
            print(f"\n📊 训练周期信息:")
            print(f"  周期天数: {cycle_info.get('cycle_days', 'N/A')}天")
            print(f"  每周周期数: {cycle_info.get('cycles_per_week', 'N/A')}")
            print(f"  训练模式: {cycle_info.get('training_pattern', 'N/A')}")
            
            # 验证分化计划中的周期信息
            split_plan = result_1['split_plan']
            print(f"\n📋 分化计划周期信息:")
            print(f"  cycle_days: {split_plan.get('cycle_days', 'N/A')}")
            print(f"  cycles_per_week: {split_plan.get('cycles_per_week', 'N/A')}")
            print(f"  training_pattern: {split_plan.get('training_pattern', 'N/A')}")
            
            print(f"\n训练日安排（一个周期内）:")
            for session in result_1['split_plan']['session_plans']:
                print(f"  {session['session_name']}: {', '.join(session['target_muscle_groups'])}")
            
            # 验证周期日程
            weekly_schedule = result_1['weekly_schedule']
            if weekly_schedule and len(weekly_schedule) > 0:
                cycle_schedule = weekly_schedule[0]
                print(f"\n📅 周期日程表:")
                print(f"  说明: {cycle_schedule.get('note', 'N/A')}")
                for day in cycle_schedule.get('schedule', []):
                    if day['is_training_day']:
                        print(f"  {day['day']}: {day['session']['session_name']} ({day['intensity_level']})")
                    else:
                        print(f"  {day['day']}: 休息日")
            
            # 验证：推拉腿+练三休一应该是4天周期
            assert cycle_info.get('cycle_days') == 4, f"期望4天周期，实际{cycle_info.get('cycle_days')}天"
            assert cycle_info.get('training_pattern') == "练三休一", f"期望'练三休一'，实际'{cycle_info.get('training_pattern')}'"
            print(f"\n✅ 周期验证通过：4天周期，练三休一")
        else:
            print(f"\n❌ 测试1失败: {result_1.get('error')}")
    
    except Exception as e:
        print(f"\n❌ 测试1异常: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*80)
    print("测试2: 上下肢分化（4天训练，练二休一 = 3天周期）")
    print("="*80)
    
    test_input_2 = {
        "user_id": "test_user_002",
        "training_level": "intermediate",
        "primary_goal": "strength",
        "training_days_per_week": 4,
        "session_duration_minutes": 90,
        "available_equipment": ["杠铃", "哑铃", "拉力器"],
        "muscle_group_focus": None,
        "injury_history": None,
        "preferred_split_type": "upper_lower",
        "include_cardio": False,
        "rest_day_preference": "spread_out",
        "time_constraints": None
    }
    
    try:
        result_2 = await tool.execute(test_input_2)
        
        if result_2["success"]:
            print(f"\n✅ 测试2成功")
            print(f"分化类型: {result_2['split_plan']['split_name']}")
            
            cycle_info = result_2.get("cycle_info", {})
            print(f"\n📊 训练周期信息:")
            print(f"  周期天数: {cycle_info.get('cycle_days', 'N/A')}天")
            print(f"  每周周期数: {cycle_info.get('cycles_per_week', 'N/A')}")
            print(f"  训练模式: {cycle_info.get('training_pattern', 'N/A')}")
            
            # 验证：上下肢+练二休一应该是3天周期
            assert cycle_info.get('cycle_days') == 3, f"期望3天周期，实际{cycle_info.get('cycle_days')}天"
            assert cycle_info.get('training_pattern') == "练二休一", f"期望'练二休一'，实际'{cycle_info.get('training_pattern')}'"
            print(f"\n✅ 周期验证通过：3天周期，练二休一")
        else:
            print(f"\n❌ 测试2失败: {result_2.get('error')}")
    
    except Exception as e:
        print(f"\n❌ 测试2异常: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*80)
    print("测试3: 推拉腿分化（6天训练，练六休一 = 7天周期）")
    print("="*80)
    
    test_input_3 = {
        "user_id": "test_user_003",
        "training_level": "advanced",
        "primary_goal": "hypertrophy",
        "training_days_per_week": 6,
        "session_duration_minutes": 75,
        "available_equipment": ["杠铃", "哑铃", "拉力器", "史密斯机"],
        "muscle_group_focus": None,
        "injury_history": None,
        "preferred_split_type": "push_pull_legs",
        "include_cardio": False,
        "rest_day_preference": "consecutive",
        "time_constraints": None
    }
    
    try:
        result_3 = await tool.execute(test_input_3)
        
        if result_3["success"]:
            print(f"\n✅ 测试3成功")
            print(f"分化类型: {result_3['split_plan']['split_name']}")
            
            cycle_info = result_3.get("cycle_info", {})
            print(f"\n📊 训练周期信息:")
            print(f"  周期天数: {cycle_info.get('cycle_days', 'N/A')}天")
            print(f"  每周周期数: {cycle_info.get('cycles_per_week', 'N/A')}")
            print(f"  训练模式: {cycle_info.get('training_pattern', 'N/A')}")
            
            # 验证：推拉腿+练六休一应该是7天周期
            assert cycle_info.get('cycle_days') == 7, f"期望7天周期，实际{cycle_info.get('cycle_days')}天"
            assert cycle_info.get('training_pattern') == "练六休一", f"期望'练六休一'，实际'{cycle_info.get('training_pattern')}'"
            print(f"\n✅ 周期验证通过：7天周期，练六休一")
        else:
            print(f"\n❌ 测试3失败: {result_3.get('error')}")
    
    except Exception as e:
        print(f"\n❌ 测试3异常: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*80)
    print("测试4: 全身训练（3天训练，练一休一 = 2天周期）")
    print("="*80)
    
    test_input_4 = {
        "user_id": "test_user_004",
        "training_level": "beginner",
        "primary_goal": "general_fitness",
        "training_days_per_week": 3,
        "session_duration_minutes": 45,
        "available_equipment": ["哑铃", "弹力带"],
        "muscle_group_focus": None,
        "injury_history": None,
        "preferred_split_type": "full_body",
        "include_cardio": True,
        "rest_day_preference": "spread_out",
        "time_constraints": "时间紧张，需要高效训练"
    }
    
    try:
        result_4 = await tool.execute(test_input_4)
        
        if result_4["success"]:
            print(f"\n✅ 测试4成功")
            print(f"分化类型: {result_4['split_plan']['split_name']}")
            
            cycle_info = result_4.get("cycle_info", {})
            print(f"\n📊 训练周期信息:")
            print(f"  周期天数: {cycle_info.get('cycle_days', 'N/A')}天")
            print(f"  每周周期数: {cycle_info.get('cycles_per_week', 'N/A')}")
            print(f"  训练模式: {cycle_info.get('training_pattern', 'N/A')}")
            
            print(f"\n定制化说明:")
            print(f"  器械适配: {', '.join(result_4['customization_notes']['equipment_adaptations'])}")
            print(f"  节省时间建议: {', '.join(result_4['customization_notes']['time_saving_tips'])}")
        else:
            print(f"\n❌ 测试4失败: {result_4.get('error')}")
    
    except Exception as e:
        print(f"\n❌ 测试4异常: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*80)
    print("所有测试完成")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(test_training_split_designer())
