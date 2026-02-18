#!/usr/bin/env python3
"""检查Qdrant中的muscles字段"""
from qdrant_client import QdrantClient

client = QdrantClient(host='qdrant', port=6333)
results, _ = client.scroll('fitness_exercises_v2', limit=5, with_payload=True)

for r in results:
    p = r.payload
    print(f"ID {p.get('id')}: {p.get('name_zh')}")
    print(f"  muscles_tree: {p.get('muscles_tree')}")
    print(f"  muscles_primary_zh: {p.get('muscles_primary_zh')}")
    print(f"  muscles_primary_en: {p.get('muscles_primary_en')}")
    print(f"  muscles_secondary_zh: {p.get('muscles_secondary_zh')}")
    print(f"  muscles_secondary_en: {p.get('muscles_secondary_en')}")
    print()
