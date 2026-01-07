#!/usr/bin/env python3
"""
分析 primary_muscle_zh/en 字段的来源和差异

关键发现：
1. 原始爬取数据(temp_musclewiki_full_exercise.json)中没有 primary_muscle_zh/en 字段
2. 原始数据只有 muscles_primary (数组，包含完整树结构)
3. primary_muscle_zh/en 是后期处理时从 muscles_primary 提取的单值字段
4. 差异原因：部分动作的 muscles_primary 为空，导致无法提取 primary_muscle
"""
import json
from pathlib import Path
from collections import defaultdict

# 文件系统路径
base_path = Path(r"F:\build_body\yuzhen-backend\storage\app\public\exercises_v2")

def analyze_primary_muscle():
    """分析 primary_muscle 字段的来源和差异"""
    
    stats = {
        'total': 0,
        'has_primary_muscle_zh': 0,
        'has_primary_muscle_en': 0,
        'has_muscles_primary_zh': 0,
        'has_muscles_primary_en': 0,
        'has_muscles_primary_tree': 0,
        'missing_primary_muscle_zh_but_has_array': [],
        'missing_primary_muscle_en_but_has_array': [],
        'missing_both_primary_and_array': [],
        'primary_muscle_zh_values': defaultdict(int),
        'primary_muscle_en_values': defaultdict(int),
    }
    
    for data_file in base_path.rglob("data.json"):
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        stats['total'] += 1
        exercise_id = data.get('id')
        name_zh = data.get('name_zh', '')
        
        # 检查各字段
        primary_muscle_zh = data.get('primary_muscle_zh')
        primary_muscle_en = data.get('primary_muscle_en')
        muscles_primary_zh = data.get('muscles_primary_zh', [])
        muscles_primary_en = data.get('muscles_primary_en', [])
        muscles_primary_tree = data.get('muscles_primary_tree', [])
        
        if primary_muscle_zh:
            stats['has_primary_muscle_zh'] += 1
            stats['primary_muscle_zh_values'][primary_muscle_zh] += 1
        
        if primary_muscle_en:
            stats['has_primary_muscle_en'] += 1
            stats['primary_muscle_en_values'][primary_muscle_en] += 1
        
        if muscles_primary_zh:
            stats['has_muscles_primary_zh'] += 1
        
        if muscles_primary_en:
            stats['has_muscles_primary_en'] += 1
        
        if muscles_primary_tree:
            stats['has_muscles_primary_tree'] += 1
        
        # 分析差异
        if not primary_muscle_zh and muscles_primary_zh:
            stats['missing_primary_muscle_zh_but_has_array'].append({
                'id': exercise_id,
                'name_zh': name_zh,
                'muscles_primary_zh': muscles_primary_zh
            })
        
        if not primary_muscle_en and muscles_primary_en:
            stats['missing_primary_muscle_en_but_has_array'].append({
                'id': exercise_id,
                'name_zh': name_zh,
                'muscles_primary_en': muscles_primary_en
            })
        
        if not primary_muscle_zh and not muscles_primary_zh:
            stats['missing_both_primary_and_array'].append({
                'id': exercise_id,
                'name_zh': name_zh,
                'muscles_primary_tree': muscles_primary_tree
            })
    
    return stats

def main():
    print("=" * 80)
    print("分析 primary_muscle_zh/en 字段的来源和差异")
    print("=" * 80)
    
    stats = analyze_primary_muscle()
    
    print(f"\n📊 总体统计:")
    print(f"  总动作数: {stats['total']}")
    print(f"  有 primary_muscle_zh: {stats['has_primary_muscle_zh']}")
    print(f"  有 primary_muscle_en: {stats['has_primary_muscle_en']}")
    print(f"  有 muscles_primary_zh: {stats['has_muscles_primary_zh']}")
    print(f"  有 muscles_primary_en: {stats['has_muscles_primary_en']}")
    print(f"  有 muscles_primary_tree: {stats['has_muscles_primary_tree']}")
    
    print(f"\n⚠️ 差异分析:")
    print(f"  缺少 primary_muscle_zh 但有 muscles_primary_zh: {len(stats['missing_primary_muscle_zh_but_has_array'])}")
    print(f"  缺少 primary_muscle_en 但有 muscles_primary_en: {len(stats['missing_primary_muscle_en_but_has_array'])}")
    print(f"  两者都缺少: {len(stats['missing_both_primary_and_array'])}")
    
    # 显示缺少 primary_muscle_zh 但有数组的示例
    if stats['missing_primary_muscle_zh_but_has_array']:
        print(f"\n📋 缺少 primary_muscle_zh 但有 muscles_primary_zh 的示例 (前5个):")
        for item in stats['missing_primary_muscle_zh_but_has_array'][:5]:
            print(f"  ID {item['id']}: {item['name_zh']}")
            print(f"    muscles_primary_zh: {item['muscles_primary_zh']}")
    
    # 显示两者都缺少的示例
    if stats['missing_both_primary_and_array']:
        print(f"\n📋 两者都缺少的示例 (前5个):")
        for item in stats['missing_both_primary_and_array'][:5]:
            print(f"  ID {item['id']}: {item['name_zh']}")
            print(f"    muscles_primary_tree: {item['muscles_primary_tree']}")
    
    # 显示 primary_muscle_zh 的值分布
    print(f"\n📊 primary_muscle_zh 值分布 (前10个):")
    sorted_values = sorted(stats['primary_muscle_zh_values'].items(), key=lambda x: -x[1])
    for value, count in sorted_values[:10]:
        print(f"  {value}: {count}")
    
    print("\n" + "=" * 80)
    print("结论:")
    print("=" * 80)
    print("""
1. 原始爬取数据中没有 primary_muscle_zh/en 字段
2. 这些字段是后期处理时从 muscles_primary 数组提取的第一个元素
3. 差异原因：
   - 部分动作的 muscles_primary 数组为空
   - 或者后期处理脚本没有覆盖所有动作
4. 解决方案：
   - 可以从 muscles_primary_zh[0] 补全 primary_muscle_zh
   - 可以从 muscles_primary_en[0] 补全 primary_muscle_en
   - 或者直接使用 muscles_primary_zh/en 数组，废弃单值字段
""")

if __name__ == "__main__":
    main()
