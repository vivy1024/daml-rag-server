#!/usr/bin/env python3
"""
从文件系统同步英文字段到Qdrant
在本地运行，通过Qdrant HTTP API更新
"""
import json
from pathlib import Path
from qdrant_client import QdrantClient

# 连接Qdrant（本地端口映射）
client = QdrantClient(host='localhost', port=6333)

# 文件系统路径
base_path = Path(r"F:\build_body\yuzhen-backend\storage\app\public\exercises_v2")

# 统计
updated = 0
total = 0

# 遍历所有data.json
for data_file in base_path.rglob("data.json"):
    total += 1
    try:
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        exercise_id = data.get('id')
        if not exercise_id:
            continue
        
        # 准备更新的字段
        update_payload = {}
        
        # 英文字段
        if data.get('muscles_primary_en'):
            update_payload['muscles_primary_en'] = data['muscles_primary_en']
        if data.get('muscles_secondary_en'):
            update_payload['muscles_secondary_en'] = data['muscles_secondary_en']
        if data.get('all_muscles_en'):
            update_payload['all_muscles_en'] = data['all_muscles_en']
        
        if update_payload:
            # 通过exercise_id查找point
            results = client.scroll(
                collection_name="fitness_exercises_v2",
                scroll_filter={
                    "must": [{"key": "id", "match": {"value": exercise_id}}]
                },
                limit=1,
                with_payload=False
            )
            
            if results[0]:
                point_id = results[0][0].id
                client.set_payload(
                    collection_name="fitness_exercises_v2",
                    payload=update_payload,
                    points=[point_id]
                )
                updated += 1
                
                if updated % 100 == 0:
                    print(f"已更新 {updated} 个点...")
    
    except Exception as e:
        print(f"错误 {data_file}: {e}")

print(f"\n完成！总文件: {total}, 已更新: {updated}")

# 验证
print("\n验证结果:")
results, _ = client.scroll("fitness_exercises_v2", limit=5, with_payload=True)
for r in results:
    p = r.payload
    print(f"ID {p.get('id')}: {p.get('name_zh')}")
    print(f"  muscles_primary_en: {p.get('muscles_primary_en')}")
    print(f"  muscles_secondary_en: {p.get('muscles_secondary_en')}")
