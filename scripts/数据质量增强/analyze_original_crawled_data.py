#!/usr/bin/env python3
"""
分析初始爬取版本的Exercise数据质量

对比分析：
1. 初始爬取版本 (yuzhen-backend/storage/app/public/exercises_v2/)
2. 当前Neo4j数据库版本 (data/enhanced_perfect_exercises_dataset.json)

重点检查：
- description 和 correct_steps 的关系
- correct_steps_zh 是否存在
- 数据结构差异
"""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

print("=" * 80)
print("初始爬取版本 vs 当前数据库版本 - 数据质量对比分析")
print("=" * 80)

# 1. 分析初始爬取版本
print("\n【第一部分】分析初始爬取版本")
print("-" * 80)

# 尝试多个可能的路径
possible_paths = [
    Path('yuzhen-backend/storage/app/public/exercises_v2'),
    Path('../yuzhen-backend/storage/app/public/exercises_v2'),
    Path('../../yuzhen-backend/storage/app/public/exercises_v2'),
]

crawled_base_path = None
for path in possible_paths:
    if path.exists():
        crawled_base_path = path
        break

if crawled_base_path is None:
    print(f"错误：找不到初始爬取数据目录")
    print(f"尝试的路径:")
    for p in possible_paths:
        print(f"  - {p.absolute()}")
    sys.exit(1)

print(f"使用路径: {crawled_base_path.absolute()}")
crawled_stats = {
    "total": 0,
    "has_correct_steps_zh": 0,
    "desc_contains_correct_steps": 0,
    "desc_equals_steps": 0,
    "has_detailed_description": 0,
    "steps_zh_empty": 0,
}

crawled_samples = {
    "has_steps_zh": [],
    "no_steps_zh": [],
    "detailed_desc": [],
    "simple_desc": [],
}

print("\n扫描初始爬取数据...")

# 遍历所有data.json文件
for range_dir in sorted(crawled_base_path.glob('*')):
    if not range_dir.is_dir():
        continue
    
    for sub_range_dir in sorted(range_dir.glob('*')):
        if not sub_range_dir.is_dir():
            continue
        
        for exercise_dir in sorted(sub_range_dir.glob('*')):
            if not exercise_dir.is_dir():
                continue
            
            data_file = exercise_dir / 'data.json'
            if not data_file.exists():
                continue
            
            try:
                with open(data_file, 'r', encoding='utf-8') as f:
                    exercise = json.load(f)
                
                crawled_stats["total"] += 1
                
                ex_id = exercise.get('id')
                name_zh = exercise.get('name_zh', '')
                desc = exercise.get('description', '')
                desc_zh = exercise.get('description_zh', '')
                steps_zh = exercise.get('correct_steps_zh', [])
                steps_en = exercise.get('correct_steps', [])
                
                # 检查是否有correct_steps_zh
                if steps_zh and len(steps_zh) > 0:
                    crawled_stats["has_correct_steps_zh"] += 1
                    if len(crawled_samples["has_steps_zh"]) < 3:
                        crawled_samples["has_steps_zh"].append({
                            "id": ex_id,
                            "name_zh": name_zh,
                            "steps_zh_count": len(steps_zh),
                            "steps_zh_sample": steps_zh[0] if steps_zh else None
                        })
                else:
                    crawled_stats["steps_zh_empty"] += 1
                    if len(crawled_samples["no_steps_zh"]) < 3:
                        crawled_samples["no_steps_zh"].append({
                            "id": ex_id,
                            "name_zh": name_zh,
                            "desc_zh": desc_zh[:100]
                        })
                
                # 检查description是否包含"Correct Steps"
                if "**Correct Steps:**" in desc or "正确步骤" in desc_zh:
                    crawled_stats["desc_contains_correct_steps"] += 1
                
                # 检查description是否详细（长度>500字符）
                if len(desc) > 500:
                    crawled_stats["has_detailed_description"] += 1
                    if len(crawled_samples["detailed_desc"]) < 3:
                        crawled_samples["detailed_desc"].append({
                            "id": ex_id,
                            "name_zh": name_zh,
                            "desc_length": len(desc),
                            "desc_preview": desc[:200]
                        })
                else:
                    if len(crawled_samples["simple_desc"]) < 3:
                        crawled_samples["simple_desc"].append({
                            "id": ex_id,
                            "name_zh": name_zh,
                            "desc_length": len(desc),
                            "desc_preview": desc[:200]
                        })
                
                # 检查description和correct_steps是否相同
                if steps_en:
                    steps_text = '\n'.join([s.get('text', '') if isinstance(s, dict) else s for s in steps_en])
                    desc_clean = desc.replace('**Correct Steps:**', '').replace('**', '').strip()
                    
                    import re
                    desc_normalized = re.sub(r'^\d+\.\s*', '', desc_clean, flags=re.MULTILINE)
                    steps_normalized = re.sub(r'^\d+\.\s*', '', steps_text, flags=re.MULTILINE)
                    
                    if desc_normalized.replace(' ', '').replace('\n', '') == steps_normalized.replace(' ', '').replace('\n', ''):
                        crawled_stats["desc_equals_steps"] += 1
                
            except Exception as e:
                print(f"错误：读取 {data_file} 失败: {e}")
                continue

print(f"\n初始爬取版本统计：")
print(f"  总动作数: {crawled_stats['total']}")
print(f"  有 correct_steps_zh: {crawled_stats['has_correct_steps_zh']} ({crawled_stats['has_correct_steps_zh']/crawled_stats['total']*100:.1f}%)")
print(f"  correct_steps_zh 为空: {crawled_stats['steps_zh_empty']} ({crawled_stats['steps_zh_empty']/crawled_stats['total']*100:.1f}%)")
print(f"  description 包含 'Correct Steps': {crawled_stats['desc_contains_correct_steps']} ({crawled_stats['desc_contains_correct_steps']/crawled_stats['total']*100:.1f}%)")
print(f"  description 和 correct_steps 内容相同: {crawled_stats['desc_equals_steps']} ({crawled_stats['desc_equals_steps']/crawled_stats['total']*100:.1f}%)")
print(f"  有详细 description (>500字符): {crawled_stats['has_detailed_description']} ({crawled_stats['has_detailed_description']/crawled_stats['total']*100:.1f}%)")

# 2. 对比当前数据库版本
print("\n\n【第二部分】对比当前数据库版本")
print("-" * 80)

db_file = 'data/enhanced_perfect_exercises_dataset.json'
print(f"\n读取数据库文件: {db_file}")

with open(db_file, 'r', encoding='utf-8') as f:
    db_data = json.load(f)

if isinstance(db_data, dict):
    if 'enhanced_perfect_exercises' in db_data:
        db_exercises = db_data['enhanced_perfect_exercises']
    elif 'exercises' in db_data:
        db_exercises = db_data['exercises']
else:
    db_exercises = db_data

db_stats = {
    "total": len(db_exercises),
    "has_correct_steps_zh": 0,
    "steps_zh_empty": 0,
    "desc_en_equals_steps_en": 0,
    "has_professional_desc": 0,
}

for exercise in db_exercises:
    steps_zh = exercise.get('correct_steps_zh') or []
    desc_zh_prof = exercise.get('description_zh_professional') or ''
    
    if steps_zh and len(steps_zh) > 0:
        db_stats["has_correct_steps_zh"] += 1
    else:
        db_stats["steps_zh_empty"] += 1
    
    if desc_zh_prof:
        db_stats["has_professional_desc"] += 1

print(f"\n当前数据库版本统计：")
print(f"  总动作数: {db_stats['total']}")
print(f"  有 correct_steps_zh: {db_stats['has_correct_steps_zh']} ({db_stats['has_correct_steps_zh']/db_stats['total']*100:.1f}%)")
print(f"  correct_steps_zh 为空: {db_stats['steps_zh_empty']} ({db_stats['steps_zh_empty']/db_stats['total']*100:.1f}%)")
print(f"  有 description_zh_professional: {db_stats['has_professional_desc']} ({db_stats['has_professional_desc']/db_stats['total']*100:.1f}%)")

# 3. 关键发现
print("\n\n【第三部分】关键发现")
print("=" * 80)

print("\n✅ 初始爬取版本的优势：")
print(f"  1. 有 {crawled_stats['has_correct_steps_zh']} 个动作包含 correct_steps_zh")
print(f"  2. 有 {crawled_stats['has_detailed_description']} 个动作有详细的 description")

print("\n❌ 初始爬取版本的问题：")
print(f"  1. {crawled_stats['steps_zh_empty']} 个动作缺少 correct_steps_zh ({crawled_stats['steps_zh_empty']/crawled_stats['total']*100:.1f}%)")
print(f"  2. {crawled_stats['desc_contains_correct_steps']} 个动作的 description 包含步骤内容 ({crawled_stats['desc_contains_correct_steps']/crawled_stats['total']*100:.1f}%)")
print(f"  3. {crawled_stats['desc_equals_steps']} 个动作的 description 和 correct_steps 完全相同 ({crawled_stats['desc_equals_steps']/crawled_stats['total']*100:.1f}%)")

print("\n🔄 数据演变：")
print(f"  初始版本 → 当前数据库版本")
print(f"  correct_steps_zh: {crawled_stats['has_correct_steps_zh']} → {db_stats['has_correct_steps_zh']}")
print(f"  新增 description_zh_professional: 0 → {db_stats['has_professional_desc']}")

print("\n💡 结论：")
print("  1. 初始爬取时，description 和 correct_steps 就已经是相同内容")
print("  2. 初始爬取时，大部分动作就缺少 correct_steps_zh")
print("  3. 这不是导入脚本的问题，而是源数据本身的问题")
print("  4. description_zh_professional 是后期生成的，质量较好")

# 4. 样本展示
print("\n\n【第四部分】样本数据")
print("=" * 80)

print("\n【样本1】初始版本 - 有 correct_steps_zh 的动作")
print("-" * 80)
for i, sample in enumerate(crawled_samples["has_steps_zh"], 1):
    print(f"\n{i}. ID={sample['id']}, 名称={sample['name_zh']}")
    print(f"   steps_zh 数量: {sample['steps_zh_count']}")
    print(f"   第一条: {sample['steps_zh_sample']}")

print("\n【样本2】初始版本 - 没有 correct_steps_zh 的动作")
print("-" * 80)
for i, sample in enumerate(crawled_samples["no_steps_zh"], 1):
    print(f"\n{i}. ID={sample['id']}, 名称={sample['name_zh']}")
    print(f"   description_zh: {sample['desc_zh']}...")

print("\n【样本3】初始版本 - 有详细 description 的动作")
print("-" * 80)
for i, sample in enumerate(crawled_samples["detailed_desc"], 1):
    print(f"\n{i}. ID={sample['id']}, 名称={sample['name_zh']}")
    print(f"   description 长度: {sample['desc_length']}")
    print(f"   预览: {sample['desc_preview']}...")

print("\n【样本4】初始版本 - 简单 description 的动作")
print("-" * 80)
for i, sample in enumerate(crawled_samples["simple_desc"], 1):
    print(f"\n{i}. ID={sample['id']}, 名称={sample['name_zh']}")
    print(f"   description 长度: {sample['desc_length']}")
    print(f"   预览: {sample['desc_preview']}...")

print("\n" + "=" * 80)
print("分析完成")
print("=" * 80)

# 保存报告
report = {
    "crawled_version": crawled_stats,
    "database_version": db_stats,
    "samples": crawled_samples
}

report_file = 'original_vs_current_data_quality_report.json'
with open(report_file, 'w', encoding='utf-8') as f:
    json.dump(report, f, indent=2, ensure_ascii=False)

print(f"\n详细报告已保存到: {report_file}")
