"""
测试营养摄入分析器工具

验证NutritionIntakeAnalyzer的基本功能
"""

import asyncio
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.applications.fitness.mcp_tools.nutrition.nutrition_intake_analyzer import (
    NutritionIntakeAnalyzer,
    NutritionIntakeAnalyzerInput
)
from src.framework.clients.neo4j_client import Neo4jClient
from qdrant_client import QdrantClient
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_nutrition_intake_analyzer():
    """测试营养摄入分析器"""
    
    # 初始化客户端
    neo4j_client = Neo4jClient()
    try:
        await neo4j_client.connect()
    except Exception as e:
        logger.warning(f"⚠️ Neo4j连接失败: {e}")
        logger.warning("⚠️ 将使用模拟数据进行测试")
    
    qdrant_client = QdrantClient(
        host=os.getenv("QDRANT_HOST", "localhost"),
        port=int(os.getenv("QDRANT_PORT", "6333"))
    )
    
    # 创建工具实例
    tool = NutritionIntakeAnalyzer(
        neo4j_client=neo4j_client,
        qdrant_client=qdrant_client,
        three_layer_engine=None,  # 不需要三层检索
        logger=logger
    )
    
    print("\n" + "="*80)
    print("测试1: 基本营养摄入分析（提供目标值）")
    print("="*80)
    
    # 测试输入
    test_input = {
        "user_id": "test_user_001",
        "daily_food_intake": [
            {
                "food_name": "鸡胸肉",
                "portion_size": 200,
                "meal_type": "lunch"
            },
            {
                "food_name": "糙米饭",
                "portion_size": 150,
                "meal_type": "lunch"
            },
            {
                "food_name": "西兰花",
                "portion_size": 100,
                "meal_type": "lunch"
            },
            {
                "food_name": "鸡蛋",
                "portion_size": 100,
                "meal_type": "breakfast"
            },
            {
                "food_name": "牛奶",
                "portion_size": 250,
                "meal_type": "breakfast"
            }
        ],
        "target_calories": 2200,
        "target_protein_grams": 150,
        "target_carbs_grams": 250,
        "target_fat_grams": 70,
        "include_micronutrients": False,
        "fitness_goal": "muscle_gain"
    }
    
    try:
        result = await tool.execute_with_monitoring(test_input)
        
        if result["success"]:
            print("\n✅ 测试成功！")
            print(f"\n当前摄入:")
            current = result["current_intake"]
            print(f"  热量: {current['calories']:.0f}卡")
            print(f"  蛋白质: {current['protein_grams']:.0f}g")
            print(f"  碳水: {current['carbs_grams']:.0f}g")
            print(f"  脂肪: {current['fat_grams']:.0f}g")
            print(f"  纤维: {current['fiber_grams']:.0f}g")
            
            print(f"\n目标需求:")
            target = result["target_needs"]
            print(f"  热量: {target['calories']:.0f}卡")
            print(f"  蛋白质: {target['protein_grams']:.0f}g")
            print(f"  碳水: {target['carbs_grams']:.0f}g")
            print(f"  脂肪: {target['fat_grams']:.0f}g")
            
            print(f"\n营养缺口:")
            gap = result["nutrient_gap"]
            print(f"  状态: {gap['overall_status']}")
            print(f"  热量缺口: {gap['calories_gap']:+.0f}卡 ({gap['calories_gap_percentage']:+.1f}%)")
            print(f"  蛋白质缺口: {gap['protein_gap']:+.0f}g ({gap['protein_gap_percentage']:+.1f}%)")
            print(f"  碳水缺口: {gap['carbs_gap']:+.0f}g ({gap['carbs_gap_percentage']:+.1f}%)")
            print(f"  脂肪缺口: {gap['fat_gap']:+.0f}g ({gap['fat_gap_percentage']:+.1f}%)")
            print(f"  推理: {gap['reasoning']}")
            
            print(f"\n饮食质量评分:")
            quality = result["diet_quality_score"]
            print(f"  综合评分: {quality['overall_score']:.1f}/100")
            print(f"  营养密度: {quality['nutrient_density_score']:.1f}/100")
            print(f"  食物多样性: {quality['food_variety_score']:.1f}/100")
            print(f"  进餐时机: {quality['meal_timing_score']:.1f}/100")
            
            if quality['strengths']:
                print(f"\n  优势:")
                for strength in quality['strengths']:
                    print(f"    ✓ {strength}")
            
            if quality['weaknesses']:
                print(f"\n  劣势:")
                for weakness in quality['weaknesses']:
                    print(f"    ✗ {weakness}")
            
            print(f"\n改善建议 (共{len(result['improvement_suggestions'])}条):")
            for i, suggestion in enumerate(result['improvement_suggestions'][:5], 1):
                print(f"\n  {i}. [{suggestion['priority'].upper()}] {suggestion['suggestion']}")
                print(f"     原因: {suggestion['reasoning']}")
                if suggestion['example_foods']:
                    print(f"     推荐食物: {', '.join(suggestion['example_foods'][:3])}")
            
            print(f"\n执行时间: {result['execution_time_ms']:.2f}ms")
            print(f"置信度: {result['confidence_score']:.1f}%")
            
        else:
            print(f"\n❌ 测试失败: {result.get('error', {}).get('message', '未知错误')}")
            
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 清理资源
        await neo4j_client.disconnect()
        qdrant_client.close()
    
    print("\n" + "="*80)
    print("测试完成")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(test_nutrition_intake_analyzer())
