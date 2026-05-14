#!/usr/bin/env python
"""测试Qdrant向量检索"""

from qdrant_client import QdrantClient

client = QdrantClient(host='qdrant', port=6333)

# 检查集合
collections = client.get_collections()
print('可用集合:')
for c in collections.collections:
    info = client.get_collection(c.name)
    print(f'  - {c.name}: {info.points_count} 个向量')

# 测试搜索
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('BAAI/bge-m3')
query = '推荐胸部训练动作'
vector = model.encode(query).tolist()

# 在fitness_exercises_v2集合中搜索（注意集合名）
results = client.query_points(
    collection_name='fitness_exercises_v2',
    query=vector,
    limit=5
)
print(f'\n搜索 "{query}" 结果: {len(results.points)} 个')
for r in results.points[:3]:
    print(f'  - {r.payload.get("name_zh", "未知")} (score: {r.score:.3f})')
