#!/usr/bin/env python3
"""
全面检查肌肉字段一致性
检查：增强数据文件、Neo4j、Qdrant、MySQL
"""
import asyncio
import json
from collections import defaultdict

print("="*70)
print("肌肉字段全面一致性检查")
print("="*70)

muscle_fields = [
    'muscles_tree', 'muscles_primary_tree', 'muscles_secondary_tree',
    'muscles_primary_zh', 'muscles_primary_en',
    'muscles_secondary_zh', 'muscles_secondary_en',
    'all_muscles_zh', 'all_muscles_en',
    'primary_muscle_zh', 'primary_muscle_en'
]

# 1. 增强数据文件
print("\n【1】增强数据文件 (enhanced_perfect_exercises_dataset.json)")
print("-"*50)

try:
    with open('/app/data/enhanced_perfect_exercises_dataset.json', 'r', encoding='utf-8') as f:
        enhanced_data = json.load(f)
    
    exercises = enhanced_data.get('enhanced_perfect_exercises', [])
    print(f"总数: {len(exercises)}")
    
    enhanced_stats = defaultdict(int)
    for ex in exercises:
        for field in muscle_fields:
            if ex.get(field):
                enhanced_stats[field] += 1
    
    for field in muscle_fields:
        print(f"  {field}: {enhanced_stats[field]}")
except Exception as e:
    print(f"错误: {e}")

# 2. Neo4j
print("\n【2】Neo4j")
print("-"*50)

try:
    from neo4j import GraphDatabase
    driver = GraphDatabase.driver('bolt://neo4j:7687', auth=('neo4j', 'build_body_2024'))
    
    with driver.session() as session:
        total = session.run('MATCH (e:Exercise) RETURN count(e) as c').single()['c']
        print(f"总数: {total}")
        
        for field in muscle_fields:
            result = session.run(f'MATCH (e:Exercise) WHERE e.{field} IS NOT NULL RETURN count(e) as c')
            count = result.single()['c']
            print(f"  {field}: {count}")
    
    driver.close()
except Exception as e:
    print(f"错误: {e}")

# 3. Qdrant
print("\n【3】Qdrant")
print("-"*50)

try:
    from qdrant_client import QdrantClient
    client = QdrantClient(host='qdrant', port=6333)
    
    # 全量统计
    qdrant_stats = defaultdict(int)
    total = 0
    offset = None
    
    while True:
        results, next_offset = client.scroll('fitness_exercises_v2', limit=100, offset=offset, with_payload=True)
        if not results:
            break
        for r in results:
            total += 1
            for field in muscle_fields:
                if r.payload.get(field):
                    qdrant_stats[field] += 1
        offset = next_offset
        if offset is None:
            break
    
    print(f"总数: {total}")
    for field in muscle_fields:
        print(f"  {field}: {qdrant_stats[field]}")
except Exception as e:
    print(f"错误: {e}")

# 4. MySQL
print("\n【4】MySQL")
print("-"*50)

async def check_mysql():
    import aiomysql
    
    conn = await aiomysql.connect(
        host='fitness_mysql', port=3306,
        user='fitness_user', password='fitness_pass',
        db='fitness_app'
    )
    
    async with conn.cursor() as cursor:
        await cursor.execute('SELECT COUNT(*) FROM exercises')
        total = (await cursor.fetchone())[0]
        print(f"总数: {total}")
        
        for field in muscle_fields:
            try:
                await cursor.execute(f'SELECT COUNT(*) FROM exercises WHERE {field} IS NOT NULL')
                count = (await cursor.fetchone())[0]
                print(f"  {field}: {count}")
            except Exception as e:
                print(f"  {field}: 字段不存在")
    
    conn.close()

try:
    asyncio.run(check_mysql())
except Exception as e:
    print(f"错误: {e}")

print("\n" + "="*70)
print("检查完成")
print("="*70)
