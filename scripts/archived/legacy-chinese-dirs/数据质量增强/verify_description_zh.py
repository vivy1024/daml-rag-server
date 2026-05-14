#!/usr/bin/env python3
"""
验证 description_zh 是否包含完整的步骤内容

检查是否可以用 description_zh 替换 correct_steps_zh
"""

import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

print("=" * 80)
print("验证 description_zh 质量")
print("=" * 80)

# 读取数据
db_file = 'data/enhanced_perfect_exercises_dataset.json'
print(f"\n读取数据库文件: {db_file}")

with open(db_file, 'r', encoding='utf-8') as f:
    db_data = json.load(f)

if isinstance(db_data, dict):
    if 'enhanced_perfect_exercises' in db_data:
        exercises = db_data['enhanced_perfect_exercises']
    elif 'exercises' in db_data:
        exercises = db_data['exercises']
else:
    exercises = db_data

print(f"总动作数: {len(exercises)}")

# 统计
stats = {
    "total": len(exercises),
    "has_desc_zh": 0,
    "desc_zh_empty": 0,
    "desc_zh_has_steps": 0,  # 包含"正确步骤"或"步骤"
    "desc_zh_is_professional": 0,  # 是专业描述模板
    "desc_zh_is_detailed": 0,  # 详细描述（>200字符）
    "steps_zh_empty": 0,
    "can_use_desc_zh_as_steps": 0,  # 可以用 description_zh 作为步骤
}

samples = {
    "has_steps_content": [],
    "professional_template": [],
    "detailed_desc": [],
    "empty_steps_zh": [],
}

print("\n开始分析...")

for exercise in exercises:
    ex_id = exercise.get('id')
    name_zh = exercise.get('name_zh', '')
    desc_zh = (exercise.get('description_zh') or '').strip()
    steps_zh = exercise.get('correct_steps_zh') or []
    
    # 统计 description_zh
    if desc_zh:
        stats["has_desc_zh"] += 1
        
        # 检查是否包含步骤内容
        if '正确步骤' in desc_zh or '步骤：' in desc_zh or '。 1' in desc_zh or '。1' in desc_zh:
            stats["desc_zh_has_steps"] += 1
            if len(samples["has_steps_content"]) < 5:
                samples["has_steps_content"].append({
                    "id": ex_id,
                    "name_zh": name_zh,
                    "desc_zh": desc_zh[:150],
                    "has_steps_zh": len(steps_zh) > 0
                })
        
        # 检查是否是专业模板
        if '是针对' in desc_zh and '的专业训练动作' in desc_zh:
            stats["desc_zh_is_professional"] += 1
            if len(samples["professional_template"]) < 3:
                samples["professional_template"].append({
                    "id": ex_id,
                    "name_zh": name_zh,
                    "desc_zh": desc_zh
                })
        
        # 检查是否是详细描述
        if len(desc_zh) > 200:
            stats["desc_zh_is_detailed"] += 1
            if len(samples["detailed_desc"]) < 3:
                samples["detailed_desc"].append({
                    "id": ex_id,
                    "name_zh": name_zh,
                    "desc_zh_length": len(desc_zh),
                    "desc_zh": desc_zh[:200]
                })
    else:
        stats["desc_zh_empty"] += 1
    
    # 统计 correct_steps_zh
    if not steps_zh or len(steps_zh) == 0:
        stats["steps_zh_empty"] += 1
        
        # 如果 description_zh 包含步骤，可以用来替换
        if desc_zh and ('正确步骤' in desc_zh or '步骤：' in desc_zh or '。 1' in desc_zh):
            stats["can_use_desc_zh_as_steps"] += 1
            if len(samples["empty_steps_zh"]) < 5:
                samples["empty_steps_zh"].append({
                    "id": ex_id,
                    "name_zh": name_zh,
                    "desc_zh": desc_zh[:150]
                })

print("\n【统计结果】")
print("=" * 80)

print(f"\n总动作数: {stats['total']}")
print(f"\ndescription_zh 状态：")
print(f"  有 description_zh: {stats['has_desc_zh']} ({stats['has_desc_zh']/stats['total']*100:.1f}%)")
print(f"  description_zh 为空: {stats['desc_zh_empty']} ({stats['desc_zh_empty']/stats['total']*100:.1f}%)")
print(f"  包含步骤内容: {stats['desc_zh_has_steps']} ({stats['desc_zh_has_steps']/stats['total']*100:.1f}%)")
print(f"  是专业模板: {stats['desc_zh_is_professional']} ({stats['desc_zh_is_professional']/stats['total']*100:.1f}%)")
print(f"  是详细描述 (>200字符): {stats['desc_zh_is_detailed']} ({stats['desc_zh_is_detailed']/stats['total']*100:.1f}%)")

print(f"\ncorrect_steps_zh 状态：")
print(f"  correct_steps_zh 为空: {stats['steps_zh_empty']} ({stats['steps_zh_empty']/stats['total']*100:.1f}%)")
print(f"  可用 description_zh 替换: {stats['can_use_desc_zh_as_steps']} ({stats['can_use_desc_zh_as_steps']/stats['steps_zh_empty']*100:.1f}% of empty)")

print("\n【样本展示】")
print("=" * 80)

print("\n【样本1】description_zh 包含步骤内容")
print("-" * 80)
for i, sample in enumerate(samples["has_steps_content"], 1):
    print(f"\n{i}. ID={sample['id']}, 名称={sample['name_zh']}")
    print(f"   有 correct_steps_zh: {'✅' if sample['has_steps_zh'] else '❌'}")
    print(f"   description_zh: {sample['desc_zh']}...")

print("\n【样本2】description_zh 是专业模板")
print("-" * 80)
for i, sample in enumerate(samples["professional_template"], 1):
    print(f"\n{i}. ID={sample['id']}, 名称={sample['name_zh']}")
    print(f"   description_zh: {sample['desc_zh']}")

print("\n【样本3】description_zh 是详细描述")
print("-" * 80)
for i, sample in enumerate(samples["detailed_desc"], 1):
    print(f"\n{i}. ID={sample['id']}, 名称={sample['name_zh']}")
    print(f"   长度: {sample['desc_zh_length']}")
    print(f"   description_zh: {sample['desc_zh']}...")

print("\n【样本4】correct_steps_zh 为空，但 description_zh 有步骤")
print("-" * 80)
for i, sample in enumerate(samples["empty_steps_zh"], 1):
    print(f"\n{i}. ID={sample['id']}, 名称={sample['name_zh']}")
    print(f"   description_zh: {sample['desc_zh']}...")

print("\n\n【结论】")
print("=" * 80)

print("\n✅ 可行性分析：")
if stats['desc_zh_has_steps'] > stats['total'] * 0.5:
    print(f"  ✅ {stats['desc_zh_has_steps']} 个动作的 description_zh 包含步骤内容 ({stats['desc_zh_has_steps']/stats['total']*100:.1f}%)")
    print(f"  ✅ 可以用 description_zh 替换 {stats['can_use_desc_zh_as_steps']} 个缺失的 correct_steps_zh")
else:
    print(f"  ❌ 只有 {stats['desc_zh_has_steps']} 个动作的 description_zh 包含步骤内容")
    print(f"  ❌ 不适合大规模替换")

print("\n💡 用户方案评估：")
print("  方案：用 description_zh 替换 correct_steps_zh，然后删除 description_zh 和 description_en")
if stats['can_use_desc_zh_as_steps'] > stats['steps_zh_empty'] * 0.8:
    print(f"  ✅ 可行！可以替换 {stats['can_use_desc_zh_as_steps']} / {stats['steps_zh_empty']} 个缺失的步骤")
else:
    print(f"  ⚠️ 部分可行，只能替换 {stats['can_use_desc_zh_as_steps']} / {stats['steps_zh_empty']} 个缺失的步骤")

print("\n🎯 建议操作：")
print("  1. 对于 correct_steps_zh 为空的动作：")
print(f"     - 如果 description_zh 包含步骤（{stats['can_use_desc_zh_as_steps']}个）：解析并提取步骤")
print(f"     - 如果 description_zh 不包含步骤：从 correct_steps_en 翻译")
print("  2. 删除 description_zh 和 description_en（等待重新爬取）")
print("  3. 保留 description_zh_professional（虽然是模板，但可以作为临时描述）")

print("\n" + "=" * 80)
print("验证完成")
print("=" * 80)
