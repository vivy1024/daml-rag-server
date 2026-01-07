#!/usr/bin/env python3
"""检查数据集中grips字段"""

import json

with open('/app/data/enhanced_perfect_exercises_dataset.json') as f:
    d = json.load(f)
exercises = d['enhanced_perfect_exercises']

empty_grips = sum(1 for ex in exercises if not ex.get('grips_zh') or len(ex.get('grips_zh', [])) == 0)
print(f'数据集grips_zh空值: {empty_grips}')

# 检查有grips的示例
print('\n有grips的示例:')
count = 0
for ex in exercises:
    grips = ex.get('grips_zh', [])
    if grips and count < 5:
        print(f"  ID {ex['id']}: grips_zh={grips}")
        count += 1
