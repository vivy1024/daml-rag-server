"""
测试改进后的exercise_alternative_finder工具

验证改进方案的效果：
- 方案1: 改进的相似度计算算法
- 方案2: 灵活的查询策略

作者: BUILD_BODY Team
日期: 2025-12-14
"""

import asyncio
import sys
import os

# 添加src目录到Python路径
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, src_path)

from applications.fitness.mcp_tools.exercise.exercise_alternative_finder import ExerciseAlternativeFinder
from framework.clients.neo4j_client import Neo4jClient, Neo4jClientConfig


async def test_improved_finder():
    """测试改进后的查找器"""
    
    print("=" * 80)
    print("测试改进后的Exercise Alternative Finder")
    print("=" * 80)
    
    # 初始化Neo4j连接
    neo4j_config = Neo4jClientConfig.from_env()
    neo4j_client = Neo4jClient(config=neo4j_config)
    await neo4j_client.connect()
    
    # 初始化工具
    finder = ExerciseAlternativeFinder(
        neo4j_client=neo4j_client,
        qdrant_client=None,
        three_layer_engine=None
    )
    
    # 测试场景1: 基础替代（应该返回5个结果）
    print("\n" + "=" * 80)
    print("测试场景1: 基础替代 - 寻找杠铃卧推的替代动作（胸部）")
    print("=" * 80)
    
    result1 = await finder.execute({
        "user_id": "test_user_001",
        "original_exercise_id": "4",  # 杠铃卧推（胸部）
        "reason": "variety",
        "constraints": {}
    })
    
    print(f"\n✅ 执行成功: {result1['success']}")
    print(f"📊 找到替代方案数量: {len(result1['alternatives'])}")
    print(f"⏱️  执行时间: {result1['execution_time_ms']:.2f}ms")
    print(f"🎯 置信度: {result1.get('confidence_score', 0)}")
    
    if result1['alternatives']:
        print("\n替代动作列表:")
        for i, alt in enumerate(result1['alternatives'], 1):
            print(f"\n{i}. {alt['name_zh']} ({alt['name_en']})")
            print(f"   相似度: {alt['similarity_score']}")
            print(f"   难度: {alt['difficulty_level']}")
            print(f"   器械: {alt['equipment_needed']}")
            print(f"   目标肌群: {', '.join(alt['target_muscles'])}")
            print(f"   匹配原因: {', '.join(alt['match_reasons'])}")
    
    # 测试场景2: 器械不可用（测试灵活查询）
    print("\n" + "=" * 80)
    print("测试场景2: 器械不可用 - 只有哑铃和器械可用")
    print("=" * 80)
    
    result2 = await finder.execute({
        "user_id": "test_user_002",
        "original_exercise_id": "4",  # 杠铃卧推
        "reason": "equipment_unavailable",
        "constraints": {
            "available_equipment": ["哑铃", "器械", "徒手"]
        }
    })
    
    print(f"\n✅ 执行成功: {result2['success']}")
    print(f"📊 找到替代方案数量: {len(result2['alternatives'])}")
    print(f"⏱️  执行时间: {result2['execution_time_ms']:.2f}ms")
    
    if result2['alternatives']:
        print("\n替代动作列表:")
        for i, alt in enumerate(result2['alternatives'], 1):
            print(f"\n{i}. {alt['name_zh']} ({alt['name_en']})")
            print(f"   相似度: {alt['similarity_score']}")
            print(f"   器械: {alt['equipment_needed']}")
    else:
        print("\n⚠️  未找到替代方案（可能需要进一步放宽条件）")
    
    # 测试场景3: 难度过高（测试灵活查询）
    print("\n" + "=" * 80)
    print("测试场景3: 难度过高 - 寻找更简单的替代动作")
    print("=" * 80)
    
    result3 = await finder.execute({
        "user_id": "test_user_003",
        "original_exercise_id": "8",  # 杠铃深蹲（中级）
        "reason": "difficulty_too_high",
        "constraints": {
            "skill_level": "beginner"
        }
    })
    
    print(f"\n✅ 执行成功: {result3['success']}")
    print(f"📊 找到替代方案数量: {len(result3['alternatives'])}")
    print(f"⏱️  执行时间: {result3['execution_time_ms']:.2f}ms")
    
    if result3['alternatives']:
        print("\n替代动作列表:")
        for i, alt in enumerate(result3['alternatives'], 1):
            print(f"\n{i}. {alt['name_zh']} ({alt['name_en']})")
            print(f"   相似度: {alt['similarity_score']}")
            print(f"   难度: {alt['difficulty_level']}")
    else:
        print("\n⚠️  未找到替代方案（可能需要进一步放宽条件）")
    
    # 测试场景4: 损伤限制
    print("\n" + "=" * 80)
    print("测试场景4: 损伤限制 - 肩部受伤")
    print("=" * 80)
    
    result4 = await finder.execute({
        "user_id": "test_user_004",
        "original_exercise_id": "4",  # 杠铃卧推
        "reason": "injury",
        "constraints": {
            "injury_limitations": ["肩部受伤"]
        }
    })
    
    print(f"\n✅ 执行成功: {result4['success']}")
    print(f"📊 找到替代方案数量: {len(result4['alternatives'])}")
    print(f"⏱️  执行时间: {result4['execution_time_ms']:.2f}ms")
    
    if result4['alternatives']:
        print("\n替代动作列表:")
        for i, alt in enumerate(result4['alternatives'], 1):
            print(f"\n{i}. {alt['name_zh']} ({alt['name_en']})")
            print(f"   相似度: {alt['similarity_score']}")
            print(f"   调整建议: {', '.join(alt['adjustments_needed'])}")
    
    # 测试场景5: 二头肌动作替代（杠铃弯举）
    print("\n" + "=" * 80)
    print("测试场景5: 二头肌动作替代 - 寻找杠铃弯举的替代动作")
    print("=" * 80)
    
    result5 = await finder.execute({
        "user_id": "test_user_005",
        "original_exercise_id": "1",  # 杠铃弯举（二头肌）
        "reason": "variety",
        "constraints": {}
    })
    
    print(f"\n✅ 执行成功: {result5['success']}")
    print(f"📊 找到替代方案数量: {len(result5['alternatives'])}")
    print(f"⏱️  执行时间: {result5['execution_time_ms']:.2f}ms")
    
    if result5['alternatives']:
        print("\n替代动作列表:")
        for i, alt in enumerate(result5['alternatives'], 1):
            print(f"\n{i}. {alt['name_zh']} ({alt['name_en']})")
            print(f"   相似度: {alt['similarity_score']}")
            print(f"   目标肌群: {', '.join(alt['target_muscles'])}")
            print(f"   匹配原因: {', '.join(alt['match_reasons'])}")
    
    # 关闭连接
    await neo4j_client.disconnect()
    
    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)
    
    # 总结
    print("\n📊 测试总结:")
    print(f"场景1（胸部-杠铃卧推）: {len(result1['alternatives'])}个结果")
    print(f"场景2（器械限制）: {len(result2['alternatives'])}个结果")
    print(f"场景3（难度过高）: {len(result3['alternatives'])}个结果")
    print(f"场景4（损伤限制）: {len(result4['alternatives'])}个结果")
    print(f"场景5（二头肌-杠铃弯举）: {len(result5['alternatives'])}个结果")
    
    total_results = (
        len(result1['alternatives']) +
        len(result2['alternatives']) +
        len(result3['alternatives']) +
        len(result4['alternatives']) +
        len(result5['alternatives'])
    )
    
    print(f"\n总计: {total_results}个替代方案")
    
    if total_results >= 15:
        print("\n✅ 改进效果显著！所有场景都返回了合理的结果")
    elif total_results >= 10:
        print("\n⚠️  改进有效，但部分场景仍需优化")
    else:
        print("\n❌ 改进效果有限，需要进一步调整")


if __name__ == "__main__":
    asyncio.run(test_improved_finder())
