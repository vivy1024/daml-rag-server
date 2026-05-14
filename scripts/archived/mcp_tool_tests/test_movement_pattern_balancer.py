"""
测试动作模式平衡器工具

验证工具的基本功能和业务逻辑
"""

import asyncio
import sys
import os
import logging
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.framework.clients.neo4j_client import Neo4jClient
from qdrant_client import QdrantClient
from src.applications.fitness.mcp_tools.training.movement_pattern_balancer import MovementPatternBalancer

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test_movement_pattern_balancer")


async def test_movement_pattern_balancer():
    """测试动作模式平衡器"""
    print("=" * 80)
    print("测试动作模式平衡器工具")
    print("=" * 80)
    
    # 初始化客户端
    neo4j_client = Neo4jClient()
    await neo4j_client.connect()
    qdrant_client = QdrantClient(host="localhost", port=6333)
    
    # 创建工具实例
    tool = MovementPatternBalancer(
        neo4j_client=neo4j_client,
        qdrant_client=qdrant_client,
        three_layer_engine=None,
        logger=logger
    )
    
    print(f"\n✅ 工具名称: {tool.get_name()}")
    print(f"✅ 工具描述: {tool.get_description()}")
    print(f"✅ 工具分类: {tool.get_category()}")
    print(f"✅ 工具复杂度: {tool.get_complexity()}")
    
    # 测试用例1：基本平衡分析
    print("\n" + "=" * 80)
    print("测试用例1：基本平衡分析")
    print("=" * 80)
    
    test_input_1 = {
        "user_id": "test_user_123",
        "current_program": ["1", "2", "3"],  # 使用实际的exercise_id
        "target_muscle_groups": ["胸大肌", "背阔肌", "股四头肌"]
    }
    
    print(f"\n输入参数:")
    print(f"  - 用户ID: {test_input_1['user_id']}")
    print(f"  - 当前计划: {test_input_1['current_program']}")
    print(f"  - 目标肌群: {test_input_1['target_muscle_groups']}")
    
    result_1 = await tool.execute(test_input_1)
    
    print(f"\n执行结果:")
    print(f"  - 成功: {result_1['success']}")
    print(f"  - 执行时间: {result_1['execution_time_ms']:.2f}ms")
    
    if result_1['success']:
        balance = result_1['balance_analysis']
        print(f"\n平衡分析:")
        print(f"  - 平衡分数: {balance['balanced_score']:.2f}")
        print(f"  - 不平衡模式数量: {len(balance['imbalanced_patterns'])}")
        
        if balance['imbalanced_patterns']:
            print(f"\n不平衡模式:")
            for pattern in balance['imbalanced_patterns'][:3]:
                print(f"    • {pattern}")
        
        print(f"\n协同覆盖:")
        for muscle, synergies in list(balance['synergy_coverage'].items())[:3]:
            print(f"    • {muscle}: {', '.join(synergies) if synergies else '无'}")
        
        print(f"\n拮抗平衡:")
        for muscle, status in list(balance['antagonist_balance'].items())[:3]:
            print(f"    • {muscle}: {status}")
        
        print(f"\n程序调整建议:")
        for i, adjustment in enumerate(result_1['program_adjustments'][:5], 1):
            print(f"    {i}. {adjustment}")
    
    # 测试用例2：空计划
    print("\n" + "=" * 80)
    print("测试用例2：空计划")
    print("=" * 80)
    
    test_input_2 = {
        "user_id": "test_user_456",
        "current_program": [],
        "target_muscle_groups": []
    }
    
    print(f"\n输入参数:")
    print(f"  - 用户ID: {test_input_2['user_id']}")
    print(f"  - 当前计划: {test_input_2['current_program']}")
    print(f"  - 目标肌群: {test_input_2['target_muscle_groups']}")
    
    result_2 = await tool.execute(test_input_2)
    
    print(f"\n执行结果:")
    print(f"  - 成功: {result_2['success']}")
    print(f"  - 执行时间: {result_2['execution_time_ms']:.2f}ms")
    
    if result_2['success']:
        balance = result_2['balance_analysis']
        print(f"\n平衡分析:")
        print(f"  - 平衡分数: {balance['balanced_score']:.2f}")
        print(f"  - 不平衡模式数量: {len(balance['imbalanced_patterns'])}")
    
    # 测试用例3：单一肌群
    print("\n" + "=" * 80)
    print("测试用例3：单一肌群训练")
    print("=" * 80)
    
    test_input_3 = {
        "user_id": "test_user_789",
        "current_program": ["1", "2"],
        "target_muscle_groups": ["胸大肌"]
    }
    
    print(f"\n输入参数:")
    print(f"  - 用户ID: {test_input_3['user_id']}")
    print(f"  - 当前计划: {test_input_3['current_program']}")
    print(f"  - 目标肌群: {test_input_3['target_muscle_groups']}")
    
    result_3 = await tool.execute(test_input_3)
    
    print(f"\n执行结果:")
    print(f"  - 成功: {result_3['success']}")
    print(f"  - 执行时间: {result_3['execution_time_ms']:.2f}ms")
    
    if result_3['success']:
        balance = result_3['balance_analysis']
        print(f"\n平衡分析:")
        print(f"  - 平衡分数: {balance['balanced_score']:.2f}")
        print(f"  - 不平衡模式数量: {len(balance['imbalanced_patterns'])}")
        
        if balance['imbalanced_patterns']:
            print(f"\n不平衡模式:")
            for pattern in balance['imbalanced_patterns']:
                print(f"    • {pattern}")
    
    print("\n" + "=" * 80)
    print("✅ 所有测试完成")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_movement_pattern_balancer())
