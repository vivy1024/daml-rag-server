#!/usr/bin/env python3
"""检查muscles_secondary字段在各数据源的情况"""

import asyncio
import os
import sys
sys.path.insert(0, '/app')

from neo4j import AsyncGraphDatabase
from qdrant_client import QdrantClient


async def main():
    print("="*60)
    print("检查muscles_secondary字段")
    print("="*60)
    
    # Neo4j
    uri = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "your_password")
    driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
    
    async with driver.session() as session:
        result = await session.run(
            "MATCH (e:Exercise) WHERE e.muscles_secondary_zh IS NOT NULL RETURN count(e) as c"
        )
        r = await result.single()
        print(f"Neo4j muscles_secondary_zh: {r['c']}个")
        
        result = await session.run(
            "MATCH (e:Exercise) WHERE e.muscles_secondary_en IS NOT NULL RETURN count(e) as c"
        )
        r = await result.single()
        print(f"Neo4j muscles_secondary_en: {r['c']}个")
        
        result = await session.run("MATCH (e:Exercise) RETURN count(e) as c")
        r = await result.single()
        print(f"Neo4j总Exercise: {r['c']}个")
    
    await driver.close()
    
    # Qdrant
    client = QdrantClient(host="qdrant", port=6333)
    results, _ = client.scroll(
        collection_name="fitness_exercises_v2",
        limit=100,
        with_payload=True
    )
    
    has_secondary_zh = sum(1 for r in results if r.payload.get("muscles_secondary_zh"))
    print(f"\nQdrant muscles_secondary_zh (前100个): {has_secondary_zh}个有值")


if __name__ == "__main__":
    asyncio.run(main())
