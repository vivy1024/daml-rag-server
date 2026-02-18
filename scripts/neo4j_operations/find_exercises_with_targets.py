"""
查找有TARGETS关系的动作
"""

import asyncio
import sys
import os

src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, src_path)

from framework.clients.neo4j_client import Neo4jClient, Neo4jClientConfig


async def find_exercises():
    neo4j_config = Neo4jClientConfig.from_env()
    neo4j_client = Neo4jClient(config=neo4j_config)
    await neo4j_client.connect()
    
    # 查询有TARGETS_PRIMARY关系的动作示例
    query1 = """
    MATCH (e:Exercise)-[:TARGETS_PRIMARY]->(m:Muscle)
    RETURN e.id as id, e.name_zh as exercise, m.name_zh as muscle
    LIMIT 10
    """
    
    results1 = await neo4j_client.execute_query(query1, {})
    print("=" * 80)
    print("有TARGETS_PRIMARY关系的动作示例（前10个）:")
    print("=" * 80)
    for r in results1:
        print(f"  ID {r['id']}: {r['exercise']} -> {r['muscle']}")
    
    # 统计有关系的动作数量
    query2 = """
    MATCH (e:Exercise)-[:TARGETS_PRIMARY]->(m:Muscle)
    RETURN count(DISTINCT e) as exercise_count
    """
    
    results2 = await neo4j_client.execute_query(query2, {})
    print(f"\n有TARGETS_PRIMARY关系的动作总数: {results2[0]['exercise_count']}")
    
    # 查询ID在1-10范围内的动作及其关系
    query3 = """
    MATCH (e:Exercise)
    WHERE e.id >= 1 AND e.id <= 10
    OPTIONAL MATCH (e)-[:TARGETS_PRIMARY]->(m:Muscle)
    RETURN e.id as id, e.name_zh as exercise, collect(m.name_zh) as muscles
    ORDER BY e.id
    """
    
    results3 = await neo4j_client.execute_query(query3, {})
    print("\n" + "=" * 80)
    print("ID 1-10的动作及其TARGETS关系:")
    print("=" * 80)
    for r in results3:
        muscles_str = ", ".join(r['muscles']) if r['muscles'] else "无关系"
        print(f"  ID {r['id']}: {r['exercise']} -> {muscles_str}")
    
    await neo4j_client.disconnect()


if __name__ == "__main__":
    asyncio.run(find_exercises())
