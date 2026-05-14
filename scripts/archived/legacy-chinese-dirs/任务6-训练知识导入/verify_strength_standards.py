#!/usr/bin/env python3
"""验证力量标准导入结果"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import asyncio
from framework.clients.neo4j_client import Neo4jClient

async def main():
    client = Neo4jClient()
    await client.connect()
    
    # 统计StrengthStandard节点总数
    result = await client.execute_query("""
        MATCH (s:StrengthStandard)
        RETURN count(s) as total
    """)
    total = result[0]['total']
    print(f"StrengthStandard节点总数: {total}")
    
    # 统计有力量标准的Exercise数量
    result2 = await client.execute_query("""
        MATCH (e:Exercise)-[:HAS_STRENGTH_STANDARD]->(s:StrengthStandard)
        RETURN count(DISTINCT e) as exercises
    """)
    exercises = result2[0]['exercises']
    print(f"有力量标准的Exercise数量: {exercises}")
    
    # 查看示例数据
    result3 = await client.execute_query("""
        MATCH (e:Exercise {name_zh: '杠铃深蹲'})-[:HAS_STRENGTH_STANDARD]->(s:StrengthStandard)
        RETURN s.gender as gender, s.bodyweight_kg as bodyweight, s.level_zh as level, s.weight_kg as weight
        ORDER BY s.gender, s.bodyweight_kg, s.level
        LIMIT 5
    """)
    
    print(f"\n杠铃深蹲的力量标准示例:")
    print("=" * 80)
    for r in result3:
        print(f"性别: {r['gender']}, 体重: {r['bodyweight']}kg, 水平: {r['level']}, 标准: {r['weight']}kg")

if __name__ == "__main__":
    asyncio.run(main())
