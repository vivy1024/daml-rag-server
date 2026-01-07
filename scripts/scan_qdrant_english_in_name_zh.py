#!/usr/bin/env python3
"""
扫描Qdrant中name_zh包含英文的记录
"""

from qdrant_client import QdrantClient
import re

client = QdrantClient(host='qdrant', port=6333)

# 获取所有向量
all_points = []
offset = None
while True:
    results, offset = client.scroll(
        collection_name='fitness_exercises_v2',
        limit=500,
        offset=offset,
        with_payload=True
    )
    all_points.extend(results)
    if offset is None:
        break

print(f"Qdrant总向量数: {len(all_points)}")

# 检查name_zh包含英文的记录
english_pattern = re.compile(r'[A-Za-z]')
problems = []
for point in all_points:
    name_zh = point.payload.get('name_zh', '')
    if english_pattern.search(name_zh):
        problems.append({
            'id': point.payload.get('exercise_id'),
            'name_zh': name_zh
        })

print(f"name_zh包含英文的记录数: {len(problems)}")
print()
for p in problems[:30]:
    print(f"ID {p['id']}: {p['name_zh']}")
if len(problems) > 30:
    print(f"... 还有 {len(problems) - 30} 条")
