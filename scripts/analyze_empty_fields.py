#!/usr/bin/env python3
"""分析源文件中空值字段的动作"""
import json
import glob

files = glob.glob('yuzhen-backend/storage/app/public/exercises_v2/**/data.json', recursive=True)
print(f'源文件数量: {len(files)}')

# 找出各字段为空的动作
empty_diff = []
empty_force = []
empty_mechanic = []
empty_muscle = []

for filepath in files:
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        ex_info = {
            'id': data.get('id'),
            'name': data.get('name_zh'),
            'muscle': data.get('primary_muscle_zh'),
            'equipment': data.get('equipment_zh')
        }
        
        if not data.get('difficulty_zh'):
            empty_diff.append(ex_info)
        if not data.get('force_zh'):
            empty_force.append(ex_info)
        if not data.get('mechanic_zh'):
            empty_mechanic.append(ex_info)
        if not data.get('primary_muscle_zh'):
            empty_muscle.append(ex_info)
    except:
        pass

print(f'\ndifficulty_zh为空: {len(empty_diff)}个')
print('前5个示例:')
for ex in empty_diff[:5]:
    print(f"  ID {ex['id']}: {ex['name']}")

print(f'\nforce_zh为空: {len(empty_force)}个')
print('前5个示例:')
for ex in empty_force[:5]:
    print(f"  ID {ex['id']}: {ex['name']}")

print(f'\nmechanic_zh为空: {len(empty_mechanic)}个')
print('前5个示例:')
for ex in empty_mechanic[:5]:
    print(f"  ID {ex['id']}: {ex['name']}")

print(f'\nprimary_muscle_zh为空: {len(empty_muscle)}个')
print('前5个示例:')
for ex in empty_muscle[:5]:
    print(f"  ID {ex['id']}: {ex['name']}")
