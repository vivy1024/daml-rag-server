#!/usr/bin/env python3
"""
查询Neo4j数据库中的动作关系
"""
import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.framework.clients.neo4j_client import Neo4jClient


async def query_relationships():
    """查询所有关系类型"""
    
    print("\n" + "="*80)
    print("查询Neo4j数据库中的所有关系类型")
    print("="*80)
    
    neo4j_client = Neo4jClient()
    await neo4j_client.connect()
    
    try:
        # 查询所有关系类型
        query = """
        CALL db.relationshipTypes() YIELD relationshipType
        RETURN relationshipType
        """
        
        result = await neo4j_client.execute_query(query)
        
        print(f"\n找到 {len(result)} 种关系类型:")
        for record in result:
            rel_type = record['relationshipType']
            
            # 统计每种关系的数量
            count_query = f"""
            MATCH ()-[r:{rel_type}]->()
            RETURN count(r) AS count
            """
            count_result = await neo4j_client.execute_query(count_query)
            count = count_result[0]['count'] if count_result else 0
            
            print(f"  {rel_type}: {count} 个")
        
        # 查询Exercise相关的关系
        print("\n" + "="*80)
        print("查询Exercise节点的关系示例:")
        print("="*80)
        
        query2 = """
        MATCH (e:Exercise)-[r]->(target)
        RETURN type(r) AS rel_type, labels(target) AS target_labels, count(*) AS count
        ORDER BY count DESC
        LIMIT 10
        """
        
        result2 = await neo4j_client.execute_query(query2)
        
        for record in result2:
            print(f"{record['rel_type']} -> {record['target_labels']}: {record['count']} 个")
        
    finally:
        print("\n" + "="*80)
        print("查询完成")
        print("="*80)


if __name__ == "__main__":
    asyncio.run(query_relationships())
