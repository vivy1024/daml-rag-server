#!/usr/bin/env python3
"""
验证康复阶段节点和关系创建结果

验证内容：
1. RehabilitationPhase节点数量和属性
2. REHAB_PROGRESSION关系数量和属性
3. 数据完整性和正确性

作者：薛小川
日期：2025-12-15
"""

import asyncio
import json
import sys
import os
from neo4j import AsyncGraphDatabase

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))


async def verify_rehabilitation_phases(driver):
    """验证康复阶段节点"""
    print("\n" + "=" * 80)
    print("📋 验证康复阶段节点")
    print("=" * 80)
    
    async with driver.session() as session:
        # 1. 统计节点数量
        query_count = """
        MATCH (rp:RehabilitationPhase)
        RETURN count(rp) as total_count
        """
        result = await session.run(query_count)
        record = await result.single()
        total_count = record["total_count"]
        
        print(f"\n✅ 总节点数: {total_count}")
        
        # 2. 获取所有节点详情
        query_details = """
        MATCH (rp:RehabilitationPhase)
        RETURN rp.phase_id as phase_id,
               rp.name_zh as name_zh,
               rp.name_en as name_en,
               rp.duration_days as duration_days,
               rp.goals as goals,
               rp.allowed_activities as allowed_activities,
               rp.contraindicated_activities as contraindicated_activities,
               rp.description as description
        ORDER BY 
            CASE rp.phase_id
                WHEN 'acute' THEN 1
                WHEN 'subacute' THEN 2
                WHEN 'recovery' THEN 3
            END
        """
        result = await session.run(query_details)
        records = await result.data()
        
        print("\n📊 节点详情:")
        for i, record in enumerate(records, 1):
            print(f"\n{i}. {record['name_zh']} ({record['phase_id']})")
            print(f"   英文名: {record['name_en']}")
            print(f"   持续时间: {record['duration_days']} 天")
            print(f"   目标: {json.loads(record['goals'])}")
            print(f"   允许活动: {json.loads(record['allowed_activities'])}")
            print(f"   禁忌活动: {json.loads(record['contraindicated_activities'])}")
            print(f"   描述: {record['description']}")
        
        # 3. 验证必需阶段
        required_phases = {'acute', 'subacute', 'recovery'}
        existing_phases = {r['phase_id'] for r in records}
        missing_phases = required_phases - existing_phases
        
        if missing_phases:
            print(f"\n❌ 缺少阶段: {missing_phases}")
            return False
        else:
            print(f"\n✅ 所有必需阶段都已创建")
            return True


async def verify_rehab_progressions(driver):
    """验证康复渐进关系"""
    print("\n" + "=" * 80)
    print("📋 验证REHAB_PROGRESSION关系")
    print("=" * 80)
    
    async with driver.session() as session:
        # 1. 统计关系数量
        query_count = """
        MATCH ()-[r:REHAB_PROGRESSION]->()
        RETURN count(r) as total_count
        """
        result = await session.run(query_count)
        record = await result.single()
        total_count = record["total_count"]
        
        print(f"\n✅ 总关系数: {total_count}")
        
        # 2. 获取所有关系详情
        query_details = """
        MATCH (e1:Exercise)-[r:REHAB_PROGRESSION]->(e2:Exercise)
        RETURN e1.name_zh as from_exercise,
               e1.exercise_id as from_id,
               e2.name_zh as to_exercise,
               e2.exercise_id as to_id,
               r.progression_order as order,
               r.criteria as criteria,
               r.estimated_weeks as weeks,
               r.phase as phase,
               r.notes as notes
        ORDER BY r.progression_order, e1.name_zh
        """
        result = await session.run(query_details)
        records = await result.data()
        
        print("\n📊 关系详情:")
        for i, record in enumerate(records, 1):
            print(f"\n{i}. {record['from_exercise']} → {record['to_exercise']}")
            print(f"   顺序: {record['order']}")
            print(f"   阶段: {record['phase']}")
            print(f"   预计周数: {record['weeks']} 周")
            print(f"   进阶标准: {record['criteria']}")
            print(f"   备注: {record['notes']}")
        
        # 3. 验证属性完整性
        incomplete = [r for r in records if not all([
            r.get('order'),
            r.get('criteria'),
            r.get('weeks'),
            r.get('phase')
        ])]
        
        if incomplete:
            print(f"\n❌ 发现 {len(incomplete)} 个属性不完整的关系")
            return False
        else:
            print(f"\n✅ 所有关系属性完整")
        
        # 4. 检查循环依赖
        query_cycle = """
        MATCH (e:Exercise)-[r:REHAB_PROGRESSION]->(e)
        RETURN count(r) as self_loop_count
        """
        result = await session.run(query_cycle)
        record = await result.single()
        self_loop_count = record["self_loop_count"]
        
        if self_loop_count > 0:
            print(f"\n❌ 发现 {self_loop_count} 个自循环")
            return False
        else:
            print(f"\n✅ 无循环依赖")
            return True


async def verify_integration(driver):
    """验证集成情况"""
    print("\n" + "=" * 80)
    print("📋 验证数据集成")
    print("=" * 80)
    
    async with driver.session() as session:
        # 1. 检查康复路径的完整性
        query_paths = """
        MATCH path = (e1:Exercise)-[:REHAB_PROGRESSION*]->(e2:Exercise)
        WHERE NOT (e1)<-[:REHAB_PROGRESSION]-()
        RETURN e1.name_zh as start_exercise,
               [node in nodes(path) | node.name_zh] as path_exercises,
               length(path) as path_length
        ORDER BY path_length DESC
        LIMIT 5
        """
        result = await session.run(query_paths)
        records = await result.data()
        
        print("\n📊 康复路径示例:")
        for i, record in enumerate(records, 1):
            path_str = " → ".join(record['path_exercises'])
            print(f"\n{i}. {path_str}")
            print(f"   路径长度: {record['path_length']} 步")
        
        # 2. 按阶段统计关系
        query_by_phase = """
        MATCH ()-[r:REHAB_PROGRESSION]->()
        RETURN r.phase as phase,
               count(r) as count
        ORDER BY 
            CASE r.phase
                WHEN 'acute' THEN 1
                WHEN 'subacute' THEN 2
                WHEN 'recovery' THEN 3
            END
        """
        result = await session.run(query_by_phase)
        records = await result.data()
        
        print("\n📊 按阶段统计:")
        for record in records:
            print(f"   {record['phase']}: {record['count']} 个关系")
        
        return True


async def main():
    """主函数"""
    from dotenv import load_dotenv
    
    # 加载环境变量
    load_dotenv()
    
    # Neo4j配置
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "")
    
    print("=" * 80)
    print("🔍 康复阶段节点和关系验证工具")
    print("=" * 80)
    print(f"\nNeo4j URI: {neo4j_uri}")
    print(f"Neo4j User: {neo4j_user}")
    
    # 连接Neo4j
    driver = AsyncGraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
    
    try:
        # 验证康复阶段节点
        phases_valid = await verify_rehabilitation_phases(driver)
        
        # 验证康复渐进关系
        progressions_valid = await verify_rehab_progressions(driver)
        
        # 验证集成情况
        integration_valid = await verify_integration(driver)
        
        # 总结
        print("\n" + "=" * 80)
        print("📊 验证总结")
        print("=" * 80)
        print(f"康复阶段节点: {'✅ 通过' if phases_valid else '❌ 失败'}")
        print(f"康复渐进关系: {'✅ 通过' if progressions_valid else '❌ 失败'}")
        print(f"数据集成: {'✅ 通过' if integration_valid else '❌ 失败'}")
        
        if phases_valid and progressions_valid and integration_valid:
            print("\n🎉 所有验证通过！")
            print("=" * 80)
            return 0
        else:
            print("\n⚠️ 部分验证失败，请检查")
            print("=" * 80)
            return 1
        
    except Exception as e:
        print(f"\n❌ 验证失败: {e}")
        import traceback
        traceback.print_exc()
        return 1
        
    finally:
        await driver.close()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
