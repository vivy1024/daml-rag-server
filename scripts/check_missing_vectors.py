#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查Neo4j和Qdrant之间的数据差异
"""

from neo4j import GraphDatabase
from qdrant_client import QdrantClient

# 连接Neo4j
neo4j_driver = GraphDatabase.driver('bolt://neo4j:7687', auth=('neo4j', 'build_body_2024'))

# 连接Qdrant
qdrant_client = QdrantClient(host='qdrant', port=6333)

# 获取Neo4j中所有Exercise的ID
with neo4j_driver.session() as session:
    result = session.run('MATCH (e:Exercise) RETURN e.id as id ORDER BY e.id')
    neo4j_ids = set([record['id'] for record in result])

print(f'Neo4j Exercise总数: {len(neo4j_ids)}')

# 获取Qdrant中所有向量的ID
scroll_result = qdrant_client.scroll(
    collection_name='fitness_exercises_v2',
    limit=2000,
    with_payload=True,
    with_vectors=False
)
qdrant_ids = set([int(point.id) for point in scroll_result[0]])

print(f'Qdrant向量总数: {len(qdrant_ids)}')

# 找出缺失的ID
missing_ids = neo4j_ids - qdrant_ids
print(f'\n缺失的Exercise ID ({len(missing_ids)}个):')
print(sorted(missing_ids))

# 查询缺失动作的详细信息
if missing_ids:
    with neo4j_driver.session() as session:
        result = session.run(
            'MATCH (e:Exercise) WHERE e.id IN $ids RETURN e.id as id, e.name_zh as name_zh, e.name as name_en ORDER BY e.id',
            ids=list(missing_ids)
        )
        print('\n缺失动作详情:')
        for record in result:
            print(f'  ID {record["id"]}: {record["name_zh"]} ({record["name_en"]})')

neo4j_driver.close()
