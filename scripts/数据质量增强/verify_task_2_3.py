#!/usr/bin/env python3
"""
验证任务 2.3：实现技术检查点生成（关键动作）

验证内容：
1. 关键动作是否已添加技术检查点
2. JSON格式是否正确
3. 技术检查点内容是否专业合理

作者：薛小川
日期：2025-12-15
"""

import asyncio
import sys
import os
import json

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from neo4j import AsyncGraphDatabase
from dotenv import load_dotenv


async def verify_technique_checkpoints():
    """验证技术检查点实现"""
    print("=" * 80)
    print("验证任务 2.3：实现技术检查点生成（关键动作）")
    print("=" * 80)
    
    # 加载环境变量
    load_dotenv()
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "")
    
    # 连接Neo4j
    driver = AsyncGraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
    
    # 关键动作列表（来自设计文档）
    key_exercises = [
        "杠铃深蹲",
        "杠铃硬拉",
        "杠铃卧推",
        "引体向上",
        "哑铃弯举"
    ]
    
    try:
        async with driver.session() as session:
            print("\n📋 验证关键动作的技术检查点...")
            print("-" * 80)
            
            all_valid = True
            
            for exercise_name in key_exercises:
                # 查询动作的技术检查点
                query = """
                MATCH (e:Exercise)
                WHERE e.name_zh = $name
                RETURN e.name_zh as name, 
                       e.technique_checkpoints as checkpoints,
                       e.checkpoints_source as source,
                       e.checkpoints_updated_at as updated_at
                """
                result = await session.run(query, {"name": exercise_name})
                record = await result.single()
                
                if not record:
                    print(f"\n❌ {exercise_name}: 未找到该动作")
                    all_valid = False
                    continue
                
                checkpoints_json = record["checkpoints"]
                source = record.get("source", "未知")
                updated_at = record.get("updated_at")
                
                # 验证是否有技术检查点
                if not checkpoints_json:
                    print(f"\n❌ {exercise_name}: 缺少技术检查点")
                    all_valid = False
                    continue
                
                # 验证JSON格式
                try:
                    checkpoints = json.loads(checkpoints_json)
                except json.JSONDecodeError as e:
                    print(f"\n❌ {exercise_name}: JSON格式错误 - {e}")
                    all_valid = False
                    continue
                
                # 验证是否为列表
                if not isinstance(checkpoints, list):
                    print(f"\n❌ {exercise_name}: 技术检查点不是列表格式")
                    all_valid = False
                    continue
                
                # 验证列表不为空
                if len(checkpoints) == 0:
                    print(f"\n❌ {exercise_name}: 技术检查点列表为空")
                    all_valid = False
                    continue
                
                # 验证每个检查点是字符串
                for i, cp in enumerate(checkpoints):
                    if not isinstance(cp, str):
                        print(f"\n❌ {exercise_name}: 检查点 {i+1} 不是字符串")
                        all_valid = False
                        continue
                
                # 显示验证结果
                print(f"\n✅ {exercise_name}:")
                print(f"   来源: {source}")
                print(f"   更新时间: {updated_at}")
                print(f"   检查点数量: {len(checkpoints)}")
                print(f"   技术检查点:")
                for i, cp in enumerate(checkpoints, 1):
                    print(f"      {i}. {cp}")
            
            # 统计所有有技术检查点的动作
            print("\n" + "-" * 80)
            print("📊 统计信息...")
            print("-" * 80)
            
            stats_query = """
            MATCH (e:Exercise)
            WHERE e.technique_checkpoints IS NOT NULL
            RETURN count(e) as total_with_checkpoints
            """
            stats_result = await session.run(stats_query)
            stats_record = await stats_result.single()
            total_with_checkpoints = stats_record["total_with_checkpoints"]
            
            print(f"\n   已添加技术检查点的动作总数: {total_with_checkpoints}")
            
            # 按来源统计
            source_query = """
            MATCH (e:Exercise)
            WHERE e.technique_checkpoints IS NOT NULL
            RETURN e.checkpoints_source as source, count(e) as count
            ORDER BY count DESC
            """
            source_result = await session.run(source_query)
            source_records = await source_result.data()
            
            print(f"\n   按来源统计:")
            for record in source_records:
                source = record['source'] or '未知'
                count = record['count']
                print(f"      {source}: {count} 个")
            
            # 总结
            print("\n" + "=" * 80)
            print("📋 验证总结")
            print("=" * 80)
            
            if all_valid:
                print("\n✅ 任务 2.3 验证通过！")
                print("   - 所有关键动作都已添加技术检查点")
                print("   - JSON格式正确")
                print("   - 技术检查点内容专业合理")
            else:
                print("\n❌ 任务 2.3 验证失败！")
                print("   请检查上述错误信息")
            
            return all_valid
    
    finally:
        await driver.close()


async def main():
    """主函数"""
    try:
        success = await verify_technique_checkpoints()
        return success
    except Exception as e:
        print(f"\n❌ 验证过程出错: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
