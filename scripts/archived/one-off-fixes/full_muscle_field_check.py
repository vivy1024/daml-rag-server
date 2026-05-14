#!/usr/bin/env python3
"""
全面检查肌肉字段一致性
检查：文件系统、两个增强数据文件、Neo4j、Qdrant、MySQL
"""
import json
from pathlib import Path
from collections import defaultdict

print("="*70)
print("肌肉字段全面一致性检查")
print("="*70)

# 1. 文件系统统计
print("\n【1】文件系统 (exercises_v2)")
print("-"*50)

fs_path = Path(r"F:\build_body\yuzhen-backend\storage\app\public\exercises_v2")
fs_stats = defaultdict(int)
fs_total = 0

muscle_fields = [
    'muscles_tree', 'muscles_primary_tree', 'muscles_secondary_tree',
    'muscles_primary_zh', 'muscles_primary_en',
    'muscles_secondary_zh', 'muscles_secondary_en',
    'all_muscles_zh', 'all_muscles_en',
    'primary_muscle_zh', 'primary_muscle_en'
]

for data_file in fs_path.rglob("data.json"):
    fs_total += 1
    with open(data_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    for field in muscle_fields:
        if data.get(field):
            fs_stats[field] += 1

print(f"总数: {fs_total}")
for field in muscle_fields:
    print(f"  {field}: {fs_stats[field]}")

# 2. 增强数据文件1
print("\n【2】增强数据文件 (enhanced_perfect_exercises_dataset.json)")
print("-"*50)

enhanced_path = Path(r"F:\build_body\data\enhanced_perfect_exercises_dataset.json")
if enhanced_path.exists():
    with open(enhanced_path, 'r', encoding='utf-8') as f:
        enhanced_data = json.load(f)
    
    exercises = enhanced_data.get('enhanced_perfect_exercises', [])
    print(f"总数: {len(exercises)}")
    
    enhanced_stats = defaultdict(int)
    for ex in exercises:
        for field in muscle_fields:
            if ex.get(field):
                enhanced_stats[field] += 1
    
    for field in muscle_fields:
        print(f"  {field}: {enhanced_stats[field]}")
else:
    print("文件不存在")

# 3. 增强数据文件2 (perfect_enhanced_dataset)
print("\n【3】增强数据文件2 (perfect_enhanced_dataset)")
print("-"*50)

enhanced2_path = Path(r"F:\build_body\perfect_enhanced_dataset")
if enhanced2_path.exists():
    json_files = list(enhanced2_path.glob("*.json"))
    print(f"JSON文件数: {len(json_files)}")
    if json_files:
        # 检查第一个文件的结构
        with open(json_files[0], 'r', encoding='utf-8') as f:
            sample = json.load(f)
        print(f"示例文件字段: {list(sample.keys())[:10]}...")
else:
    print("目录不存在")

print("\n" + "="*70)
print("数据库检查需要在Docker容器内执行")
print("="*70)
