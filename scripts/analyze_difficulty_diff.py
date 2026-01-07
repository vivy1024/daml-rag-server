#!/usr/bin/env python3
"""
分析源文件和目标数据集的difficulty差异

源文件：yuzhen-backend/storage/app/public/exercises_v2/
目标：perfect_enhanced_dataset/data/enhanced_perfect_exercises_dataset.json

重点：novice在源文件是"零基础"，在目标是"新手"
"""
import os
import json
import glob
from collections import defaultdict

# 路径配置（容器内路径）
SOURCE_DIR = "/app/../yuzhen-backend/storage/app/public/exercises_v2"
TARGET_FILE = "/app/../perfect_enhanced_dataset/data/enhanced_perfect_exercises_dataset.json"

def load_source_difficulties():
    """从源文件加载difficulty"""
    difficulties = {}
    pattern = os.path.join(SOURCE_DIR, "**/data.json")
    files = glob.glob(pattern, recursive=True)
    
    print(f"源文件数量: {len(files)}")
    
    for filepath in files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            ex_id = data.get('id')
            diff_zh = data.get('difficulty_zh', '')
            diff_en = data.get('difficulty_en', '')
            
            if ex_id:
                difficulties[ex_id] = {
                    'zh': diff_zh,
                    'en': diff_en,
                    'name': data.get('name_zh', '')
                }
        except Exception as e:
            pass
    
    return difficulties

def load_target_difficulties():
    """从目标数据集加载difficulty"""
    difficulties = {}
    
    with open(TARGET_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    exercises = data.get('exercises', [])
    print(f"目标数据集动作数量: {len(exercises)}")
    
    for ex in exercises:
        ex_id = ex.get('id')
        diff_zh = ex.get('difficulty_zh', '')
        diff_en = ex.get('difficulty_en', '')
        
        if ex_id:
            difficulties[ex_id] = {
                'zh': diff_zh,
                'en': diff_en,
                'name': ex.get('name_zh', '')
            }
    
    return difficulties

def analyze_distribution(difficulties, name):
    """分析difficulty分布"""
    dist_zh = defaultdict(int)
    dist_en = defaultdict(int)
    
    for ex_id, data in difficulties.items():
        dist_zh[data['zh']] += 1
        dist_en[data['en']] += 1
    
    print(f"\n=== {name} difficulty_zh 分布 ===")
    for diff, count in sorted(dist_zh.items(), key=lambda x: -x[1]):
        print(f"  {diff or '(空)'}: {count}")
    
    print(f"\n=== {name} difficulty_en 分布 ===")
    for diff, count in sorted(dist_en.items(), key=lambda x: -x[1]):
        print(f"  {diff or '(空)'}: {count}")
    
    return dist_zh, dist_en

def find_differences(source, target):
    """找出差异"""
    differences = []
    
    for ex_id in source:
        if ex_id in target:
            src = source[ex_id]
            tgt = target[ex_id]
            
            if src['zh'] != tgt['zh']:
                differences.append({
                    'id': ex_id,
                    'name': src['name'],
                    'source_zh': src['zh'],
                    'target_zh': tgt['zh'],
                    'source_en': src['en'],
                    'target_en': tgt['en']
                })
    
    return differences

def main():
    print("=" * 60)
    print("分析源文件和目标数据集的difficulty差异")
    print("=" * 60)
    
    # 加载数据
    source = load_source_difficulties()
    target = load_target_difficulties()
    
    print(f"\n源文件加载: {len(source)} 个动作")
    print(f"目标数据集加载: {len(target)} 个动作")
    
    # 分析分布
    src_zh, src_en = analyze_distribution(source, "源文件")
    tgt_zh, tgt_en = analyze_distribution(target, "目标数据集")
    
    # 找出差异
    differences = find_differences(source, target)
    
    print(f"\n=== 差异统计 ===")
    print(f"总差异数量: {len(differences)}")
    
    # 按差异类型分组
    diff_types = defaultdict(list)
    for d in differences:
        key = f"{d['source_zh']} -> {d['target_zh']}"
        diff_types[key].append(d)
    
    print("\n=== 差异类型分布 ===")
    for diff_type, items in sorted(diff_types.items(), key=lambda x: -len(x[1])):
        print(f"  {diff_type}: {len(items)} 个")
        # 显示前3个示例
        for item in items[:3]:
            print(f"    - ID {item['id']}: {item['name']}")
    
    # 特别关注 novice/零基础 vs 新手
    novice_diff = [d for d in differences if '零基础' in d['source_zh'] or '新手' in d['target_zh']]
    print(f"\n=== 零基础/新手 差异 ===")
    print(f"数量: {len(novice_diff)}")
    for d in novice_diff[:10]:
        print(f"  ID {d['id']}: {d['name']}")
        print(f"    源: {d['source_zh']} ({d['source_en']})")
        print(f"    目标: {d['target_zh']} ({d['target_en']})")

if __name__ == "__main__":
    main()
