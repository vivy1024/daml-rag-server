#!/usr/bin/env python3
"""分析muscles_tree的完整结构，提取所有肌肉及其层级关系"""
import json
from collections import defaultdict

with open('/app/data/enhanced_perfect_exercises_dataset.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
exercises = data['enhanced_perfect_exercises']

# 收集所有肌肉信息
muscles = {}  # id -> muscle_info
parent_relations = []  # (child_id, parent_id)

for e in exercises:
    tree = e.get('muscles_tree') or []
    for m in tree:
        if not m:
            continue
        muscle_id = m.get('id')
        if muscle_id and muscle_id not in muscles:
            muscles[muscle_id] = {
                'id': muscle_id,
                'name_en': m.get('name'),
                'name_zh': m.get('name_zh'),
                'scientific_name': m.get('scientific_name'),
                'level': m.get('level', 0),
                'parent_id': m.get('parent')
            }
        if m.get('parent'):
            parent_relations.append((muscle_id, m.get('parent')))

# 去重parent_relations
parent_relations = list(set(parent_relations))

print(f"=== 从 muscles_tree 提取的肌肉 ===")
print(f"总肌肉数: {len(muscles)}")
print(f"层级关系数: {len(parent_relations)}")

# 按level分组
by_level = defaultdict(list)
for m in muscles.values():
    by_level[m['level']].append(m)

print(f"\n=== 按层级分组 ===")
for level in sorted(by_level.keys()):
    print(f"\nLevel {level} ({len(by_level[level])}个):")
    for m in sorted(by_level[level], key=lambda x: x['name_zh'] or ''):
        parent_info = f" (parent: {m['parent_id']})" if m['parent_id'] else ""
        print(f"  {m['id']:3d}. {m['name_zh']} / {m['name_en']}{parent_info}")

print(f"\n=== 层级关系 ===")
for child_id, parent_id in sorted(parent_relations):
    child = muscles.get(child_id, {})
    parent = muscles.get(parent_id, {})
    print(f"  {child.get('name_zh', '?')} -> {parent.get('name_zh', '?')}")

# 输出JSON供后续使用
output = {
    'muscles': list(muscles.values()),
    'parent_relations': [{'child_id': c, 'parent_id': p} for c, p in parent_relations]
}
with open('/app/scripts/log/muscles_from_tree.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)
print(f"\n已保存到 /app/scripts/log/muscles_from_tree.json")
