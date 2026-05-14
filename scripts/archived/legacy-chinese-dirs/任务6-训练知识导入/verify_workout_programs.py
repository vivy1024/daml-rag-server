#!/usr/bin/env python3
"""验证训练计划模板导入结果"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import asyncio
from framework.clients.neo4j_client import Neo4jClient

async def main():
    client = Neo4jClient()
    await client.connect()
    
    # 统计WorkoutProgram节点总数
    result = await client.execute_query("""
        MATCH (p:WorkoutProgram)
        RETURN count(p) as total
    """)
    total = result[0]['total']
    print(f"WorkoutProgram节点总数: {total}")
    
    # 检查关系
    result2 = await client.execute_query("""
        MATCH (p:WorkoutProgram)-[r]->()
        RETURN type(r) as rel_type, count(r) as count
    """)
    
    print(f"\nWorkoutProgram的关系:")
    print("=" * 60)
    for r in result2:
        print(f"{r['rel_type']}: {r['count']}个")
    
    # 查看示例数据
    result3 = await client.execute_query("""
        MATCH (p:WorkoutProgram)
        RETURN p.name_zh as name, p.goal as goal, p.training_days_per_week as days
        LIMIT 5
    """)
    
    print(f"\n训练计划模板示例:")
    print("=" * 60)
    for r in result3:
        print(f"名称: {r['name']}, 目标: {r['goal']}, 训练天数: {r['days']}")

if __name__ == "__main__":
    asyncio.run(main())
