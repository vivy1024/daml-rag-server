#!/usr/bin/env python3
"""
从文件系统同步muscles_secondary字段到MySQL和Qdrant
以文件系统为准，598个动作有secondary数据
"""
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
        # 只提取文件系统中实际存在的secondary字段
        if 'muscles_secondary_zh' in data:
            entry['muscles_secondary_zh'] = data['muscles_secondary_zh']
        if 'muscles_secondary_en' in data:
            entry['muscles_secondary_en'] = data['muscles_secondary_en']
        
        # 记录所有ID，没有secondary的设为None
        result[eid] = entry if entry else {'muscles_secondary_zh': None, 'muscles_secondary_en': None}
    except:
        pass

# 保存
output_path = Path(r"F:\build_body\data\logs\secondary_muscles_sync.json")
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

has_zh = sum(1 for v in result.values() if v.get('muscles_secondary_zh'))
has_en = sum(1 for v in result.values() if v.get('muscles_secondary_en'))
print(f"总数: {len(result)}")
print(f"有secondary_zh: {has_zh}")
print(f"有secondary_en: {has_en}")
print(f"已保存到: {output_path}")
