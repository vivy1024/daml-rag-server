#!/usr/bin/env python3
"""检查Neo4j中的肌肉名称"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import asyncio
from framework.clients.neo4j_client import Neo4jClient

async def main():
    client = Neo4jClient()
    await client.connect()
    
    # 获取所有肌肉名称
    result = await client.execute_query("""
        MATCH (m:Muscle)
        RETURN m.name_zh as name, m.mev as mev, m.mav as mav, m.mrv as mrv
        ORDER BY name
    """)
    
    print("Neo4j中的肌肉节点：")
    print("=" * 80)
    for r in result:
        status = "✅" if r['mev'] and r['mev'] != 'N/A' else "❌"
        print(f"{status} {r['name']}: MEV={r['mev']}, MAV={r['mav']}, MRV={r['mrv']}")
    
    print(f"\n总计: {len(result)} 个肌肉节点")
    
    await client.close()

if __name__ == "__main__":
    asyncio.run(main())
