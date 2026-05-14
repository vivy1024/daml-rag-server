#!/usr/bin/env python3
"""验证同步结果"""
from neo4j import GraphDatabase
from qdrant_client import QdrantClient

# Neo4j验证
print("=== Neo4j验证 ===")
driver = GraphDatabase.driver('bolt://fitness_neo4j:7687', auth=('neo4j', 'build_body_2024'))
with driver.session() as s:
    r = s.run("MATCH (e:Exercise) WHERE e.description_zh IS NOT NULL AND e.description_zh <> '' RETURN count(e) as cnt")
    print(f"有description_zh: {r.single()['cnt']}")
    r = s.run("MATCH (e:Exercise) WHERE e.force_zh IS NOT NULL AND e.force_zh <> '' RETURN count(e) as cnt")
    print(f"有force_zh: {r.single()['cnt']}")
    r = s.run("MATCH (e:Exercise) WHERE e.mechanic_zh IS NOT NULL AND e.mechanic_zh <> '' RETURN count(e) as cnt")
    print(f"有mechanic_zh: {r.single()['cnt']}")
driver.close()

# Qdrant验证
print("\n=== Qdrant验证 ===")
client = QdrantClient(host='fitness_qdrant', port=6333)
result = client.scroll(collection_name='fitness_exercises_v2', limit=100, with_payload=True)
has_desc = sum(1 for p in result[0] if p.payload.get('description_zh'))
has_force = sum(1 for p in result[0] if p.payload.get('force_zh'))
print(f"前100个中有description_zh: {has_desc}")
print(f"前100个中有force_zh: {has_force}")

print("\n✅ 验证完成")
