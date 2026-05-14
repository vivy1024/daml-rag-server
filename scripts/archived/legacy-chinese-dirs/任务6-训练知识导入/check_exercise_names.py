#!/usr/bin/env python3
"""检查Neo4j中的动作名称"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import asyncio
from framework.clients.neo4j_client import Neo4jClient

async def main():
    client = Neo4jClient()
    await client.connect()
    
    # 搜索包含关键词的动作
    keywords = ["深蹲", "卧推", "硬拉", "推举"]
    
    for keyword in keywords:
        result = await client.execute_query(f"""
            MATCH (e:Exercise)
            WHERE e.name_zh CONTAINS '{keyword}'
            RETURN e.name_zh as name
            ORDER BY name
            LIMIT 10
        """)
        
        print(f"\n包含'{keyword}'的动作:")
        print("=" * 60)
        if result:
            for r in result:
                print(f"  - {r['name']}")
        else:
            print(f"  未找到包含'{keyword}'的动作")

if __name__ == "__main__":
    asyncio.run(main())
