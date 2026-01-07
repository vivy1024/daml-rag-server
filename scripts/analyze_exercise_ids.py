#!/usr/bin/env python3
"""
分析文件系统中的动作ID分布
扫描 exercises_v2 目录，收集所有存在的ID
"""
import os
import json
from pathlib import Path

def scan_exercise_ids():
    """扫描文件系统中所有动作ID"""
    base_path = Path("/app/storage/exercises_v2")
    
    if not base_path.exists():
        print(f"❌ 路径不存在: {base_path}")
        return []
    
    exercise_ids = []
    
    # 遍历所有范围目录 (0000-0099, 0100-0199, ...)
    for range_dir in sorted(base_path.iterdir()):
        if not range_dir.is_dir():
            continue
        
        # 遍历子范围目录 (0000-0009, 0010-0019, ...)
        for sub_range_dir in sorted(range_dir.iterdir()):
            if not sub_range_dir.is_dir():
                continue
            
            # 遍历具体ID目录
            for id_dir in sorted(sub_range_dir.iterdir()):
                if id_dir.is_dir():
                    try:
                        exercise_id = int(id_dir.name)
                        exercise_ids.append(exercise_id)
                    except ValueError:
                        print(f"⚠️ 无效ID目录: {id_dir}")
    
    return sorted(exercise_ids)

def analyze_gaps(ids):
    """分析ID中的间隙"""
    if not ids:
        return []
    
    gaps = []
    for i in range(1, max(ids) + 1):
        if i not in ids:
            gaps.append(i)
    return gaps

def main():
    print("🔍 扫描文件系统中的动作ID...")
    ids = scan_exercise_ids()
    
    print(f"\n📊 统计结果:")
    print(f"  - 总动作数: {len(ids)}")
    print(f"  - 最小ID: {min(ids) if ids else 'N/A'}")
    print(f"  - 最大ID: {max(ids) if ids else 'N/A'}")
    
    gaps = analyze_gaps(ids)
    print(f"  - 缺失ID数: {len(gaps)}")
    
    if gaps and len(gaps) <= 50:
        print(f"  - 缺失ID列表: {gaps}")
    elif gaps:
        print(f"  - 前20个缺失ID: {gaps[:20]}")
        print(f"  - 后20个缺失ID: {gaps[-20:]}")
    
    # 保存完整ID列表
    output = {
        "total_count": len(ids),
        "min_id": min(ids) if ids else None,
        "max_id": max(ids) if ids else None,
        "missing_count": len(gaps),
        "missing_ids": gaps,
        "existing_ids": ids
    }
    
    output_path = Path("/app/scripts/log/exercise_ids_analysis.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 完整分析结果已保存到: {output_path}")

if __name__ == "__main__":
    main()
