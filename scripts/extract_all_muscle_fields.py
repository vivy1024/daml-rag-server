#!/usr/bin/env python3
"""从文件系统提取所有肌肉字段"""
import json
from pathlib import Path

base_path = Path(r"F:\build_body\yuzhen-backend\storage\app\public\exercises_v2")

muscle_fields = [
    'muscles_tree', 'muscles_primary_tree', 'muscles_secondary_tree',
    'muscles_primary_zh', 'muscles_primary_en',
    'muscles_secondary_zh', 'muscles_secondary_en',
    'all_muscles_zh', 'all_muscles_en',
    'primary_muscle_zh', 'primary_muscle_en'
]

result = {}

for data_file in base_path.rglob("data.json"):
    try:
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        eid = data.get('id')
        if not eid:
            continue
        
        entry = {}
        for field in muscle_fields:
            if field in data:
                entry[field] = data[field]
        
        result[eid] = entry
    except Exception as e:
        print(f"错误 {data_file}: {e}")

# 保存
output_path = Path(r"F:\build_body\data\logs\all_muscle_fields.json")
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False)

print(f"已提取 {len(result)} 条记录")

# 统计
from collections import defaultdict
stats = defaultdict(int)
for eid, fields in result.items():
    for field in muscle_fields:
        if fields.get(field):
            stats[field] += 1

print("\n字段统计:")
for field in muscle_fields:
    print(f"  {field}: {stats[field]}")
