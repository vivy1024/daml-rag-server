"""
测试智能重量计算器的训练目标调整功能

验证不同训练目标的重量百分比调整是否正确
"""

import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.applications.fitness.mcp_tools.training.intelligent_weight_calculator import (
    IntelligentWeightCalculator
)
from unittest.mock import AsyncMock, MagicMock


async def test_weight_goal_adjustment():
    """测试不同训练目标的重量百分比调整"""
    
    print("=" * 80)
    print("测试智能重量计算器 - 训练目标重量百分比调整")
    print("=" * 80)
    print()
    
    # 创建模拟的依赖
    mock_neo4j = AsyncMock()
    mock_neo4j.run_query = AsyncMock(return_value=[
        {
            "mechanic": "compound",
            "force": "push",
            "difficulty_level": "intermediate"
        }
    ])
    
    mock_qdrant = MagicMock()
    mock_three_layer = MagicMock()
    mock_logger = MagicMock()
    
    # 创建工具实例
    calculator = IntelligentWeightCalculator(
        neo4j_client=mock_neo4j,
        qdrant_client=mock_qdrant,
        three_layer_engine=mock_three_layer,
        logger=mock_logger
    )
    
    # 测试用例：相同的用户和动作，不同的训练目标
    test_cases = [
        {
            "training_goal": "strength",
            "expected_adjustment": 0.90,
            "description": "力量训练：85-95%（中位数90%）"
        },
        {
            "training_goal": "hypertrophy",
            "expected_adjustment": 0.70,
            "description": "增肌训练：60-80%（中位数70%）"
        },
        {
            "training_goal": "endurance",
            "expected_adjustment": 0.50,
            "description": "耐力训练：40-60%（中位数50%）"
        },
        {
            "training_goal": "general_fitness",
            "expected_adjustment": 0.70,
            "description": "一般健身：65-75%（中位数70%）"
        }
    ]
    
    print("测试场景：中级训练者，卧推动作，RPE=8.0")
    print()
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"测试 {i}: {test_case['description']}")
        print("-" * 80)
        
        input_data = {
            "user_id": "test_user",
            "exercise_id": "bench_press",
            "training_goal": test_case["training_goal"],
            "reps_target": 10,
            "rpe_target": 8.0,
            "user_level": "intermediate"
        }
        
        result = await calculator.execute(input_data)
        
        if result["success"]:
            adjustments = result["adjustments"]
            calculation = result["calculation"]
            
            print(f"✅ 计算成功")
            print(f"   目标调整因子: {adjustments['goal_adjustment']:.2f}")
            print(f"   预期调整因子: {test_case['expected_adjustment']:.2f}")
            print(f"   推荐重量: {calculation['recommended_weight']}kg")
            print(f"   重量范围: {calculation['weight_range'][0]}-{calculation['weight_range'][1]}kg")
            print(f"   估算1RM: {calculation['reps_1rm_estimate']}kg")
            print(f"   1RM百分比: {calculation['percentage_of_1rm']}%")
            
            # 验证调整因子
            if abs(adjustments['goal_adjustment'] - test_case['expected_adjustment']) < 0.01:
                print(f"   ✅ 调整因子正确")
            else:
                print(f"   ❌ 调整因子错误")
            
            # 显示进阶指导
            print(f"   进阶指导:")
            for guideline in result["progression_guidelines"][:2]:
                print(f"     - {guideline}")
        else:
            print(f"❌ 计算失败")
        
        print()
    
    print("=" * 80)
    print("测试完成")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_weight_goal_adjustment())
