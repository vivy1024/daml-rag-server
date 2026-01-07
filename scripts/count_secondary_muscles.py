#!/usr/bin/env python3
"""统计文件系统中有muscles_secondary字段的文件数"""
import json
from pathlib import Path

base_path = Path(r"F:\build_body\yuzhen-backend\storage\app\public\exercises_v2")
total = 0
has_secondary_zh = 0
has_secondary_en = 0

for data_file in base_path.rglob("data.json"):
    total += 1
    try:
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if data.get("muscles_secondary_zh"):
            has_secondary_zh += 1
        if data.get("muscles_secondary_en"):
            has_secondary_en += 1
    except:
        pass

print(f"总文件数: {total}")
print(f"有muscles_secondary_zh: {has_secondary_zh}")
print(f"有muscles_secondary_en: {has_secondary_en}")

# 显示几个有secondary的例子
print("\n有secondary的示例:")
count = 0
for data_file in base_path.rglob("data.json"):
    if count >= 3:
        break
    try:
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if data.get("muscles_secondary_zh"):
            print(f"  ID {data['id']}: {data['name_zh']}")
            print(f"    primary: {data.get('muscles_primary_zh')}")
            print(f"    secondary_zh: {data.get('muscles_secondary_zh')}")
            print(f"    secondary_en: {data.get('muscles_secondary_en')}")
            count += 1
    except:
        pass
