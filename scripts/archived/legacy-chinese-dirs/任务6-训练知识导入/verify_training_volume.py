#!/usr/bin/env python3
"""验证训练量标准导入结果"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import asyncio
from framework.clients.neo4j_client import Neo4jClient

async def main():
    client = Neo4jClient()
    await client.connect()
    
    # 获取有训练量数据的肌肉
    result = await client.execute_query("""
        MATCH (m:Muscle)
        WHERE m.mev IS NOT NULL AND m.mev <> 'N/A'
        RETURN m.name_zh as name, m.mev as mev, m.mav as mav, m.mrv as mrv
        ORDER BY name
    """)
    
    print(f"有训练量数据的肌肉节点 ({len(result)}个):")
    print("=" * 80)
    for r in result:
        print(f"{r['name']}: MEV={r['mev']}, MAV={r['mav']}, MRV={r['mrv']}")
    
    # 获取总数
    total_result = await client.execute_query("MATCH (m:Muscle) RETURN count(m) as total")
    total = total_result[0]['total']
    
    print(f"\n总计: {len(result)}/{total} 个肌肉节点有训练量数据")
    print(f"完成度: {len(result)/total*100:.1f}%")

if __name__ == "__main__":
    asyncio.run(main())
