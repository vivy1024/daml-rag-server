#!/usr/bin/env python3
"""检查原始爬取数据的肌肉字段"""
import json

with open(r'F:\build_body\scripts\log\temp_musclewiki_full_exercise.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f'原始爬取数据总数: {len(data)}')
print()

# 统计肌肉相关字段
muscle_fields = set()
for ex in data:
    for key in ex.keys():
        if 'muscle' in key.lower():
            muscle_fields.add(key)

print('原始数据中的肌肉字段:')
for f in sorted(muscle_fields):
    print(f'  {f}')

print()

# 找一个有secondary的例子
for ex in data:
    if ex.get('secondary_muscles'):
        print(f"=== 示例: ID {ex.get('id')} {ex.get('name')} ===")
        for key in sorted(ex.keys()):
            if 'muscle' in key.lower():
                print(f"  {key}: {ex[key]}")
        break
