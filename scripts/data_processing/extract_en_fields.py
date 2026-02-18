#!/usr/bin/env python3
"""从文件系统提取英文字段，生成JSON供容器内脚本使用"""
import json
from pathlib import Path

base_path = Path(r"F:\build_body\yuzhen-backend\storage\app\public\exercises_v2")
result = {}

for data_file in base_path.rglob("data.json"):
    try:
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        eid = data.get('id')
        if not eid:
            continue
        
        entry = {}
        if data.get('muscles_primary_en'):
            entry['muscles_primary_en'] = data['muscles_primary_en']
        if data.get('muscles_secondary_en'):
            entry['muscles_secondary_en'] = data['muscles_secondary_en']
        if data.get('all_muscles_en'):
            entry['all_muscles_en'] = data['all_muscles_en']
        
        if entry:
            result[eid] = entry
    except:
        pass

# 保存到data目录
output_path = Path(r"F:\build_body\data\en_muscles_fields.json")
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print(f"已提取 {len(result)} 条记录到 {output_path}")

# 显示示例
for eid in list(result.keys())[:3]:
    print(f"ID {eid}: {result[eid]}")
