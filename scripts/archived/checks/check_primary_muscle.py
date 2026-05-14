#!/usr/bin/env python3
"""检查primary_muscle字段"""
import json
from pathlib import Path

base_path = Path(r"F:\build_body\yuzhen-backend\storage\app\public\exercises_v2")

# 找一个缺少primary_muscle_zh的动作
missing_zh = []
for data_file in base_path.rglob("data.json"):
    with open(data_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    if not data.get('primary_muscle_zh') and data.get('muscles_primary_zh'):
        missing_zh.append((data_file, data))
        if len(missing_zh) >= 3:
            break

print("缺少primary_muscle_zh但有muscles_primary_zh的动作:")
for path, data in missing_zh:
    print(f"\nID {data.get('id')} {data.get('name_zh')}:")
    print(f"  primary_muscle_zh: {data.get('primary_muscle_zh')}")
    print(f"  primary_muscle_en: {data.get('primary_muscle_en')}")
    print(f"  muscles_primary_zh: {data.get('muscles_primary_zh')}")
    print(f"  muscles_primary_en: {data.get('muscles_primary_en')}")

# 检查一个有primary_muscle_zh的动作
data_file2 = base_path / "0000-0099/0030-0039/39/data.json"
with open(data_file2, 'r', encoding='utf-8') as f:
    data2 = json.load(f)

print("\n\n有primary_muscle_zh的动作:")
print(f"ID {data2.get('id')} {data2.get('name_zh')}:")
print(f"  primary_muscle_zh: {data2.get('primary_muscle_zh')}")
print(f"  primary_muscle_en: {data2.get('primary_muscle_en')}")
print(f"  muscles_primary_zh: {data2.get('muscles_primary_zh')}")
print(f"  muscles_primary_en: {data2.get('muscles_primary_en')}")
