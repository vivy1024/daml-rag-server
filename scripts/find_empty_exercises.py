#!/usr/bin/env python3
"""找出多个字段都为空的动作，用于重新爬取测试"""

import json

with open('/app/data/enhanced_perfect_exercises_dataset.json') as f:
    d = json.load(f)
exercises = d['enhanced_perfect_exercises']

# 找出多个字段都为空的动作
empty_all = []
for ex in exercises:
    empty_fields = []
    
    if not ex.get('description_zh'):
        empty_fields.append('description_zh')
    if not ex.get('force_zh'):
        empty_fields.append('force_zh')
    if not ex.get('mechanic_zh'):
        empty_fields.append('mechanic_zh')
    if not ex.get('grips_zh') or len(ex.get('grips_zh', [])) == 0:
        empty_fields.append('grips_zh')
    
    if len(empty_fields) >= 3:  # 至少3个字段为空
        empty_all.append({
            'id': ex['id'],
            'name_zh': ex.get('name_zh', ''),
            'name_en': ex.get('name_en', ''),
            'slug': ex.get('slug', ''),
            'empty_fields': empty_fields,
            'empty_count': len(empty_fields)
        })

# 按空值数量排序
empty_all.sort(key=lambda x: -x['empty_count'])

print(f'找到 {len(empty_all)} 个动作有3个以上字段为空')
print()
print('典型示例（前10个）:')
print('-' * 80)
for item in empty_all[:10]:
    print(f"ID {item['id']}: {item['name_zh']} ({item['name_en']})")
    print(f"  slug: {item['slug']}")
    print(f"  空字段({item['empty_count']}): {', '.join(item['empty_fields'])}")
    print()

# 输出用于爬取的ID列表
print('=' * 80)
print('建议重新爬取的ID（前5个）:')
test_ids = [item['id'] for item in empty_all[:5]]
print(test_ids)
