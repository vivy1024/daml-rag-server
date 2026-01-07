#!/usr/bin/env python3
"""
找出真正的固定值字段（所有非空值都相同）
"""
import json
from collections import Counter

DATASET_FILE = "perfect_enhanced_dataset/data/enhanced_perfect_exercises_dataset.json"

with open(DATASET_FILE, 'r', encoding='utf-8') as f:
    data = json.load(f)
exercises = data.get('enhanced_perfect_exercises', [])
print(f"数据集动作数量: {len(exercises)}")

# 检查特定字段
fields_to_check = [
    'key_nutrients', 'recommended_foods', 'nutrition_timing',
    'safety_pre_check', 'equipment_risks', 'safety_level',
    'rep_range', 'set_range', 'rest_period', 'intensity_percentage'
]

print("\n=== 检查疑似固定值字段 ===")
for field in fields_to_check:
    values = []
    for ex in exercises:
        val = ex.get(field)
        if val:  # 只统计非空值
            if isinstance(val, list):
                val = json.dumps(val, ensure_ascii=False, sort_keys=True)
            values.append(str(val))
    
    if values:
        counter = Counter(values)
        unique = len(counter)
        most_common = counter.most_common(3)
        
        print(f"\n{field}:")
        print(f"  非空值数量: {len(values)}")
        print(f"  唯一值数量: {unique}")
        print(f"  最常见值:")
        for val, cnt in most_common:
            ratio = cnt / len(values) * 100
            val_display = val[:80] + '...' if len(val) > 80 else val
            print(f"    {val_display}: {cnt} ({ratio:.1f}%)")

# 找出广告动作
print("\n\n=== 广告内容动作 ===")
ad_exercises = []
for ex in exercises:
    name = ex.get('name_zh', '') or ex.get('name_en', '')
    if '随时随地' in name or 'Simplify' in name or '简化' in name:
        ad_exercises.append({
            'id': ex.get('id'),
            'name_zh': ex.get('name_zh'),
            'name_en': ex.get('name_en')
        })

print(f"发现 {len(ad_exercises)} 个广告动作:")
for ex in ad_exercises:
    print(f"  ID {ex['id']}: {ex['name_zh']} / {ex['name_en']}")
