"""
检查数据库中所有关系类型
"""

import asyncio
import sys
import os

src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, src_path)

from framework.clients.neo4j_client import Neo4jClient, Neo4jClientConfig


async def check_relationships():
    neo4j_config = Neo4jClientConfig.from_env()
    neo4j_client = Neo4jClient(config=neo4j_config)
    await neo4j_client.connect()
    
    # 查询所有关系类型及数量
    query = """
    CALL db.relationshipTypes() YIELD relationshipType
    CALL apoc.cypher.run('MATCH ()-[r:' + relationshipType + ']->() RETURN count(r) as count', {})
    YIELD value
    RETURN relationshipType, value.count as count
    ORDER BY value.count DESC
    """
    
    try:
        results = await neo4j_client.execute_query(query, {})
        print("=" * 80)
        print("数据库中所有关系类型及数量:")
        print("=" * 80)
        for r in results:
            print(f"  {r['relationshipType']}: {r['count']}个")
    except Exception as e:
        print(f"APOC查询失败，使用备用方案: {e}")
        
        # 备用方案：手动查询已知的关系类型
        known_types = [
            "TARGETS_PRIMARY", "TARGETS_SECONDARY", "REQUIRES",
            "CONTAINS_NUTRIENT", "HAS_PHASE", "SUITABLE_FOR_LEVEL",
            "RECOMMENDED_FOR_GOAL", "PROGRESSES_TO", "CONTRAINDICATED_FOR"
        ]
        
        print("=" * 80)
        print("已知关系类型统计:")
        print("=" * 80)
        
        for rel_type in known_types:
            count_query = f"MATCH ()-[r:{rel_type}]->() RETURN count(r) as count"
            count_result = await neo4j_client.execute_query(count_query, {})
            count = count_result[0]['count'] if count_result else 0
            print(f"  {rel_type}: {count}个")
    
    await neo4j_client.disconnect()


if __name__ == "__main__":
    asyncio.run(check_relationships())
