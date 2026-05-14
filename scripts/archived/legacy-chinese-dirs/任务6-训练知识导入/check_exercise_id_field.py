#!/usr/bin/env python3
"""检查Exercise节点的ID字段"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import asyncio
from framework.clients.neo4j_client import Neo4jClient

async def main():
    client = Neo4jClient()
    await client.connect()
    
    # 查找杠铃深蹲
    result = await client.execute_query("""
        MATCH (e:Exercise {name_zh: '杠铃深蹲'})
        RETURN e.exercise_id as exercise_id, e.id as id, keys(e) as all_keys
        LIMIT 1
    """)
    
    if result:
        print("杠铃深蹲节点的字段:")
        print("=" * 60)
        print(f"exercise_id: {result[0].get('exercise_id')}")
        print(f"id: {result[0].get('id')}")
        print(f"\n所有字段: {result[0].get('all_keys')}")
    else:
        print("未找到杠铃深蹲节点")

if __name__ == "__main__":
    asyncio.run(main())
