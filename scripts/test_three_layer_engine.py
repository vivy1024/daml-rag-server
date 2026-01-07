#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试三层检索引擎

验证Neo4j字段修复后的实际执行情况
"""

import asyncio
import sys
import os
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 添加项目路径
sys.path.insert(0, '/app')

from src.framework.retrieval.true_three_layer_engine import TrueThreeLayerEngine


async def test_three_layer_engine():
    """测试三层检索引擎"""
    print("=" * 60)
    print("测试三层检索引擎")
    print("=" * 60)
    
    # 初始化引擎（显式传递Neo4j配置）
    neo4j_uri = os.getenv('NEO4J_URI', 'bolt://neo4j:7687')
    neo4j_user = os.getenv('NEO4J_USER', 'neo4j')
    neo4j_password = os.getenv('NEO4J_PASSWORD')
    
    print(f"\nNeo4j配置:")
    print(f"  URI: {neo4j_uri}")
    print(f"  User: {neo4j_user}")
    print(f"  Password: {'***' if neo4j_password else 'None'}")
    
    engine = TrueThreeLayerEngine(
        graphrag_api_port="8001",
        neo4j_uri=neo4j_uri,
        neo4j_user=neo4j_user,
        neo4j_password=neo4j_password,
        enable_neo4j_direct=True
    )
    
    print(f"\nNeo4j可用性: {engine.neo4j_available}")
    
    # 测试查询
    query = "推荐适合初学者的胸部增肌训练动作，可用器械：哑铃、杠铃"
    
    print(f"\n查询: {query}")
    print("-" * 60)
    
    # 执行三层检索
    result = await engine.execute_three_layer_query(
        query=query,
        domain="fitness_exercises",
        user_id="21",
        user_profile={
            "fitness_level": "beginner",
            "available_equipment": ["哑铃", "杠铃"]
        },
        filters={
            "muscle_group": "胸部",
            "difficulty_level": "beginner",
            "available_equipment": ["哑铃", "杠铃"]
        },
        top_k=10,
        safety_check=True
    )
    
    # 输出结果
    print(f"\n【Layer 1 - 向量检索】")
    print(f"  成功: {result.layer_1_result.success}")
    print(f"  结果数: {len(result.layer_1_result.results)}")
    print(f"  置信度: {result.layer_1_result.confidence:.2f}")
    print(f"  耗时: {result.layer_1_result.execution_time_ms:.0f}ms")
    if result.layer_1_result.error:
        print(f"  错误: {result.layer_1_result.error}")
    
    print(f"\n【Layer 2 - 图谱推理】")
    print(f"  成功: {result.layer_2_result.success}")
    print(f"  结果数: {len(result.layer_2_result.results)}")
    print(f"  置信度: {result.layer_2_result.confidence:.2f}")
    print(f"  耗时: {result.layer_2_result.execution_time_ms:.0f}ms")
    print(f"  数据源: {result.layer_2_result.metadata.get('source', 'unknown')}")
    if result.layer_2_result.error:
        print(f"  错误: {result.layer_2_result.error}")
    
    # 检查equipment字段
    if result.layer_2_result.results:
        first_result = result.layer_2_result.results[0]
        print(f"\n  第一个结果的字段:")
        print(f"    - exercise_name_zh: {first_result.get('exercise_name_zh', 'N/A')}")
        print(f"    - equipment: {first_result.get('equipment', 'N/A')}")
        print(f"    - difficulty: {first_result.get('difficulty', 'N/A')}")
    
    print(f"\n【Layer 3 - 业务规则】")
    print(f"  成功: {result.layer_3_result.success}")
    print(f"  结果数: {len(result.layer_3_result.results)}")
    print(f"  置信度: {result.layer_3_result.confidence:.2f}")
    print(f"  耗时: {result.layer_3_result.execution_time_ms:.0f}ms")
    
    print(f"\n【最终结果】")
    print(f"  总结果数: {len(result.final_results)}")
    print(f"  总置信度: {result.total_confidence:.2f}")
    print(f"  总耗时: {result.total_execution_time_ms:.0f}ms")
    print(f"  推理: {result.reasoning}")
    
    if result.final_results:
        print(f"\n【前3个推荐】")
        for i, rec in enumerate(result.final_results[:3], 1):
            print(f"  {i}. {rec.get('exercise_name_zh', 'N/A')}")
            print(f"     器械: {rec.get('equipment', 'N/A')}")
            print(f"     难度: {rec.get('difficulty', 'N/A')}")
    
    print("\n" + "=" * 60)
    
    # 关闭引擎
    engine.close()


if __name__ == "__main__":
    asyncio.run(test_three_layer_engine())
