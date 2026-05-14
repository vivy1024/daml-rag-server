#!/usr/bin/env python3
"""
删除 primary_muscle_zh/en 单值字段，统一使用 muscles_primary_zh/en 数组字段
"""
import json
from pathlib import Path

base_path = Path(r"F:\build_body\yuzhen-backend\storage\app\public\exercises_v2")

def remove_primary_muscle_fields():
    """从文件系统删除 primary_muscle_zh/en 字段"""
    
    removed_count = 0
    
    for data_file in base_path.rglob("data.json"):
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        modified = False
        
        # 删除 primary_muscle_zh
        if 'primary_muscle_zh' in data:
            del data['primary_muscle_zh']
            modified = True
        
        # 删除 primary_muscle_en
        if 'primary_muscle_en' in data:
            del data['primary_muscle_en']
            modified = True
        
        if modified:
            with open(data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            removed_count += 1
    
    print(f"✅ 已从 {removed_count} 个文件中删除 primary_muscle_zh/en 字段")

if __name__ == "__main__":
    remove_primary_muscle_fields()
