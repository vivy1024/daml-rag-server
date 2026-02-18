"""
测试运动营养优化器工具

测试场景：
1. 力量训练的营养优化
2. 耐力训练的营养优化
3. HIIT训练的营养优化
4. 不同训练时间的营养策略
"""

import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.applications.fitness.mcp_tools.nutrition.exercise_nutrition_optimization import (
    ExerciseNutritionOptimization,
    ExerciseNutritionOptimizationInput
)
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_strength_training_optimization():
    """测试力量训练的营养优化"""
    print("\n" + "="*80)
    print("测试场景1: 力量训练的营养优化")
    print("="*80)
    
    # 创建工具实例（不需要数据库连接）
    tool = ExerciseNutritionOptimization(
        neo4j_client=None,
        qdrant_client=None,
        three_layer_engine=None,
        logger=logger
    )
    
    # 测试输入
    input_data = {
        "user_id": "test_user_001",
        "training_type": "strength",
        "training_duration_minutes": 75,
        "training_intensity": "high",
        "training_time": "afternoon",
        "weight_kg": 75.0,
        "fitness_goal": "muscle_gain",
        "daily_protein_target": 150.0,
        "daily_carbs_target": 300.0,
        "current_supplements": []
    }
    
    # 执行工具
    result = await tool.execute(input_data)
    
    # 打印结果
    print(f"\n✅ 工具执行成功: {result['success']}")
    print(f"执行时间: {result['execution_time_ms']:.2f}ms")
    print(f"置信度: {result['confidence_score']}")
    
    print("\n📊 训练概览:")
    summary = result['training_summary']
    print(f"  训练类型: {summary['training_type']}")
    print(f"  训练时长: {summary['duration_minutes']}分钟")
    print(f"  训练强度: {summary['intensity']}")
    print(f"  预估消耗: {summary['estimated_calories_burned']}卡")
    print(f"  营养优先级: {summary['nutrition_priority']}")
    
    print("\n🍽️ 训练前营养窗口:")
    for window in result['pre_workout_nutrition']:
        print(f"\n  {window['timing']}:")
        print(f"    热量: {window['calories']}卡")
        print(f"    蛋白质: {window['protein_grams']}g")
        print(f"    碳水: {window['carbs_grams']}g")
        print(f"    脂肪: {window['fat_grams']}g")
        print(f"    食物示例: {', '.join(window['food_examples'][:2])}")
    
    print("\n💪 训练中营养:")
    intra = result['intra_workout_nutrition']
    print(f"  {intra['timing']}:")
    print(f"    碳水: {intra['carbs_grams']}g")
    print(f"    关键原则: {intra['key_principles'][0]}")
    
    print("\n🥤 训练后营养窗口:")
    for window in result['post_workout_nutrition']:
        print(f"\n  {window['timing']}:")
        print(f"    热量: {window['calories']}卡")
        print(f"    蛋白质: {window['protein_grams']}g")
        print(f"    碳水: {window['carbs_grams']}g")
    
    print("\n💊 补剂推荐（前5个）:")
    for i, supp in enumerate(result['supplement_recommendations'][:5], 1):
        print(f"\n  {i}. {supp['supplement_name']} ({supp['priority']})")
        print(f"     剂量: {supp['dosage']}")
        print(f"     时机: {supp['timing']}")
        print(f"     性价比: {supp['cost_effectiveness']}")
    
    print("\n😴 恢复营养:")
    for recovery in result['recovery_nutrition']:
        print(f"\n  {recovery['timing']}:")
        print(f"    关注点: {recovery['nutrition_focus'][0]}")
    
    print("\n💧 水分补充策略:")
    hydration = result['hydration_strategy']
    print(f"  每日基础: {hydration['daily_baseline']}")
    print(f"  训练额外: {hydration['training_additional']}")
    print(f"  每日总量: {hydration['total_daily']}")
    
    print("\n💡 个性化建议（前5条）:")
    for i, tip in enumerate(result['personalized_tips'][:5], 1):
        print(f"  {i}. {tip}")


async def test_endurance_training_optimization():
    """测试耐力训练的营养优化"""
    print("\n" + "="*80)
    print("测试场景2: 耐力训练的营养优化")
    print("="*80)
    
    tool = ExerciseNutritionOptimization(
        neo4j_client=None,
        qdrant_client=None,
        three_layer_engine=None,
        logger=logger
    )
    
    input_data = {
        "user_id": "test_user_002",
        "training_type": "endurance",
        "training_duration_minutes": 90,
        "training_intensity": "moderate",
        "training_time": "morning",
        "weight_kg": 65.0,
        "fitness_goal": "weight_loss",
        "daily_protein_target": 130.0,
        "daily_carbs_target": 200.0,
        "current_supplements": ["whey_protein"]
    }
    
    result = await tool.execute(input_data)
    
    print(f"\n✅ 工具执行成功: {result['success']}")
    print(f"\n📊 训练概览:")
    summary = result['training_summary']
    print(f"  训练类型: {summary['training_type']}")
    print(f"  预估消耗: {summary['estimated_calories_burned']}卡")
    print(f"  营养优先级: {summary['nutrition_priority']}")
    
    print("\n💪 训练中营养（耐力训练重点）:")
    intra = result['intra_workout_nutrition']
    print(f"  碳水需求: {intra['carbs_grams']}g")
    print(f"  关键原则:")
    for principle in intra['key_principles']:
        print(f"    - {principle}")
    
    print("\n💊 补剂推荐数量:", len(result['supplement_recommendations']))
    print("  已过滤掉已使用的补剂（乳清蛋白）")


async def test_hiit_training_optimization():
    """测试HIIT训练的营养优化"""
    print("\n" + "="*80)
    print("测试场景3: HIIT训练的营养优化")
    print("="*80)
    
    tool = ExerciseNutritionOptimization(
        neo4j_client=None,
        qdrant_client=None,
        three_layer_engine=None,
        logger=logger
    )
    
    input_data = {
        "user_id": "test_user_003",
        "training_type": "hiit",
        "training_duration_minutes": 30,
        "training_intensity": "very_high",
        "training_time": "evening",
        "weight_kg": 70.0,
        "fitness_goal": "recomp",
        "daily_protein_target": 140.0,
        "daily_carbs_target": 250.0,
        "current_supplements": ["whey_protein", "creatine", "caffeine"]
    }
    
    result = await tool.execute(input_data)
    
    print(f"\n✅ 工具执行成功: {result['success']}")
    print(f"\n📊 训练概览:")
    summary = result['training_summary']
    print(f"  训练类型: {summary['training_type']}")
    print(f"  训练强度: {summary['intensity']}")
    print(f"  预估消耗: {summary['estimated_calories_burned']}卡")
    
    print("\n😴 恢复营养（HIIT对神经系统压力大）:")
    for recovery in result['recovery_nutrition']:
        print(f"\n  {recovery['timing']}:")
        for focus in recovery['nutrition_focus']:
            print(f"    - {focus}")
    
    print("\n💊 补剂推荐（已过滤3个已使用的）:")
    for supp in result['supplement_recommendations'][:3]:
        print(f"  - {supp['supplement_name']} ({supp['priority']})")


async def test_morning_vs_evening_training():
    """测试早晨vs晚间训练的营养策略差异"""
    print("\n" + "="*80)
    print("测试场景4: 早晨 vs 晚间训练的营养策略")
    print("="*80)
    
    tool = ExerciseNutritionOptimization(
        neo4j_client=None,
        qdrant_client=None,
        three_layer_engine=None,
        logger=logger
    )
    
    # 早晨训练
    morning_input = {
        "user_id": "test_user_004",
        "training_type": "strength",
        "training_duration_minutes": 60,
        "training_intensity": "moderate",
        "training_time": "morning",
        "weight_kg": 80.0,
        "fitness_goal": "muscle_gain",
        "daily_protein_target": 160.0,
        "daily_carbs_target": 320.0,
        "current_supplements": []
    }
    
    morning_result = await tool.execute(morning_input)
    
    # 晚间训练
    evening_input = morning_input.copy()
    evening_input["training_time"] = "evening"
    
    evening_result = await tool.execute(evening_input)
    
    print("\n🌅 早晨训练的个性化建议:")
    morning_tips = [tip for tip in morning_result['personalized_tips'] if '早晨' in tip or '🌅' in tip]
    for tip in morning_tips:
        print(f"  {tip}")
    
    print("\n🌙 晚间训练的个性化建议:")
    evening_tips = [tip for tip in evening_result['personalized_tips'] if '晚间' in tip or '🌙' in tip]
    for tip in evening_tips:
        print(f"  {tip}")


async def main():
    """运行所有测试"""
    print("\n" + "="*80)
    print("运动营养优化器工具测试")
    print("="*80)
    
    try:
        # 测试1: 力量训练
        await test_strength_training_optimization()
        
        # 测试2: 耐力训练
        await test_endurance_training_optimization()
        
        # 测试3: HIIT训练
        await test_hiit_training_optimization()
        
        # 测试4: 早晨vs晚间训练
        await test_morning_vs_evening_training()
        
        print("\n" + "="*80)
        print("✅ 所有测试完成！")
        print("="*80)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
