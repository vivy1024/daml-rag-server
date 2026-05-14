#!/usr/bin/env python3
"""
从三端数据库删除 primary_muscle_zh/en 字段
"""
import asyncio
from neo4j import AsyncGraphDatabase
from qdrant_client import QdrantClient

async def remove_from_neo4j():
    """从Neo4j删除字段"""
    driver = AsyncGraphDatabase.driver(
        "bolt://fitness_neo4j:7687",
        auth=("neo4j", "build_body_2024")
    )
    
    async with driver.session() as session:
        # 删除 primary_muscle_zh 和 primary_muscle_en 属性
        result = await session.run("""
            MATCH (e:Exercise)
            WHERE e.primary_muscle_zh IS NOT NULL OR e.primary_muscle_en IS NOT NULL
            REMOVE e.primary_muscle_zh, e.primary_muscle_en
            RETURN count(e) as count
        """)
        record = await result.single()
        count = record["count"] if record else 0
        print(f"✅ Neo4j: 已从 {count} 个Exercise节点删除 primary_muscle_zh/en")
    
    await driver.close()

def remove_from_qdrant():
    """从Qdrant删除字段"""
    client = QdrantClient(host="fitness_qdrant", port=6333)
    
    # Qdrant集合名
    collection_name = "fitness_exercises_v2"
    
    # 使用 delete_payload 删除指定字段
    # 获取所有点的ID
    scroll_result = client.scroll(
        collection_name=collection_name,
        limit=100,
        with_payload=False,
        with_vectors=False
    )
    
    all_ids = []
    while scroll_result[0]:
        all_ids.extend([p.id for p in scroll_result[0]])
        if scroll_result[1]:
            scroll_result = client.scroll(
                collection_name=collection_name,
                limit=100,
                offset=scroll_result[1],
                with_payload=False,
                with_vectors=False
            )
        else:
            break
    
    # 批量删除字段
    if all_ids:
        client.delete_payload(
            collection_name=collection_name,
            keys=["primary_muscle_zh", "primary_muscle_en"],
            points=all_ids
        )
    
    print(f"✅ Qdrant: 已从 {len(all_ids)} 个点删除 primary_muscle_zh/en 字段")

async def main():
    print("🔄 开始从数据库删除 primary_muscle_zh/en 字段...")
    
    # Neo4j
    await remove_from_neo4j()
    
    # Qdrant
    remove_from_qdrant()
    
    print("\n✅ 完成！统一使用 muscles_primary_zh/en 数组字段")

if __name__ == "__main__":
    asyncio.run(main())
