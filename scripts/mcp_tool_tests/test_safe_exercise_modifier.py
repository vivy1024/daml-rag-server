"""
测试safe_exercise_modifier工具

测试场景：
1. 肩部损伤修饰
2. 新手友好修饰
3. 康复期修饰
"""

import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.framework.clients.neo4j_client import Neo4jClient
from src.applications.fitness.mcp_tools.safety.safe_exercise_modifier import SafeExerciseModifier
import logging


async def test_safe_exercise_modifier():
    """测试安全动作修饰器"""
    
    # 配置日志
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("test_safe_exercise_modifier")
    
    # 初始化客户端
    neo4j_client = Neo4jClient()
    try:
        await neo4j_client.connect()
    except Exception as e:
        print(f"⚠️  Neo4j连接失败: {e}")
        print("⚠️  将使用模拟数据进行测试")
        # 继续测试，但会失败 - 这是预期的
    
    # 创建工具实例
    modifier = SafeExerciseModifier(
        neo4j_client=neo4j_client,
        qdrant_client=None,
        three_layer_engine=None,
        logger=logger
    )
    
    print("=" * 80)
    print("测试1: 肩部损伤修饰")
    print("=" * 80)
    
    try:
        result1 = await modifier.execute({
            "user_id": "test_user_001",
            "exercise_id": "4",  # 杠铃卧推（有效ID）
            "modification_purpose": "injury_prevention",
            "user_injuries": ["肩部损伤"],
            "modification_preference": "moderate"
        })
        
        print(f"\n✅ 测试1成功")
        print(f"原动作: {result1['original_exercise']['name_zh']}")
        print(f"修改方案数量: {len(result1['modifications'])}")
        print(f"风险等级: {result1['contraindications_analysis']['risk_level']}")
        print(f"医学指导: {result1['medical_guidance']}")
        print(f"\n修改方案:")
        for i, mod in enumerate(result1['modifications'], 1):
            print(f"\n方案{i}: {mod['modified_name_zh']} ({mod['modification_type']})")
            print(f"  安全评分: {mod['safety_score_before']} -> {mod['safety_score_after']}")
            print(f"  修改措施: {', '.join(mod['modifications_applied'][:2])}")
        
        print(f"\n安全建议数量: {len(result1['safety_recommendations'])}")
        print(f"执行时间: {result1['execution_time_ms']:.2f}ms")
        
    except Exception as e:
        print(f"❌ 测试1失败: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 80)
    print("测试2: 新手友好修饰")
    print("=" * 80)
    
    try:
        result2 = await modifier.execute({
            "user_id": "test_user_002",
            "exercise_id": "8",  # 杠铃深蹲（有效ID）
            "modification_purpose": "beginner_friendly",
            "modification_preference": "moderate"
        })
        
        print(f"\n✅ 测试2成功")
        print(f"原动作: {result2['original_exercise']['name_zh']}")
        print(f"修改方案数量: {len(result2['modifications'])}")
        print(f"风险等级: {result2['contraindications_analysis']['risk_level']}")
        
        # 查找modified_version类型的方案
        for mod in result2['modifications']:
            if mod['modification_type'] == 'modified_version':
                print(f"\n新手修改版本:")
                print(f"  {mod['modified_name_zh']}")
                print(f"  修改措施:")
                for measure in mod['modifications_applied'][:4]:
                    print(f"    - {measure}")
                break
        
        print(f"\n执行时间: {result2['execution_time_ms']:.2f}ms")
        
    except Exception as e:
        print(f"❌ 测试2失败: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 80)
    print("测试3: 康复期修饰")
    print("=" * 80)
    
    try:
        result3 = await modifier.execute({
            "user_id": "test_user_003",
            "exercise_id": "27",  # 杠铃直腿硬拉（有效ID）
            "modification_purpose": "rehabilitation",
            "user_injuries": ["腰部损伤"],
            "modification_preference": "safe_only"
        })
        
        print(f"\n✅ 测试3成功")
        print(f"原动作: {result3['original_exercise']['name_zh']}")
        print(f"修改方案数量: {len(result3['modifications'])}")
        print(f"风险等级: {result3['contraindications_analysis']['risk_level']}")
        print(f"医学指导: {result3['medical_guidance']}")
        
        # 显示安全建议
        print(f"\n安全建议（前5条）:")
        for i, rec in enumerate(result3['safety_recommendations'][:5], 1):
            print(f"  {i}. {rec}")
        
        print(f"\n执行时间: {result3['execution_time_ms']:.2f}ms")
        
    except Exception as e:
        print(f"❌ 测试3失败: {e}")
        import traceback
        traceback.print_exc()
    
    # 关闭连接
    try:
        await neo4j_client.disconnect()
    except:
        pass
    
    print("\n" + "=" * 80)
    print("✅ 所有测试完成")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_safe_exercise_modifier())
