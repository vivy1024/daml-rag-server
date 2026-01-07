"""
检查equipment_zh字段的格式
"""

import asyncio
import sys
import os

src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, src_path)

from framework.clients.neo4j_client import Neo4jClient, Neo4jClientConfig


async def check_equipment():
    neo4j_config = Neo4jClientConfig.from_env()
    neo4j_client = Neo4jClient(config=neo4j_config)
    await neo4j_client.connect()
    
    # 查询几个动作的equipment_zh字段
    query = """
    MATCH (e:Exercise)
    WHERE e.id IN [1, 2, 3, 4, 5, 8]
    RETURN e.id as id, e.name_zh as name, e.equipment_zh as equipment, 
           toString(e.equipment_zh) as equipment_str
    """
    
    results = await neo4j_client.execute_query(query, {})
    
    print("=" * 80)
    print("Equipment字段格式检查:")
    print("=" * 80)
    for r in results:
        print(f"\nID {r['id']}: {r['name']}")
        print(f"  equipment_zh: {r['equipment']}")
        print(f"  类型: {type(r['equipment'])}")
        print(f"  字符串形式: {r['equipment_str']}")
    
    await neo4j_client.disconnect()


if __name__ == "__main__":
    asyncio.run(check_equipment())
