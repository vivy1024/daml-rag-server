#!/usr/bin/env python3
"""查找杠铃相关的动作"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import asyncio
from framework.clients.neo4j_client import Neo4jClient

async def main():
    client = Neo4jClient()
    await client.connect()
    
    # 查找杠铃相关的主要动作
    result = await client.execute_query("""
        MATCH (e:Exercise)
        WHERE e.name_zh CONTAINS '杠铃' 
        AND (e.name_zh CONTAINS '深蹲' OR e.name_zh CONTAINS '卧推' 
             OR e.name_zh CONTAINS '硬拉' OR e.name_zh CONTAINS '推举')
        RETURN e.name_zh as name
        ORDER BY name
    """)
    
    print("杠铃相关的主要动作:")
    print("=" * 60)
    for r in result:
        print(f"  - {r['name']}")
    
    print(f"\n总计: {len(result)} 个动作")

if __name__ == "__main__":
    asyncio.run(main())
