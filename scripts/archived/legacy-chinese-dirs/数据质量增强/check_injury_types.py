#!/usr/bin/env python3
"""
查看Neo4j中实际的InjuryType节点

作者：薛小川
日期：2025-12-15
"""

import asyncio
import os
from neo4j import AsyncGraphDatabase
from dotenv import load_dotenv

load_dotenv()


async def check_injury_types():
    """查看所有InjuryType节点"""
    
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://fitness_neo4j:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "build_body_2024")
    
    driver = AsyncGraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
    
    try:
        async with driver.session() as session:
            query = """
            MATCH (it:InjuryType)
            RETURN it.id as id,
                   it.name as name,
                   it.name_zh as name_zh,
                   it.severity_level as severity_level
            ORDER BY it.name
            """
            result = await session.run(query)
            records = await result.data()
            
            print("=" * 80)
            print(f"Neo4j中的InjuryType节点（共{len(records)}个）")
            print("=" * 80)
            print(f"{'序号':<6} {'中文名称':<20} {'英文名称':<30} {'严重程度':<12}")
            print("-" * 80)
            
            for i, record in enumerate(records, 1):
                name = record['name'] or 'N/A'
                name_zh = record['name_zh'] or 'N/A'
                severity = record['severity_level'] or 'N/A'
                print(f"{i:<6} {name:<20} {name_zh:<30} {severity:<12}")
            
            print("=" * 80)
            
            # 统计严重程度分布
            print("\n严重程度分布:")
            severity_count = {}
            for record in records:
                severity = record['severity_level'] or 'N/A'
                severity_count[severity] = severity_count.get(severity, 0) + 1
            
            for severity, count in sorted(severity_count.items()):
                print(f"  {severity}: {count} 个")
    
    finally:
        await driver.close()


if __name__ == "__main__":
    asyncio.run(check_injury_types())
