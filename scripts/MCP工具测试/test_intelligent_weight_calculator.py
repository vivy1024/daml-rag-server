"""
智能重量计算器工具测试脚本

测试intelligent_weight_calculator工具的实际功能
"""

import asyncio
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.framework.clients.neo4j_client import Neo4jClient
from qdrant_client import QdrantClient
from src.applications.fitness.mcp_tools.training.intelligent_weight_calculator import (
    IntelligentWeightCalculator
)
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_intelligent_weight_calculator():
    """测试智能重量计算器"""
    print("\n" + "=" * 80)
    print("智能重量计算器工具测试")
    print("=" * 80)

    # 初始化客户端
    neo4j_client = Neo4jClient()
    await neo4j_client.connect()
    qdrant_client = QdrantClient(host="localhost", port=6333)

    # 创建工具实例
    calculator = IntelligentWeightCalculator(
        neo4j_client=neo4j_client,
        qdrant_client=qdrant_client,
        three_layer_engine=None,  # 不需要三层检索
        logger=logger
    )

    # 测试场景1：中级训练者增肌训练
    print("\n" + "-" * 80)
    print("测试场景1：中级训练者增肌训练（卧推）")
    print("-" * 80)

    input_data_1 = {
        "user_id": "user_123",
        "exercise_id": "bench_press",
        "training_goal": "hypertrophy",
        "reps_target": 10,
        "rpe_target": 8.0,
        "user_level": "intermediate"
    }

    result_1 = await calculator.execute(input_data_1)

    print(f"\n✅ 执行成功: {result_1['success']}")
    print(f"⏱️  执行时间: {result_1['execution_time_ms']:.2f}ms")
    print(f"🎯 置信度: {result_1['confidence_score']}%")

    print("\n📊 计算结果:")
    calc = result_1['calculation']
    print(f"  推荐重量: {calc['recommended_weight']}kg")
    print(f"  重量范围: {calc['weight_range'][0]}kg - {calc['weight_range'][1]}kg")
    print(f"  估算1RM: {calc['reps_1rm_estimate']}kg")
    print(f"  1RM百分比: {calc['percentage_of_1rm']}%")
    print(f"  RPE相关性: {calc['rpe_correlation']}")

    print("\n🔧 调整因子:")
    adj = result_1['adjustments']
    print(f"  水平调整: {adj['level_adjustment']}")
    print(f"  目标调整: {adj['goal_adjustment']}")
    print(f"  疲劳调整: {adj['fatigue_adjustment']}")
    print(f"  总调整: {adj['total_adjustment']}")

    print("\n⚠️  安全考虑:")
    for i, consideration in enumerate(result_1['safety_considerations'], 1):
        print(f"  {i}. {consideration}")

    print("\n📈 进阶指导:")
    for i, guideline in enumerate(result_1['progression_guidelines'], 1):
        print(f"  {i}. {guideline}")

    # 测试场景2：高级训练者力量训练
    print("\n" + "-" * 80)
    print("测试场景2：高级训练者力量训练（深蹲）")
    print("-" * 80)

    input_data_2 = {
        "user_id": "user_456",
        "exercise_id": "squat",
        "training_goal": "strength",
        "reps_target": 3,
        "rpe_target": 9.0,
        "user_level": "advanced"
    }

    result_2 = await calculator.execute(input_data_2)

    print(f"\n✅ 执行成功: {result_2['success']}")
    print(f"⏱️  执行时间: {result_2['execution_time_ms']:.2f}ms")

    print("\n📊 计算结果:")
    calc = result_2['calculation']
    print(f"  推荐重量: {calc['recommended_weight']}kg")
    print(f"  重量范围: {calc['weight_range'][0]}kg - {calc['weight_range'][1]}kg")
    print(f"  估算1RM: {calc['reps_1rm_estimate']}kg")
    print(f"  1RM百分比: {calc['percentage_of_1rm']}%")

    # 测试场景3：初学者耐力训练
    print("\n" + "-" * 80)
    print("测试场景3：初学者耐力训练（肩推）")
    print("-" * 80)

    input_data_3 = {
        "user_id": "user_789",
        "exercise_id": "overhead_press",
        "training_goal": "endurance",
        "reps_target": 15,
        "rpe_target": 7.0,
        "user_level": "beginner"
    }

    result_3 = await calculator.execute(input_data_3)

    print(f"\n✅ 执行成功: {result_3['success']}")
    print(f"⏱️  执行时间: {result_3['execution_time_ms']:.2f}ms")

    print("\n📊 计算结果:")
    calc = result_3['calculation']
    print(f"  推荐重量: {calc['recommended_weight']}kg")
    print(f"  重量范围: {calc['weight_range'][0]}kg - {calc['weight_range'][1]}kg")
    print(f"  估算1RM: {calc['reps_1rm_estimate']}kg")

    # 对比不同用户水平
    print("\n" + "-" * 80)
    print("对比分析：不同用户水平的重量差异")
    print("-" * 80)

    levels = ["beginner", "intermediate", "advanced"]
    weights = []

    for level in levels:
        input_data = {
            "user_id": f"user_{level}",
            "exercise_id": "bench_press",
            "training_goal": "hypertrophy",
            "reps_target": 10,
            "rpe_target": 8.0,
            "user_level": level
        }
        result = await calculator.execute(input_data)
        weight = result['calculation']['recommended_weight']
        weights.append(weight)
        print(f"  {level:12s}: {weight}kg")

    print(f"\n  重量增长: 初学者 → 中级 → 高级")
    print(f"  百分比: 100% → {weights[1]/weights[0]*100:.0f}% → {weights[2]/weights[0]*100:.0f}%")

    print("\n" + "=" * 80)
    print("✅ 所有测试完成")
    print("=" * 80)

    # 关闭连接
    try:
        await neo4j_client.close()
    except AttributeError:
        pass  # Neo4j客户端可能没有close方法
    
    try:
        qdrant_client.close()
    except Exception:
        pass  # Qdrant客户端关闭可能失败


if __name__ == "__main__":
    asyncio.run(test_intelligent_weight_calculator())
