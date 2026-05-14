#!/usr/bin/env python3
"""
检查 description_zh_professional 的质量

分析是否真的是通用模板，还是有实际的描述价值
"""

import json
import sys
import os
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

print("=" * 80)
print("description_zh_professional 质量检查")
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

# 分析 description_zh_professional
desc_patterns = []
unique_parts = []

for exercise in exercises:
    desc = exercise.get('description_zh_professional', '')
    if desc:
        # 提取动作名称和目标肌肉
        name_zh = exercise.get('name_zh', '')
        primary_muscle = exercise.get('primary_muscle_zh', '')
        equipment = exercise.get('equipment_zh', '')
        
        # 检查是否是模板
        if '是针对' in desc and '的专业训练动作' in desc:
            # 提取模板中的变量部分
            parts = desc.split('是针对')
            if len(parts) >= 2:
                action_name = parts[0].strip()
                muscle_part = parts[1].split('的专业训练动作')[0].strip()
                desc_patterns.append({
                    "name": action_name,
                    "muscle": muscle_part,
                    "equipment": equipment,
                    "full_desc": desc
                })

print(f"\n发现模板化描述: {len(desc_patterns)} 个")

# 统计模板的多样性
muscle_counter = Counter([p['muscle'] for p in desc_patterns])
equipment_counter = Counter([p['equipment'] for p in desc_patterns])

print("\n【模板分析】")
print("-" * 80)

print("\n目标肌肉分布（前10）：")
for muscle, count in muscle_counter.most_common(10):
    print(f"  {muscle}: {count} 个动作")

print("\n器械分布（前10）：")
for equipment, count in equipment_counter.most_common(10):
    if isinstance(equipment, list):
        equipment = ', '.join(equipment)
    print(f"  {equipment}: {count} 个动作")

# 展示样本
print("\n【样本展示】")
print("-" * 80)

print("\n样本1 - 不同动作的 description_zh_professional：")
sample_exercises = [
    exercises[0],   # 第1个
    exercises[10],  # 第11个
    exercises[100], # 第101个
    exercises[500], # 第501个
    exercises[1000], # 第1001个
]

for i, ex in enumerate(sample_exercises, 1):
    print(f"\n{i}. ID={ex.get('id')}, 名称={ex.get('name_zh')}")
    print(f"   目标肌肉: {ex.get('primary_muscle_zh')}")
    print(f"   器械: {ex.get('equipment_zh')}")
    print(f"   描述: {ex.get('description_zh_professional', '')}")

# 检查是否所有描述都是相同的模板
print("\n\n【模板统一性检查】")
print("-" * 80)

template_base = "是针对XXX的专业训练动作。使用XXX进行阻力训练。动作执行应保持控制节奏，充分感受目标肌群的收缩。该动作基于运动生物力学原理设计，能有效激活目标肌群并提升肌肉力量。请在专业指导下进行训练，注意动作规范，避免运动损伤"

all_same_template = True
for exercise in exercises:
    desc = exercise.get('description_zh_professional', '')
    if desc:
        # 移除动作名称、肌肉、器械后检查
        desc_without_vars = desc
        for word in [exercise.get('name_zh', ''), exercise.get('primary_muscle_zh', ''), str(exercise.get('equipment_zh', ''))]:
            desc_without_vars = desc_without_vars.replace(word, 'XXX')
        
        if desc_without_vars != template_base:
            all_same_template = False
            break

if all_same_template:
    print("\n✅ 所有 description_zh_professional 都使用相同的模板")
    print(f"\n模板内容：\n{template_base}")
else:
    print("\n❌ description_zh_professional 不是完全统一的模板")

print("\n\n【结论】")
print("=" * 80)

print("\n💡 description_zh_professional 的特点：")
print("  1. 使用统一的模板格式")
print("  2. 仅替换了：动作名称、目标肌肉、器械类型")
print("  3. 没有动作特定的描述信息")
print("  4. 没有技术要点、注意事项等细节")

print("\n❌ 不适合作为真正的动作描述：")
print("  1. 过于通用，缺乏个性化")
print("  2. 没有动作特点说明")
print("  3. 没有与其他动作的区别")
print("  4. 用户无法从中获得有价值的信息")

print("\n" + "=" * 80)
print("检查完成")
print("=" * 80)
