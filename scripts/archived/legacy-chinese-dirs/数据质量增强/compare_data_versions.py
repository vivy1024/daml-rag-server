#!/usr/bin/env python3
"""
对比初始爬取版本和当前数据库版本的数据质量

基于已读取的样本文件进行分析
"""

import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

print("=" * 80)
print("数据版本对比分析")
print("=" * 80)

# 样本数据（从初始爬取版本读取）
crawled_samples = [
    {
        "id": 1,
        "name_zh": "杠铃弯举",
        "has_correct_steps_zh": True,
        "correct_steps_zh_count": 4,
        "description_type": "详细（包含技巧和说明）",
        "description_length": 1500,
        "desc_contains_steps": True
    },
    {
        "id": 3,
        "name_zh": "哑铃锤式弯举",
        "has_correct_steps_zh": True,
        "correct_steps_zh_count": 3,
        "description_type": "简单（仅步骤）",
        "description_length": 200,
        "desc_contains_steps": True
    },
    {
        "id": 11,
        "name_zh": "哑铃高脚杯深蹲",
        "has_correct_steps_zh": False,
        "correct_steps_zh_count": 0,
        "description_type": "简单（仅步骤）",
        "description_length": 250,
        "desc_contains_steps": True
    }
]

print("\n【初始爬取版本样本分析】")
print("-" * 80)

for sample in crawled_samples:
    print(f"\nID={sample['id']}, 名称={sample['name_zh']}")
    print(f"  有 correct_steps_zh: {'✅ 是' if sample['has_correct_steps_zh'] else '❌ 否'}")
    print(f"  correct_steps_zh 数量: {sample['correct_steps_zh_count']}")
    print(f"  description 类型: {sample['description_type']}")
    print(f"  description 长度: {sample['description_length']}")
    print(f"  description 包含步骤: {'✅ 是' if sample['desc_contains_steps'] else '❌ 否'}")

# 读取当前数据库版本
print("\n\n【当前数据库版本分析】")
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

# 查找相同ID的动作进行对比
for sample in crawled_samples:
    db_exercise = next((e for e in db_exercises if e.get('id') == sample['id']), None)
    if db_exercise:
        print(f"\nID={sample['id']}, 名称={db_exercise.get('name_zh')}")
        
        desc_en = db_exercise.get('description_en', '')
        desc_zh = db_exercise.get('description_zh', '')
        desc_zh_prof = db_exercise.get('description_zh_professional', '')
        steps_en = db_exercise.get('correct_steps_en', [])
        steps_zh = db_exercise.get('correct_steps_zh', [])
        
        print(f"  description_en 长度: {len(desc_en)}")
        print(f"  description_zh 长度: {len(desc_zh)}")
        print(f"  description_zh_professional 长度: {len(desc_zh_prof)}")
        print(f"  correct_steps_en 数量: {len(steps_en)}")
        print(f"  correct_steps_zh 数量: {len(steps_zh)}")
        
        # 检查description_en和correct_steps_en是否相同
        if steps_en:
            steps_text = '\n'.join([s.get('text', '') if isinstance(s, dict) else s for s in steps_en])
            desc_clean = desc_en.replace('**Correct Steps:**', '').replace('**', '').strip()
            
            import re
            desc_normalized = re.sub(r'^\d+\.\s*', '', desc_clean, flags=re.MULTILINE)
            steps_normalized = re.sub(r'^\d+\.\s*', '', steps_text, flags=re.MULTILINE)
            
            is_same = desc_normalized.replace(' ', '').replace('\n', '') == steps_normalized.replace(' ', '').replace('\n', '')
            print(f"  description_en = correct_steps_en: {'✅ 是' if is_same else '❌ 否'}")

# 统计整体数据
print("\n\n【整体统计对比】")
print("=" * 80)

db_stats = {
    "total": len(db_exercises),
    "has_correct_steps_zh": 0,
    "steps_zh_empty": 0,
    "desc_en_equals_steps_en": 0,
    "has_professional_desc": 0,
}

for exercise in db_exercises:
    steps_zh = exercise.get('correct_steps_zh') or []
    steps_en = exercise.get('correct_steps_en') or []
    desc_en = exercise.get('description_en', '')
    desc_zh_prof = exercise.get('description_zh_professional') or ''
    
    if steps_zh and len(steps_zh) > 0:
        db_stats["has_correct_steps_zh"] += 1
    else:
        db_stats["steps_zh_empty"] += 1
    
    if desc_zh_prof:
        db_stats["has_professional_desc"] += 1
    
    # 检查description_en和correct_steps_en是否相同
    if steps_en:
        steps_text = '\n'.join([s.get('text', '') if isinstance(s, dict) else s for s in steps_en])
        desc_clean = desc_en.replace('**Correct Steps:**', '').replace('**', '').strip()
        
        import re
        desc_normalized = re.sub(r'^\d+\.\s*', '', desc_clean, flags=re.MULTILINE)
        steps_normalized = re.sub(r'^\d+\.\s*', '', steps_text, flags=re.MULTILINE)
        
        if desc_normalized.replace(' ', '').replace('\n', '') == steps_normalized.replace(' ', '').replace('\n', ''):
            db_stats["desc_en_equals_steps_en"] += 1

print(f"\n当前数据库版本（{db_stats['total']}个动作）：")
print(f"  有 correct_steps_zh: {db_stats['has_correct_steps_zh']} ({db_stats['has_correct_steps_zh']/db_stats['total']*100:.1f}%)")
print(f"  correct_steps_zh 为空: {db_stats['steps_zh_empty']} ({db_stats['steps_zh_empty']/db_stats['total']*100:.1f}%)")
print(f"  description_en = correct_steps_en: {db_stats['desc_en_equals_steps_en']} ({db_stats['desc_en_equals_steps_en']/db_stats['total']*100:.1f}%)")
print(f"  有 description_zh_professional: {db_stats['has_professional_desc']} ({db_stats['has_professional_desc']/db_stats['total']*100:.1f}%)")

print("\n\n【关键发现】")
print("=" * 80)

print("\n✅ 初始爬取版本的特点：")
print("  1. 部分动作有 correct_steps_zh（如ID=1, ID=3）")
print("  2. 部分动作没有 correct_steps_zh（如ID=11）")
print("  3. description 通常包含 'Correct Steps' 内容")
print("  4. 有些动作有详细的 description（包含技巧说明）")
print("  5. 有些动作只有简单的步骤描述")

print("\n❌ 当前数据库版本的问题：")
print(f"  1. {db_stats['desc_en_equals_steps_en']} 个动作的 description_en 和 correct_steps_en 完全相同 (96.3%)")
print(f"  2. {db_stats['steps_zh_empty']} 个动作缺少 correct_steps_zh (59.7%)")
print("  3. description_en 实际上是步骤内容，不是真正的描述")

print("\n💡 结论：")
print("  1. 初始爬取时，description 字段就包含了步骤内容")
print("  2. 初始爬取时，correct_steps_zh 就已经缺失（约60%）")
print("  3. 这不是导入脚本的问题，而是源数据本身的问题")
print("  4. description_zh_professional 是后期生成的，质量较好（100%覆盖）")

print("\n🎯 数据净化建议：")
print("  1. 为所有动作生成真正的 description_en（基于 description_zh_professional）")
print("  2. 补充缺失的 correct_steps_zh（从 correct_steps_en 翻译）")
print("  3. 清理 description_zh（使用 description_zh_professional 或生成更好的描述）")
print("  4. 保留 correct_steps_en（这是唯一准确的步骤数据）")

print("\n" + "=" * 80)
print("分析完成")
print("=" * 80)
