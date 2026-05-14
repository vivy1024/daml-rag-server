#!/usr/bin/env python3
"""
同步所有肌肉字段到Neo4j、Qdrant、MySQL
以文件系统为准
"""
import asyncio
import json
from collections import defaultdict

print("="*70)
print("同步所有肌肉字段")
print("="*70)

# 读取数据
with open('/app/logs/all_muscle_fields.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f"读取到 {len(data)} 条记录")

muscle_fields = [
    'muscles_tree', 'muscles_primary_tree', 'muscles_secondary_tree',
    'muscles_primary_zh', 'muscles_primary_en',
    'muscles_secondary_zh', 'muscles_secondary_en',
    'all_muscles_zh', 'all_muscles_en',
    'primary_muscle_zh', 'primary_muscle_en'
]

# 1. 同步到Qdrant
print("\n【1】同步到Qdrant")
print("-"*50)

from qdrant_client import QdrantClient
client = QdrantClient(host='qdrant', port=6333)

updated = 0
for eid_str, fields in data.items():
    eid = int(eid_str)
    
    # 查找point
    results, _ = client.scroll(
        collection_name="fitness_exercises_v2",
        scroll_filter={"must": [{"key": "id", "match": {"value": eid}}]},
        limit=1,
        with_payload=False
    )
    
    if results:
        point_id = results[0].id
        
        # 准备payload（只更新简单字段，不更新tree）
        payload = {}
        for field in ['muscles_primary_zh', 'muscles_primary_en', 
                      'muscles_secondary_zh', 'muscles_secondary_en',
                      'all_muscles_zh', 'all_muscles_en',
                      'primary_muscle_zh', 'primary_muscle_en']:
            if field in fields:
                payload[field] = fields[field] if fields[field] else []
        
        if payload:
            client.set_payload(
                collection_name="fitness_exercises_v2",
                payload=payload,
                points=[point_id]
            )
            updated += 1
            
            if updated % 300 == 0:
                print(f"  已更新 {updated} 个点...")

print(f"完成！共更新 {updated} 个点")

# 2. 同步到MySQL
print("\n【2】同步到MySQL")
print("-"*50)

async def sync_mysql():
    import aiomysql
    
    conn = await aiomysql.connect(
        host='fitness_mysql', port=3306,
        user='fitness_user', password='fitness_pass',
        db='fitness_app'
    )
    
    updated = 0
    async with conn.cursor() as cursor:
        for eid_str, fields in data.items():
            eid = int(eid_str)
            
            # 更新字段
            updates = []
            values = []
            
            for field in ['muscles_tree', 'muscles_primary_tree',
                          'muscles_primary_zh', 'muscles_primary_en',
                          'muscles_secondary_zh', 'muscles_secondary_en',
                          'all_muscles_zh', 'all_muscles_en']:
                if field in fields:
                    updates.append(f"{field} = %s")
                    val = fields[field]
                    values.append(json.dumps(val, ensure_ascii=False) if val else None)
            
            # primary_muscle_zh/en 是字符串
            if 'primary_muscle_zh' in fields:
                updates.append("primary_muscle_zh = %s")
                values.append(fields['primary_muscle_zh'])
            if 'primary_muscle_en' in fields:
                updates.append("primary_muscle_en = %s")
                values.append(fields['primary_muscle_en'])
            
            if updates:
                values.append(eid)
                sql = f"UPDATE exercises SET {', '.join(updates)} WHERE id = %s"
                await cursor.execute(sql, values)
                updated += 1
        
        await conn.commit()
    
    conn.close()
    print(f"完成！共更新 {updated} 条记录")

asyncio.run(sync_mysql())

# 3. 同步到Neo4j（只更新缺失的字段）
print("\n【3】同步到Neo4j")
print("-"*50)

from neo4j import GraphDatabase
driver = GraphDatabase.driver('bolt://neo4j:7687', auth=('neo4j', 'build_body_2024'))

updated = 0
with driver.session() as session:
    for eid_str, fields in data.items():
        eid = int(eid_str)
        
        # 准备更新
        props = {}
        for field in ['muscles_primary_zh', 'muscles_primary_en',
                      'muscles_secondary_zh', 'muscles_secondary_en',
                      'all_muscles_zh', 'all_muscles_en']:
            if field in fields and fields[field]:
                props[field] = fields[field]
        
        if 'primary_muscle_zh' in fields and fields['primary_muscle_zh']:
            props['primary_muscle_zh'] = fields['primary_muscle_zh']
        if 'primary_muscle_en' in fields and fields['primary_muscle_en']:
            props['primary_muscle_en'] = fields['primary_muscle_en']
        
        if props:
            # 构建SET语句
            set_clauses = [f"e.{k} = ${k}" for k in props.keys()]
            query = f"MATCH (e:Exercise {{id: $id}}) SET {', '.join(set_clauses)}"
            props['id'] = eid
            session.run(query, props)
            updated += 1
            
            if updated % 300 == 0:
                print(f"  已更新 {updated} 个节点...")

driver.close()
print(f"完成！共更新 {updated} 个节点")

print("\n" + "="*70)
print("同步完成！")
print("="*70)
