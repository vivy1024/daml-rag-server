#!/usr/bin/env python3
"""测试力量标准导入"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import asyncio
from framework.clients.neo4j_client import Neo4jClient

async def main():
    client = Neo4jClient()
    await client.connect()
    
    # 测试查找Exercise
    exercises = ["杠铃深蹲", "杠铃卧推", "杠铃硬拉", "杠铃推举"]
    
    for ex_name in exercises:
        result = await client.execute_query("""
            MATCH (e:Exercise)
            WHERE e.name_zh = $name_zh
            RETURN e.id as id
            LIMIT 1
        """, {"name_zh": ex_name})
        
        if result:
            print(f"✅ 找到 {ex_name}: ID={result[0]['id']}")
        else:
            print(f"❌ 未找到 {ex_name}")

if __name__ == "__main__":
    asyncio.run(main())
