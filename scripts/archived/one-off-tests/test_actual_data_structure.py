#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试实际的intelligent_exercise_selector返回数据结构

验证为什么无法提取exercise_id
"""

import sys
import os
import asyncio
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.applications.fitness.mcp_tools.exercise.intelligent_exercise_selector import IntelligentExerciseSelector

async def test_actual_structure():
    """测试实际返回的数据结构"""
    
    # 创建工具实例
    tool = IntelligentExerciseSelector()
    
    # 准备测试参数
    params = {
        "user_id": "1",
        "muscle_group": "胸部",
        "training_goal": "hypertrophy",
        "difficulty_level": "beginner",
        "available_equipment": ["哑铃", "杠铃"],
        "injury_history": [],
        "exercise_preferences": [],
        "disliked_exercises": [],
        "session_focus": None
    }
    
    print("=" * 80)
    print("测试 intelligent_exercise_selector 实际返回结构")
    print("=" * 80)
    
    # 执行工具
    result = await tool.execute(params)
    
    print("\n" + "=" * 80)
    print("返回结果分析")
    print("=" * 80)
    
    # 分析结果类型
    print(f"\n1. 结果类型: {type(result)}")
    print(f"   类名: {result.__class__.__name__}")
    
    # 检查是否是Pydantic模型
    if hasattr(result, 'model_dump'):
        print(f"\n2. 这是一个Pydantic模型")
        result_dict = result.model_dump()
        print(f"   转换为字典后的keys: {list(result_dict.keys())}")
        
        # 检查recommendations
        if 'recommendations' in result_dict:
            recommendations = result_dict['recommendations']
            print(f"\n3. recommendations类型: {type(recommendations)}")
            print(f"   recommendations数量: {len(recommendations)}")
            
            if len(recommendations) > 0:
                first_rec = recommendations[0]
                print(f"\n4. 第一个推荐的类型: {type(first_rec)}")
                print(f"   第一个推荐的keys: {list(first_rec.keys()) if isinstance(first_rec, dict) else 'N/A'}")
                
                if isinstance(first_rec, dict) and 'exercise_id' in first_rec:
                    print(f"\n5. ✅ 成功找到exercise_id: {first_rec['exercise_id']}")
                else:
                    print(f"\n5. ❌ 第一个推荐中没有exercise_id字段")
                    print(f"   完整内容: {first_rec}")
    
    elif isinstance(result, dict):
        print(f"\n2. 这是一个普通字典")
        print(f"   keys: {list(result.keys())}")
        
        if 'recommendations' in result:
            recommendations = result['recommendations']
            print(f"\n3. recommendations数量: {len(recommendations)}")
            
            if len(recommendations) > 0:
                first_rec = recommendations[0]
                print(f"\n4. 第一个推荐: {first_rec}")
    
    else:
        print(f"\n2. 未知的结果类型")
        print(f"   内容: {result}")
    
    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_actual_structure())
