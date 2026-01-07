#!/usr/bin/env python3
"""从JSON文件更新Qdrant的英文字段"""
import json
from qdrant_client import QdrantClient

# 读取JSON数据（通过logs目录挂载）
with open('/app/logs/en_muscles_fields.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f"读取到 {len(data)} 条记录")

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
        client.set_payload(
            collection_name="fitness_exercises_v2",
            payload=fields,
            points=[point_id]
        )
        updated += 1
        
        if updated % 200 == 0:
            print(f"已更新 {updated} 个点...")

print(f"\n完成！共更新 {updated} 个点")

# 验证
print("\n验证结果:")
results, _ = client.scroll("fitness_exercises_v2", limit=5, with_payload=True)
for r in results:
    p = r.payload
    print(f"ID {p.get('id')}: {p.get('name_zh')}")
    print(f"  muscles_primary_en: {p.get('muscles_primary_en')}")
    print(f"  muscles_secondary_en: {p.get('muscles_secondary_en')}")
