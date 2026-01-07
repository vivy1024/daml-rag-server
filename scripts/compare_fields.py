#!/usr/bin/env python3
"""
对比Neo4j、Qdrant、MySQL的Exercise字段差异
"""

import asyncio
import os
import sys
sys.path.insert(0, '/app')
sys.path.insert(0, '/app/src')

from qdrant_client import QdrantClient
from neo4j import AsyncGraphDatabase
import aiomysql


async def get_neo4j_fields():
    """获取Neo4j Exercise节点字段"""
    uri = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "your_password")
    
    driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
    
    async with driver.session() as session:
        result = await session.run("""
            MATCH (e:Exercise)
            WITH e LIMIT 1
            RETURN keys(e) as fields
        """)
        record = await result.single()
        fields = set(record["fields"]) if record else set()
    
    await driver.close()
    return fields


def get_qdrant_fields():
    """获取Qdrant payload字段"""
    client = QdrantClient(host="qdrant", port=6333)
    results, _ = client.scroll(
        collection_name="fitness_exercises_v2",
        limit=1,
        with_payload=True
    )
    
    if results:
        return set(results[0].payload.keys())
    return set()


async def get_mysql_fields():
    """获取MySQL exercises表字段"""
    conn = await aiomysql.connect(
        host=os.getenv("MYSQL_HOST", "fitness_mysql"),
        port=int(os.getenv("MYSQL_PORT", 3306)),
        user=os.getenv("MYSQL_USER", "fitness_user"),
        password=os.getenv("MYSQL_PASSWORD", "fitness_pass"),
        db=os.getenv("MYSQL_DATABASE", "fitness_app")
    )
    
    async with conn.cursor() as cursor:
        await cursor.execute("DESCRIBE exercises")
        columns = await cursor.fetchall()
        fields = set(col[0] for col in columns)
    
    conn.close()
    return fields


async def main():
    print("="*70)
    print("Neo4j / Qdrant / MySQL Exercise字段对比")
    print("="*70)
    
    # 获取各数据源字段
    neo4j_fields = await get_neo4j_fields()
    qdrant_fields = get_qdrant_fields()
    mysql_fields = await get_mysql_fields()
    
    print(f"\n字段数量:")
    print(f"  Neo4j:  {len(neo4j_fields)}个")
    print(f"  Qdrant: {len(qdrant_fields)}个")
    print(f"  MySQL:  {len(mysql_fields)}个")
    
    # 三者共有
    common_all = neo4j_fields & qdrant_fields & mysql_fields
    print(f"\n三者共有字段 ({len(common_all)}个):")
    for f in sorted(common_all):
        print(f"  {f}")
    
    # Neo4j独有
    neo4j_only = neo4j_fields - qdrant_fields - mysql_fields
    print(f"\nNeo4j独有 ({len(neo4j_only)}个):")
    for f in sorted(neo4j_only):
        print(f"  {f}")
    
    # Qdrant独有
    qdrant_only = qdrant_fields - neo4j_fields - mysql_fields
    print(f"\nQdrant独有 ({len(qdrant_only)}个):")
    for f in sorted(qdrant_only):
        print(f"  {f}")
    
    # MySQL独有
    mysql_only = mysql_fields - neo4j_fields - qdrant_fields
    print(f"\nMySQL独有 ({len(mysql_only)}个):")
    for f in sorted(mysql_only):
        print(f"  {f}")
    
    # Neo4j + Qdrant共有（MySQL没有）
    neo4j_qdrant = (neo4j_fields & qdrant_fields) - mysql_fields
    print(f"\nNeo4j+Qdrant共有，MySQL没有 ({len(neo4j_qdrant)}个):")
    for f in sorted(neo4j_qdrant):
        print(f"  {f}")
    
    # Neo4j + MySQL共有（Qdrant没有）
    neo4j_mysql = (neo4j_fields & mysql_fields) - qdrant_fields
    print(f"\nNeo4j+MySQL共有，Qdrant没有 ({len(neo4j_mysql)}个):")
    for f in sorted(neo4j_mysql):
        print(f"  {f}")
    
    # Qdrant + MySQL共有（Neo4j没有）
    qdrant_mysql = (qdrant_fields & mysql_fields) - neo4j_fields
    print(f"\nQdrant+MySQL共有，Neo4j没有 ({len(qdrant_mysql)}个):")
    for f in sorted(qdrant_mysql):
        print(f"  {f}")


if __name__ == "__main__":
    asyncio.run(main())
