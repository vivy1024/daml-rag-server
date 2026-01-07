"""
测试meal_plan_designer工具（营养指导模式）

验证膳食营养指导器的功能
"""

import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.framework.clients.neo4j_client import Neo4jClient
from src.utils.qdrant_helper import QdrantHelper
from src.applications.fitness.mcp_tools.nutrition.meal_plan_designer import MealPlanDesigner
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_meal_plan_designer():
    """测试膳食营养指导器"""
    
    # 初始化客户端
    neo4j_client = Neo4jClient()
    await neo4j_client.connect()
    
    qdrant_client = QdrantHelper()
    
    try:
        # 创建工具实例
        tool = MealPlanDesigner(
            neo4j_client=neo4j_client,
            qdrant_client=qdrant_client,
            three_layer_engine=None,
            logger=logger
        )
        
        print("\n" + "="*80)
        print("测试1: 增肌营养指导（平衡饮食）")
        print("="*80)
        
        input_data = {
            "user_id": "test_user_001",
            "target_calories": 2500.0,
            "target_protein_grams": 180.0,
            "target_carbs_grams": 300.0,
            "target_fat_grams": 70.0,
            "dietary_preference": "balanced",
            "meals_per_day": 5,
            "training_days_per_week": 5,
            "fitness_goal": "muscle_gain"
        }
        
        result = await tool.execute_with_monitoring(input_data)
        
        if result["success"]:
            print(f"\n✅ 测试成功")
            print(f"执行时间: {result['metadata']['execution_time_ms']:.2f}ms")
            
            # 显示计划概览
            summary = result["plan_summary"]
            print(f"\n📊 营养指导模式:")
            print(f"  理念: {summary['philosophy']}")
            print(f"  灵活性: {summary['flexibility']}")
            
            print(f"\n🎯 目标营养:")
            target = summary['target_nutrition']
            print(f"  热量: {target['calories']:.0f}卡")
            print(f"  蛋白质: {target['protein']:.0f}g")
            print(f"  碳水: {target['carbs']:.0f}g")
            print(f"  脂肪: {target['fat']:.0f}g")
            
            # 显示训练日方案
            training_plan = result["training_day_plan"]
            print(f"\n🏋️ 训练日方案:")
            print(f"  每日总计: {training_plan['daily_totals']['calories']:.0f}卡")
            print(f"  水分目标: {training_plan['hydration_target']}")
            print(f"\n  餐次安排:")
            for meal in training_plan["meals"][:3]:  # 只显示前3餐
                print(f"    {meal['meal_time']} - {meal['meal_type']}:")
                print(f"      目标: {meal['target_calories']:.0f}卡 "
                      f"(蛋白{meal['target_protein']:.0f}g, "
                      f"碳水{meal['target_carbs']:.0f}g, "
                      f"脂肪{meal['target_fat']:.0f}g)")
                if meal['nutrition_tips']:
                    print(f"      提示: {meal['nutrition_tips'][0]}")
            
            # 显示食物推荐
            print(f"\n🍽️ 食物推荐（基于营养益处）:")
            for rec in result["food_recommendations"][:2]:  # 只显示前2类
                print(f"\n  {rec['category']}:")
                print(f"    推荐: {', '.join(rec['recommended_foods'][:5])}")
                print(f"    益处: {rec['nutrition_benefits'][0]}")
            
            # 显示微量元素指导
            micro = result["micronutrient_guidance"]
            print(f"\n💊 关键微量元素:")
            for nutrient in micro["key_micronutrients"][:3]:  # 只显示前3个
                print(f"  • {nutrient['name']}: {nutrient['importance']}")
                print(f"    来源: {', '.join(nutrient['food_sources'][:3])}")
            
            # 显示实用建议
            print(f"\n💡 实用建议:")
            for tip in result["practical_tips"][:5]:
                print(f"  {tip}")
        
        else:
            print(f"\n❌ 测试失败: {result.get('error', {}).get('message', '未知错误')}")
        
        
        print("\n" + "="*80)
        print("测试2: 减脂营养指导")
        print("="*80)
        
        input_data2 = {
            "user_id": "test_user_002",
            "target_calories": 1800.0,
            "target_protein_grams": 150.0,
            "target_carbs_grams": 150.0,
            "target_fat_grams": 60.0,
            "dietary_preference": "high_protein",
            "meals_per_day": 4,
            "training_days_per_week": 4,
            "fitness_goal": "weight_loss"
        }
        
        result2 = await tool.execute_with_monitoring(input_data2)
        
        if result2["success"]:
            print(f"\n✅ 测试成功")
            print(f"执行时间: {result2['metadata']['execution_time_ms']:.2f}ms")
            
            # 显示休息日方案
            rest_plan = result2["rest_day_plan"]
            print(f"\n😴 休息日方案:")
            print(f"  每日总计: {rest_plan['daily_totals']['calories']:.0f}卡")
            print(f"  重点关注: {rest_plan['key_nutrients_focus'][0]}")
            
            # 显示灵活调整建议
            print(f"\n🔄 灵活调整建议:")
            for tip in result2["flexibility_tips"][:5]:
                print(f"  {tip}")
        
        else:
            print(f"\n❌ 测试失败: {result2.get('error', {}).get('message', '未知错误')}")
        
        
        print("\n" + "="*80)
        print("✅ 所有测试完成")
        print("="*80)
        
    except Exception as e:
        logger.error(f"❌ 测试过程中发生错误: {e}", exc_info=True)
    
    finally:
        # 关闭连接
        if hasattr(neo4j_client, 'close'):
            await neo4j_client.close()


if __name__ == "__main__":
    asyncio.run(test_meal_plan_designer())
