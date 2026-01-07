#!/usr/bin/env python3
"""
统一Neo4j、Qdrant字段名与文件系统一致
"""

import asyncio
import os
import sys
sys.path.insert(0, '/app')
sys.path.insert(0, '/app/src')

from qdrant_client import QdrantClient
from neo4j import AsyncGraphDatabase


async def fix_qdrant():
    """修复Qdrant字段名"""
    print("\n" + "="*60)
    print("修复Qdrant字段名")
    print("="*60)
    
    client = QdrantClient(host="qdrant", port=6333)
    
    # 获取集合信息
    collection_info = client.get_collection("fitness_exercises_v2")
    total_points = collection_info.points_count
    print(f"总向量数: {total_points}")
    
    # 分批处理
    batch_size = 100
    offset = None
    updated_count = 0
    
    while True:
        results, next_offset = client.scroll(
            collection_name="fitness_exercises_v2",
            limit=batch_size,
            offset=offset,
            with_payload=True,
            with_vectors=False
        )
        
        if not results:
            break
        
        for point in results:
            payload = point.payload
            updates = {}
            deletes = []
            
            # 1. exercise_id -> id
            if "exercise_id" in payload and "id" not in payload:
                updates["id"] = payload["exercise_id"]
                deletes.append("exercise_id")
            
            # 2. secondary_muscles_zh -> muscles_secondary_zh (已经有了，删除旧的)
            if "secondary_muscles_zh" in payload:
                if "muscles_secondary_zh" not in payload:
                    updates["muscles_secondary_zh"] = payload["secondary_muscles_zh"]
                deletes.append("secondary_muscles_zh")
            
            # 3. 删除Qdrant独有的非标准字段（文件系统没有的）
            # kinetic_chain_zh, safety_level_zh 文件系统没有，删除
            if "kinetic_chain_zh" in payload:
                deletes.append("kinetic_chain_zh")
            if "safety_level_zh" in payload:
                deletes.append("safety_level_zh")
            
            # 执行更新
            if updates:
                client.set_payload(
                    collection_name="fitness_exercises_v2",
                    payload=updates,
                    points=[point.id]
                )
            
            # 执行删除
            if deletes:
                client.delete_payload(
                    collection_name="fitness_exercises_v2",
                    keys=deletes,
                    points=[point.id]
                )
                updated_count += 1
        
        if updated_count > 0 and updated_count % 100 == 0:
            print(f"  已处理 {updated_count} 个点")
        
        offset = next_offset
        if offset is None:
            break
    
    print(f"完成！共更新 {updated_count} 个点")
    
    # 验证
    print("\n验证结果:")
    results, _ = client.scroll(
        collection_name="fitness_exercises_v2",
        limit=1,
        with_payload=True
    )
    if results:
        payload = results[0].payload
        check_fields = ["id", "exercise_id", "muscles_secondary_zh", "secondary_muscles_zh", 
                       "kinetic_chain_zh", "safety_level_zh"]
        for f in check_fields:
            if f in payload:
                print(f"  {f}: 存在")
            else:
                print(f"  {f}: 已删除/不存在")


async def fix_neo4j():
    """修复Neo4j字段"""
    print("\n" + "="*60)
    print("检查Neo4j字段")
    print("="*60)
    
    uri = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "your_password")
    
    driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
    
    async with driver.session() as session:
        # 检查是否有description字段
        result = await session.run("""
            MATCH (e:Exercise)
            WHERE e.description_zh IS NOT NULL
            RETURN count(e) as count
        """)
        record = await result.single()
        desc_count = record["count"] if record else 0
        print(f"有description_zh的Exercise: {desc_count}个")
        
        # 检查muscles_secondary_en
        result = await session.run("""
            MATCH (e:Exercise)
            WHERE e.muscles_secondary_en IS NOT NULL
            RETURN count(e) as count
        """)
        record = await result.single()
        sec_en_count = record["count"] if record else 0
        print(f"有muscles_secondary_en的Exercise: {sec_en_count}个")
        
        # Neo4j字段列表
        result = await session.run("""
            MATCH (e:Exercise)
            WITH e LIMIT 1
            RETURN keys(e) as fields
        """)
        record = await result.single()
        if record:
            fields = sorted(record["fields"])
            print(f"\nNeo4j Exercise字段 ({len(fields)}个):")
            for f in fields:
                print(f"  {f}")
    
    await driver.close()


async def main():
    print("="*60)
    print("统一字段名（以文件系统为准）")
    print("="*60)
    
    # 修复Qdrant
    await fix_qdrant()
    
    # 检查Neo4j
    await fix_neo4j()
    
    print("\n" + "="*60)
    print("完成！")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
