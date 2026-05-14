#!/usr/bin/env python3
"""
修复 primary_muscle_zh 字段
从 muscles_primary_zh[0] 补全缺失的 primary_muscle_zh
"""
import json
from pathlib import Path

# 文件系统路径
base_path = Path(r"F:\build_body\yuzhen-backend\storage\app\public\exercises_v2")

def fix_primary_muscle():
    """修复 primary_muscle_zh 字段"""
    
    fixed_count = 0
    skipped_count = 0
    already_has_count = 0
    
    for data_file in base_path.rglob("data.json"):
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        modified = False
        exercise_id = data.get('id')
        name_zh = data.get('name_zh', '')
        
        # 检查 primary_muscle_zh
        primary_muscle_zh = data.get('primary_muscle_zh')
        muscles_primary_zh = data.get('muscles_primary_zh', [])
        
        if primary_muscle_zh:
            already_has_count += 1
        elif muscles_primary_zh:
            # 从数组第一个元素补全
            data['primary_muscle_zh'] = muscles_primary_zh[0]
            modified = True
            fixed_count += 1
            print(f"✅ 修复 ID {exercise_id}: {name_zh}")
            print(f"   primary_muscle_zh = {muscles_primary_zh[0]}")
        else:
            skipped_count += 1
            print(f"⚠️ 跳过 ID {exercise_id}: {name_zh} (无 muscles_primary_zh)")
        
        # 同样检查 primary_muscle_en
        primary_muscle_en = data.get('primary_muscle_en')
        muscles_primary_en = data.get('muscles_primary_en', [])
        
        if not primary_muscle_en and muscles_primary_en:
            data['primary_muscle_en'] = muscles_primary_en[0]
            modified = True
            print(f"   primary_muscle_en = {muscles_primary_en[0]}")
        
        # 保存修改
        if modified:
            with open(data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"\n📊 修复统计:")
    print(f"  已有 primary_muscle_zh: {already_has_count}")
    print(f"  已修复: {fixed_count}")
    print(f"  跳过 (无数据): {skipped_count}")
    print(f"  总计: {already_has_count + fixed_count + skipped_count}")

if __name__ == "__main__":
    fix_primary_muscle()
